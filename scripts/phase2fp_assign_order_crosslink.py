#!/usr/bin/env python3
"""Phase 2fp: Assign→order_index subject cross-link (RO) + cheap NF peek. No Post. Never 5x."""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
import cmd_layout
import post_abi
from handle import resolve_handle, HANDLE_TYPE_ARMY

assert allow_post() is False, "allow_post must stay False"

ASSIGN_VT = cmd_layout.ORDERS["COrderAssignCommand"]["vt"]
UNASSIGN_VT = cmd_layout.ORDERS["COrderUnassignCommand"]["vt"]
EXECUTE_VT = cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]
DELETE_VT = cmd_layout.ORDERS["COrderDeleteCommand"]["vt"]
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
NF_FRONT_VT = cmd_layout.ORDERS["COrderNewFrontCommand"]["vt"]
HANDLE_STRIDE = 8
CA_HANDLE = 0x18
CA_PROVINCE = 0x28
CA_TAG = 0x1E0


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def live_meta(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = struct.unpack("<i", b.read(gs + 0x484, 4))[0]
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "pid": find_pid(),
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x Assign→order_index cross-link (no Post)",
    }


def decode_units(b, base, data: int, size: int) -> dict:
    out = {"elements": [], "army": [], "other": []}
    if not data or size <= 0 or size > 64:
        return out
    blob = try_read(b, data, size * HANDLE_STRIDE)
    if not blob or len(blob) < size * HANDLE_STRIDE:
        out["read_error"] = True
        return out
    out["hex"] = blob.hex()
    for i in range(size):
        typ, ix = struct.unpack_from("<II", blob, i * 8)
        el = {
            "i": i,
            "type": typ,
            "index": ix,
            "as_list": [typ, ix],
            "type_hex": hex(typ),
            "large_type": typ >= 0x64,
        }
        if typ == HANDLE_TYPE_ARMY:
            el["note"] = "HANDLE_TYPE_ARMY"
            ptr = None
            try:
                ptr = resolve_handle(b, typ, ix, base)
            except Exception as e:
                el["resolve_error"] = str(e)
            if ptr:
                el["resolved"] = hex(ptr)
                try:
                    echo = list(struct.unpack("<II", b.read(ptr + CA_HANDLE, 8)))
                    el["army_plus18_echo"] = echo
                    el["echo_matches"] = echo == [typ, ix]
                    el["province_id"] = u32(b, ptr + CA_PROVINCE)
                    el["country_tag"] = u32(b, ptr + CA_TAG)
                except Exception as e:
                    el["army_peek_error"] = str(e)
            out["army"].append(el)
        else:
            el["note"] = "non_ARMY"
            if typ < 0x64:
                try:
                    ptr = resolve_handle(b, typ, ix, base)
                    el["resolved"] = hex(ptr) if ptr else None
                except Exception as e:
                    el["resolve_error"] = str(e)
            else:
                el["resolve_note"] = "type>=0x64 large-type path not in handle.resolve_handle"
            out["other"].append(el)
        out["elements"].append(el)
    return out


