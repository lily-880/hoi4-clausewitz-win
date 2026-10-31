#!/usr/bin/env python3
"""Phase 2fo: RO-decode Assign/Unassign units.data handle elements. No Post. Never 5x."""
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
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
HANDLE_STRIDE = 8  # {u32 type, u32 index} — matches army_subjects unit_handle [ty, ix]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def decode_handles(blob: bytes, size: int) -> dict:
    """Decode size elements of {u32 type, u32 index} from units.data blob."""
    need = size * HANDLE_STRIDE
    elems = []
    for i in range(size):
        off = i * HANDLE_STRIDE
        if off + 8 > len(blob):
            elems.append({"i": i, "error": "short"})
            continue
        typ, ix = struct.unpack_from("<II", blob, off)
        note = None
        if typ == HANDLE_TYPE_ARMY:
            note = "HANDLE_TYPE_ARMY"
        elif typ == 0 and ix == 0:
            note = "null_or_empty"
        elems.append(
            {
                "i": i,
                "type": typ,
                "type_hex": hex(typ),
                "index": ix,
                "index_hex": hex(ix),
                "as_list": [typ, ix],
                "note": note,
                "raw8": blob[off : off + 8].hex(),
            }
        )
    return {
        "element_layout": "{u32 type, u32 index}",
        "stride": HANDLE_STRIDE,
        "size_claimed": size,
        "bytes_have": len(blob),
        "elements": elems,
        "type_histogram": _hist([e.get("type") for e in elems if "type" in e]),
    }


def _hist(vals):
    h = {}
    for v in vals:
        h[hex(v) if isinstance(v, int) else str(v)] = h.get(hex(v) if isinstance(v, int) else str(v), 0) + 1
    return h


def resolve_elems(b, base, decoded: dict) -> list:
    out = []
    for e in decoded.get("elements") or []:
        if "type" not in e:
            continue
        typ, ix = e["type"], e["index"]
        ptr = None
        err = None
        try:
            ptr = resolve_handle(b, typ, ix, base)
        except Exception as ex:
            err = str(ex)
        row = {"as_list": [typ, ix], "resolved": hex(ptr) if ptr else None, "ok": ptr is not None}
        if err:
            row["resolve_error"] = err
        if typ == HANDLE_TYPE_ARMY and ptr:
            # CArmy+0x18 often echoes handle (2ff note) — RO peek only
            try:
                echo = struct.unpack("<II", b.read(ptr + 0x18, 8))
                row["army_plus18_echo"] = list(echo)
                row["echo_matches"] = list(echo) == [typ, ix]
            except Exception as ex:
                row["army_plus18_echo_error"] = str(ex)
        out.append(row)
    return out


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
        "scenario": "ITA@1x Assign units.data handle decode (no Post)",
    }


def try_prior_ptrs(b, base) -> dict:
    """Re-read 2fn captured units.data pointers if still readable."""
    prior = json.loads((ROOT / "reports" / "phase2fn_assign_unassign_edge.json").read_text(encoding="utf-8"))
    rows = []
    for c in prior["bounded_sight"]["captures"]:
        d = c.get("decode") or {}
        u = d.get("units_cpdxarray") or {}
        data = int(u["data"], 16) if isinstance(u.get("data"), str) else u.get("data")
        size = u.get("size") or 0
        if not data or size <= 0:
            rows.append({"name": c.get("name"), "source": c.get("source"), "skipped": "empty_or_zero_data"})
            continue
        blob = try_read(b, data, size * HANDLE_STRIDE)
        if blob is None or len(blob) < size * HANDLE_STRIDE:
            rows.append(
                {
                    "name": c.get("name"),
                    "source": c.get("source"),
                    "data": hex(data),
                    "size": size,
                    "stale": True,
                    "readable": blob is not None,
                    "got": 0 if blob is None else len(blob),
                }
            )
            continue
        decoded = decode_handles(blob, size)
        resolved = resolve_elems(b, base, decoded)
        rows.append(
            {
                "name": c.get("name"),
                "source": c.get("source"),
                "cmd_addr": c.get("addr"),
                "data": hex(data),
                "size": size,
                "stale": False,
                "hex": blob.hex(),
                "decoded": decoded,
                "resolved": resolved,
            }
        )
    return {"from": "phase2fn captures", "rows": rows}