def bounded_sight(b, base, seconds: float = 75.0) -> dict:
    sess = u64(b, base + post_abi.G_SESSION)
    watch = {
        ASSIGN_VT: "COrderAssignCommand",
        UNASSIGN_VT: "COrderUnassignCommand",
        EXECUTE_VT: "COrderExecuteCommand",
        DELETE_VT: "COrderDeleteCommand",
        NF_VT: "COrderNewFallbackCommand",
        NF_FRONT_VT: "COrderNewFrontCommand",
        0x29F3710: "CHourlyTickCommand",
    }
    t0 = time.time()
    sight_counts: dict[str, int] = {}
    assigns = []
    executes = []
    deletes = []
    fallbacks = []
    fronts = []
    polls = 0
    seen_addr = set()

    while time.time() - t0 < seconds:
        polls += 1
        try:
            stage = u64(b, sess + post_abi.CSession_STAGE_ARRAY)
            scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        except Exception:
            continue
        if not stage or not (0 < scount < 256):
            if polls % 400 == 0:
                time.sleep(0)
            continue
        for i in range(scount):
            try:
                ptr = u64(b, stage + i * 8)
                vt = u64(b, ptr)
            except Exception:
                continue
            rva = vt - base
            name = watch.get(rva)
            if not name:
                continue
            sight_counts[name] = sight_counts.get(name, 0) + 1
            key = (name, ptr)
            if key in seen_addr:
                continue
            # allow re-capture Assign periodically by addr+time bucket? keep first N unique addrs
            if name == "COrderAssignCommand" and len(assigns) >= 8:
                continue
            if name != "COrderAssignCommand" and name in (
                "COrderExecuteCommand",
                "COrderDeleteCommand",
                "COrderNewFallbackCommand",
                "COrderNewFrontCommand",
            ):
                # unique addr only for siblings
                pass
            seen_addr.add(key)
            t = round(time.time() - t0, 3)
            try:
                if name == "COrderAssignCommand":
                    data = u64(b, ptr + 0x28)
                    cap = struct.unpack("<i", b.read(ptr + 0x30, 4))[0]
                    size = struct.unpack("<i", b.read(ptr + 0x34, 4))[0]
                    alloc = u64(b, ptr + 0x38)
                    u40 = u32(b, ptr + 0x40)
                    order_index = u32(b, ptr + 0x48)
                    amin = b.read(ptr + 0x4C, 1)[0]
                    units = decode_units(b, base, data, size)
                    assigns.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "units_cpdx": {
                                "data": hex(data),
                                "capacity": cap,
                                "size": size,
                                "alloc": hex(alloc),
                            },
                            "u32_at_0x40_observed": u40,
                            "u32_at_0x40_hex": hex(u40),
                            "order_index": order_index,
                            "assign_to_minimum_order": amin,
                            "units": units,
                            "army_lists": [e["as_list"] for e in units["army"]],
                            "other_lists": [e["as_list"] for e in units["other"]],
                        }
                    )
                elif name == "COrderExecuteCommand":
                    executes.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "order_index": u32(b, ptr + 0x30),
                            "execute_order": b.read(ptr + 0x34, 1)[0],
                            "all": b.read(ptr + 0x35, 1)[0],
                        }
                    )
                elif name == "COrderDeleteCommand":
                    deletes.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "order_index": u32(b, ptr + 0x30),
                        }
                    )
                elif name == "COrderNewFallbackCommand":
                    sub_t = u32(b, ptr + 0x28)
                    sub_i = u32(b, ptr + 0x2C)
                    ud = u64(b, ptr + 0x30)
                    us = struct.unpack("<i", b.read(ptr + 0x3C, 4))[0]
                    ps = struct.unpack("<i", b.read(ptr + 0x54, 4))[0]
                    fallbacks.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "subject_handle": [sub_t, sub_i],
                            "subject_type_hex": hex(sub_t),
                            "units_size": us,
                            "provinces_size": ps,
                            "units_data": hex(ud),
                        }
                    )
                elif name == "COrderNewFrontCommand":
                    # units @ catalog 0x38 data / 0x44 count — fields say units_data 56=0x38, units_count 68=0x44
                    fronts.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "hex40": b.read(ptr, 0x40).hex(),
                        }
                    )
            except Exception as e:
                if name == "COrderAssignCommand" and len(assigns) < 8:
                    assigns.append({"source": f"stage[{i}]", "addr": hex(ptr), "t": t, "error": str(e)})
        if polls % 400 == 0:
            time.sleep(0)

    # cross-link tables
    by_order: dict[str, list] = {}
    for a in assigns:
        if "order_index" not in a:
            continue
        k = str(a["order_index"])
        by_order.setdefault(k, []).append(
            {
                "addr": a["addr"],
                "t": a["t"],
                "army_lists": a.get("army_lists"),
                "other_lists": a.get("other_lists"),
                "size": (a.get("units_cpdx") or {}).get("size"),
                "assign_to_minimum_order": a.get("assign_to_minimum_order"),
            }
        )

    exec_idx = {e["order_index"] for e in executes if "order_index" in e}
    del_idx = {d["order_index"] for d in deletes if "order_index" in d}
    assign_idx = {a["order_index"] for a in assigns if "order_index" in a}
    overlap_exec = sorted(assign_idx & exec_idx)
    overlap_del = sorted(assign_idx & del_idx)

    return {
        "observe_seconds": seconds,
        "elapsed": round(time.time() - t0, 3),
        "polls": polls,
        "sight_counts": sight_counts,
        "assigns": assigns,
        "executes": executes[:20],
        "deletes": deletes[:20],
        "fallbacks": fallbacks,
        "fronts_n": len(fronts),
        "fronts_sample": fronts[:3],
        "crosslink": {
            "by_order_index": by_order,
            "assign_order_indices": sorted(assign_idx),
            "execute_order_indices": sorted(exec_idx)[:40],
            "delete_order_indices": sorted(del_idx)[:40],
            "overlap_assign_execute": overlap_exec,
            "overlap_assign_delete": overlap_del,
        },
        "fallback_seen": len(fallbacks) > 0,
        "assign_seen": len(assigns) > 0,
    }