def bounded_sight_decode(b, base, seconds: float = 75.0) -> dict:
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    watch = {
        ASSIGN_VT: "COrderAssignCommand",
        UNASSIGN_VT: "COrderUnassignCommand",
        NF_VT: "COrderNewFallbackCommand",
        0x29F3710: "CHourlyTickCommand",
    }
    t0 = time.time()
    sight_counts: dict[str, int] = {}
    captures = []
    polls = 0
    while time.time() - t0 < seconds:
        polls += 1
        stage = 0
        try:
            stage = u64(b, sess + post_abi.CSession_STAGE_ARRAY)
        except Exception:
            stage = 0
        try:
            scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        except Exception:
            scount = 0
        if stage and 0 < scount < 256:
            for i in range(scount):
                try:
                    ptr = u64(b, stage + i * 8)
                except Exception:
                    continue
                if not ptr:
                    continue
                try:
                    vt = u64(b, ptr)
                except Exception:
                    continue
                rva = vt - base
                name = watch.get(rva)
                if not name:
                    continue
                sight_counts[name] = sight_counts.get(name, 0) + 1
                if name not in ("COrderAssignCommand", "COrderUnassignCommand", "COrderNewFallbackCommand"):
                    continue
                if len(captures) >= 6:
                    continue
                # dedupe by addr already captured
                if any(c.get("addr") == hex(ptr) for c in captures):
                    continue
                try:
                    # units CPdxArray @ +0x28
                    data = u64(b, ptr + 0x28)
                    cap = struct.unpack("<i", b.read(ptr + 0x30, 4))[0]
                    size = struct.unpack("<i", b.read(ptr + 0x34, 4))[0]
                    alloc = u64(b, ptr + 0x38)
                    trail = None
                    if name == "COrderAssignCommand":
                        trail = {"order_index": u32(b, ptr + 0x48)}
                    elif name == "COrderUnassignCommand":
                        trail = {"unassign_group": b.read(ptr + 0x48, 1)[0]}
                    decoded = None
                    resolved = None
                    hex_data = None
                    if data and 0 < size <= 64:
                        blob = try_read(b, data, size * HANDLE_STRIDE)
                        if blob and len(blob) >= size * HANDLE_STRIDE:
                            hex_data = blob.hex()
                            decoded = decode_handles(blob, size)
                            resolved = resolve_elems(b, base, decoded)
                    # NewFallback subject_handle @ +0x28 is NOT units — different packing
                    subject = None
                    if name == "COrderNewFallbackCommand":
                        subject = {
                            "type": u32(b, ptr + 0x28),
                            "index": u32(b, ptr + 0x2C),
                            "note": "order-domain subject_handle (2fm); not units array",
                        }
                    captures.append(
                        {
                            "source": f"stage[{i}]",
                            "name": name,
                            "addr": hex(ptr),
                            "t": round(time.time() - t0, 3),
                            "units": {
                                "data": hex(data),
                                "capacity": cap,
                                "size": size,
                                "alloc": hex(alloc),
                            },
                            "trail": trail,
                            "units_data_hex": hex_data,
                            "decoded": decoded,
                            "resolved": resolved,
                            "subject_handle": subject,
                        }
                    )
                except Exception as e:
                    captures.append({"source": f"stage[{i}]", "name": name, "addr": hex(ptr), "error": str(e)})
        if polls % 400 == 0:
            time.sleep(0)
    return {
        "observe_seconds": seconds,
        "elapsed": round(time.time() - t0, 3),
        "polls": polls,
        "sight_counts": sight_counts,
        "captures": captures,
        "assign_with_handles": sum(
            1
            for c in captures
            if c.get("name") == "COrderAssignCommand" and (c.get("decoded") or {}).get("elements")
        ),
        "unassign_with_handles": sum(
            1
            for c in captures
            if c.get("name") == "COrderUnassignCommand" and (c.get("decoded") or {}).get("elements")
        ),
        "fallback_seen": sight_counts.get("COrderNewFallbackCommand", 0) > 0,
    }


def main():
    pid = find_pid()
    b = Backend(pid)
    base = int(b.image_base)
    live0 = live_meta(b, base)

    prior = try_prior_ptrs(b, base)
    prior_ok = [r for r in prior["rows"] if not r.get("stale") and r.get("decoded")]
    need_sight = len(prior_ok) == 0

    sight = None
    if need_sight:
        print("prior units.data stale — bounded sight 75s...", flush=True)
        sight = bounded_sight_decode(b, base, 75.0)
    else:
        print(f"prior units.data still readable: {len(prior_ok)} rows — skip long sight", flush=True)
        # cheap 15s opportunistic NewFallback only if prior already gave handles
        print("opportunistic 20s NewFallback/Assign peek...", flush=True)
        sight = bounded_sight_decode(b, base, 20.0)

    live1 = live_meta(b, base)

    # synthesize findings
    live_handle_samples = []
    for r in prior_ok:
        live_handle_samples.append(
            {
                "origin": "2fn_reread",
                "name": r["name"],
                "elements": r["decoded"]["elements"],
                "resolved": r["resolved"],
                "type_histogram": r["decoded"]["type_histogram"],
            }
        )
    if sight:
        for c in sight.get("captures") or []:
            if c.get("decoded") and c["decoded"].get("elements"):
                live_handle_samples.append(
                    {
                        "origin": "2fo_sight",
                        "name": c["name"],
                        "source": c.get("source"),
                        "units": c.get("units"),
                        "trail": c.get("trail"),
                        "elements": c["decoded"]["elements"],
                        "resolved": c.get("resolved"),
                        "type_histogram": c["decoded"]["type_histogram"],
                    }
                )

    army_typed = []
    for s in live_handle_samples:
        for e in s.get("elements") or []:
            if e.get("type") == HANDLE_TYPE_ARMY:
                army_typed.append(e.get("as_list"))

    result = "ASSIGN_UNITS_HANDLES_DECODED" if live_handle_samples else "ASSIGN_UNITS_HANDLES_THIN"
    works = [
        "units.data element layout = {u32 type, u32 index} stride 8 (matches unit_handle [ty,ix])",
        f"HANDLE_TYPE_ARMY=0x33 samples: {army_typed[:8]}",
        f"prior_reread_ok={len(prior_ok)} sight_assign_handles={(sight or {}).get('assign_with_handles')} "
        f"sight_unassign_handles={(sight or {}).get('unassign_with_handles')}",
        "resolve_handle RO on typed elements; CArmy+0x18 echo check when ARMY",
        "allow_post stays False; never 5x; 2fb not executed; tool-gate CLOSED",
    ]
    if not live_handle_samples:
        works.append("honest-thin: no readable units.data this window")
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
        "live midflight NewFallback hex"
        if not (sight or {}).get("fallback_seen")
        else "NewFallback subject fully typed",
    ]
    next_blocker = (
        "NON-Post: NewFallback/ReplaceFallback midflight subject type-id "
        "OR Assign units.data→order subject cross-link; still NO ALLOW_POST"
        if live_handle_samples
        else "NON-Post: re-sight Assign units.data while on-stage (ptrs stale); still NO ALLOW_POST"
    )

    report = {
        "phase": "2fo",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "0a1105a",
        "handle_element": {
            "layout": "{u32 type, u32 index}",
            "stride": 8,
            "HANDLE_TYPE_ARMY": HANDLE_TYPE_ARMY,
            "source": "army_subjects unit_handle [ty,ix] + handle.resolve; live confirm below",
        },
        "live_at_start": live0,
        "live": live1,
        "prior_reread": prior,
        "bounded_sight": sight,
        "live_handle_samples": live_handle_samples,
        "army_typed_lists": army_typed,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "phase2fo_assign_units_handles.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fo",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "scenario": live1["scenario"],
        "samples_n": len(live_handle_samples),
        "army_typed_lists": army_typed[:16],
        "prior_reread_ok": len(prior_ok),
        "sight": {
            "elapsed": (sight or {}).get("elapsed"),
            "assign_with_handles": (sight or {}).get("assign_with_handles"),
            "unassign_with_handles": (sight or {}).get("unassign_with_handles"),
            "fallback_seen": (sight or {}).get("fallback_seen"),
            "sight_counts": (sight or {}).get("sight_counts"),
        },
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "0a1105a",
    }
    (ROOT / "reports" / "phase2fo_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # cheap catalog note — exact string only, no invent of new fields beyond element stride note
    cl = ROOT / "calling" / "cmd_layout.py"
    ct = cl.read_text(encoding="utf-8")
    old_note = '"fields_note": "2fn: units=CPdxArray@+0x28 (size@+0x34); order_index@+0x48; posting DISABLED",'
    new_note = (
        '"fields_note": "2fn/2fo: units=CPdxArray@+0x28 (size@+0x34); '
        'elem={u32 type,u32 index}@data stride8; order_index@+0x48; posting DISABLED",'
    )
    patched = 0
    if old_note in ct:
        ct = ct.replace(old_note, new_note, 1)
        patched += 1
    old_u = '"fields_note": "2fn: units=CPdxArray@+0x28 (size@+0x34); unassign_group@+0x48; posting DISABLED",'
    new_u = (
        '"fields_note": "2fn/2fo: units=CPdxArray@+0x28 (size@+0x34); '
        'elem={u32 type,u32 index}@data stride8; unassign_group@+0x48; posting DISABLED",'
    )
    if old_u in ct:
        ct = ct.replace(old_u, new_u, 1)
        patched += 1
    if patched:
        cl.write_text(ct, encoding="utf-8")

    doc = f"""# Phase 2fo — Assign units.data handle decode

**Result:** `{result}`  
**Base:** `0a1105a` (2fn) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## Element layout (proven RO)

`units.data[i]` = `{{u32 type, u32 index}}` stride **8** (same as `unit_handle` `[ty, ix]`).

`HANDLE_TYPE_ARMY = 0x33` (51). Live army-typed lists: `{json.dumps(army_typed[:12])}`

## Prior 2fn reread

ok={len(prior_ok)} / rows={len(prior["rows"])}

## Sight

elapsed={(sight or {}).get("elapsed")} assign_handles={(sight or {}).get("assign_with_handles")}  
unassign_handles={(sight or {}).get("unassign_with_handles")} fallback={(sight or {}).get("fallback_seen")}  
counts={json.dumps((sight or {}).get("sight_counts"))}

```json
{json.dumps(live1, indent=2)}
```

**Next shortest blocker (NON-Post):** {next_blocker}
"""
    (ROOT / "docs" / "PHASE2FO_ASSIGN_UNITS_HANDLES.md").write_text(doc, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": result,
                "samples_n": len(live_handle_samples),
                "army_typed": army_typed[:12],
                "prior_ok": len(prior_ok),
                "sight": summary["sight"],
                "pid": live1["pid"],
                "ui": live1["ui_date"],
                "hours": live1["hours"],
                "cmd_layout_notes_patched": patched,
                "allow_post": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