def reuse_2fo_examples() -> list:
    """Document prior authoritative 2fo Assign rows as cross-link examples (no invent)."""
    fo = json.loads((ROOT / "reports" / "phase2fo_assign_units_handles.json").read_text(encoding="utf-8"))
    rows = []
    for c in (fo.get("bounded_sight") or {}).get("captures") or []:
        if c.get("name") != "COrderAssignCommand" or not c.get("decoded"):
            continue
        rows.append(
            {
                "origin": "2fo_sight",
                "order_index": (c.get("trail") or {}).get("order_index"),
                "units": c.get("units"),
                "army_lists": [e["as_list"] for e in c["decoded"]["elements"] if e.get("type") == HANDLE_TYPE_ARMY],
                "other_lists": [e["as_list"] for e in c["decoded"]["elements"] if e.get("type") != HANDLE_TYPE_ARMY],
            }
        )
    return rows


def main():
    pid = find_pid()
    b = Backend(pid)
    base = int(b.image_base)
    live0 = live_meta(b, base)
    prior = reuse_2fo_examples()

    print("bounded sight 75s Assign/Execute/NF...", flush=True)
    sight = bounded_sight(b, base, 75.0)
    live1 = live_meta(b, base)

    # semantic model — only what fields + live prove
    semantic = {
        "COrderAssignCommand": {
            "units_cpdxarray@+0x28": "armies (HANDLE_TYPE_ARMY=0x33) and rare non-ARMY elems",
            "order_index@+0x48": "battle-plan order slot index (same index space as Execute/Delete @+0x30)",
            "assign_to_minimum_order@+0x4C": "u8 flag",
            "link": "Assign binds units[] → order_index slot (army→order subject link)",
            "not_proven": [
                "exact COrder* object pointer for order_index (no order-table walk this slice)",
                "NewFallback subject type-id table",
                "name of u32@+0x40 (still observed-only)",
            ],
        },
        "sibling_index_space": {
            "COrderExecuteCommand.order_index@+0x30": "same integer space",
            "COrderDeleteCommand.order_index@+0x30": "same integer space",
            "COrderNewFallbackCommand.subject_handle@+0x28": "order-domain {type,index} via gate 0xbbb1e0 — distinct from Assign.order_index",
        },
    }

    army_examples = []
    for a in sight["assigns"]:
        if not a.get("army_lists"):
            continue
        army_examples.append(
            {
                "order_index": a.get("order_index"),
                "assign_to_minimum_order": a.get("assign_to_minimum_order"),
                "army_lists": a.get("army_lists"),
                "other_lists": a.get("other_lists"),
                "army_detail": [
                    {
                        "as_list": e["as_list"],
                        "province_id": e.get("province_id"),
                        "country_tag": e.get("country_tag"),
                        "echo_matches": e.get("echo_matches"),
                    }
                    for e in (a.get("units") or {}).get("army") or []
                ],
            }
        )

    result = (
        "ASSIGN_ORDER_CROSSLINK_DOCUMENTED"
        if (sight["assign_seen"] or prior)
        else "ASSIGN_ORDER_CROSSLINK_THIN"
    )
    works = [
        "Assign semantic: units[] (army handles) bind to order_index@+0x48 battle-plan slot",
        "Execute/Delete share order_index integer space @+0x30 (catalog+live)",
        f"live assigns={len(sight['assigns'])} executes={len(sight['executes'])} deletes={len(sight['deletes'])} NF={len(sight['fallbacks'])}",
        f"overlap assign∩execute={sight['crosslink']['overlap_assign_execute']} assign∩delete={sight['crosslink']['overlap_assign_delete']}",
        f"prior 2fo examples reused={len(prior)}",
        "allow_post False; never 5x; 2fb not executed; tool-gate CLOSED",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "path-vector nonempty",
        "NewFallback subject type-id table",
        "order_index→COrder* table walk",
        "live midflight NewFallback hex" if not sight["fallback_seen"] else "NewFallback subject fully typed",
    ]
    next_blocker = (
        "NON-Post: NewFallback/ReplaceFallback midflight subject type-id "
        "OR order_index→order-object table walk; still NO ALLOW_POST"
    )

    report = {
        "phase": "2fp",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "39a915c",
        "semantic": semantic,
        "live_at_start": live0,
        "live": live1,
        "prior_2fo_examples": prior,
        "bounded_sight": sight,
        "army_examples": army_examples,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "phase2fp_assign_order_crosslink.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fp",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "scenario": live1["scenario"],
        "assigns_n": len(sight["assigns"]),
        "executes_n": len(sight["executes"]),
        "fallbacks_n": len(sight["fallbacks"]),
        "crosslink": {
            "assign_order_indices": sight["crosslink"]["assign_order_indices"],
            "overlap_assign_execute": sight["crosslink"]["overlap_assign_execute"],
            "overlap_assign_delete": sight["crosslink"]["overlap_assign_delete"],
            "by_order_index": sight["crosslink"]["by_order_index"],
        },
        "army_examples": army_examples[:6],
        "prior_2fo_examples": prior,
        "sight_counts": sight["sight_counts"],
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "39a915c",
    }
    (ROOT / "reports" / "phase2fp_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # cheap recipe note only — exact replace on order_assign_recipe note string
    asp = ROOT / "calling" / "army_subjects.py"
    at = asp.read_text(encoding="utf-8")
    old = '"note": "2fn: Assign edge; vectors game-alloc; posting DISABLED",'
    new = (
        '"note": "2fn/2fp: units[]→order_index@+0x48 battle-plan slot; '
        'Execute/Delete share index space@+0x30; posting DISABLED",'
    )
    patched = 0
    if old in at:
        at = at.replace(old, new, 1)
        asp.write_text(at, encoding="utf-8")
        patched = 1

    doc = f"""# Phase 2fp — Assign→order_index cross-link

**Result:** `{result}`  
**Base:** `39a915c` (2fo) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## Semantic (RO, no invent)

`COrderAssignCommand` binds `units[]` (CPdxArray of `{{u32 type,u32 index}}`, mostly `HANDLE_TYPE_ARMY=0x33`) to **`order_index@+0x48`** — a battle-plan order **slot index**.

Same integer space:
- `COrderExecuteCommand.order_index@+0x30`
- `COrderDeleteCommand.order_index@+0x30`

`COrderNewFallbackCommand.subject_handle@+0x28` is a separate order-domain `{{type,index}}` (gate `0xbbb1e0`), **not** the Assign slot index.

## Live sight ({sight['elapsed']}s)

counts={json.dumps(sight['sight_counts'])}  
assign_indices={sight['crosslink']['assign_order_indices']}  
overlap∩Execute={sight['crosslink']['overlap_assign_execute']} overlap∩Delete={sight['crosslink']['overlap_assign_delete']}  
NF_seen={sight['fallback_seen']}

### Examples
```json
{json.dumps(army_examples[:4] or prior[:2], indent=2)}
```

```json
{json.dumps(live1, indent=2)}
```

**Next shortest blocker (NON-Post):** {next_blocker}
"""
    (ROOT / "docs" / "PHASE2FP_ASSIGN_ORDER_CROSSLINK.md").write_text(doc, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": result,
                "assigns": len(sight["assigns"]),
                "executes": len(sight["executes"]),
                "deletes": len(sight["deletes"]),
                "fallbacks": len(sight["fallbacks"]),
                "assign_indices": sight["crosslink"]["assign_order_indices"],
                "overlap_exec": sight["crosslink"]["overlap_assign_execute"],
                "overlap_del": sight["crosslink"]["overlap_assign_delete"],
                "army_examples_n": len(army_examples),
                "recipe_note_patched": patched,
                "pid": live1["pid"],
                "ui": live1["ui_date"],
                "hours": live1["hours"],
                "allow_post": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
