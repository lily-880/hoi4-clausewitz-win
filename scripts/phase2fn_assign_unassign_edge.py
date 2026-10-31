#!/usr/bin/env python3
"""Phase 2fn: Assign/Unassign edge deepen (RO) + cheap type-id polish. No Post. Never 5x."""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
sys.path.insert(0, str(ROOT / "scripts"))

from config import allow_post
from process import Backend, find_pid
import cmd_layout
import post_abi
import phase2bm_midflight_ready as mf

assert allow_post() is False

ASSIGN_VT = cmd_layout.ORDERS["COrderAssignCommand"]["vt"]
UNASSIGN_VT = cmd_layout.ORDERS["COrderUnassignCommand"]["vt"]
ASSIGN_SIZE = 0x50  # catalog size (embedded on vt line in ORDERS)
UNASSIGN_SIZE = 0x50

# CPdxArray (2de/2fm)
CPDX = {"data": 0x0, "capacity": 0x8, "size": 0xC, "alloc": 0x10, "stride": 0x18}

ASSIGN_FIELDS = {
    "units_data": 0x28,
    "units_capacity": 0x30,
    "units_count": 0x34,  # CPdxArray.size
    "units_alloc": 0x38,
    "order_index": 0x48,
    "assign_to_minimum_order": 0x4C,  # u8/u32 trailing; keep prior name
}
UNASSIGN_FIELDS = {
    "units_data": 0x28,
    "units_capacity": 0x30,
    "units_count": 0x34,
    "units_alloc": 0x38,
    "unassign_group": 0x48,
    "unassign_army_group_instances": 0x49,
}

# Cheap type-id polish from catalogs/prior (no invent)
HANDLE_TYPE_TABLE = {
    "HANDLE_TYPE_ARMY": {"value": 0x33, "dec": 51, "source": "reports/phase2ff_eth_army_path_ro.json + live peeks lo=0x33"},
    "note": "NewFallback subject_handle type field still open (order-domain gate 0xbbb1e0); not proven equal to ARMY",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def decode_assign_unassign(blob: bytes, name: str) -> dict:
    need = 0x50
    if len(blob) < need:
        return {"error": f"short {len(blob)}", "hex": blob.hex()}
    fields = ASSIGN_FIELDS if "Assign" in name and "Unassign" not in name else UNASSIGN_FIELDS
    data = struct.unpack_from("<Q", blob, fields["units_data"])[0]
    cap = struct.unpack_from("<i", blob, fields["units_capacity"])[0]
    size = struct.unpack_from("<i", blob, fields["units_count"])[0]
    alloc = struct.unpack_from("<Q", blob, fields["units_alloc"])[0]
    out = {
        "layout": name,
        "units_cpdxarray": {
            "data": hex(data),
            "capacity": cap,
            "size": size,
            "alloc": hex(alloc),
        },
        "hex50": blob[:need].hex(),
    }
    if name == "COrderAssignCommand":
        out["order_index"] = struct.unpack_from("<I", blob, 0x48)[0]
        out["assign_to_minimum_order"] = blob[0x4C]
    else:
        out["unassign_group"] = blob[0x48]
        out["unassign_army_group_instances"] = blob[0x49]
    return out


def decode_peek_qwords(qwords: list[str], label: str) -> dict:
    """Honest decode of prior post-stage peeks — may be reused memory."""
    qs = [int(x, 16) for x in qwords]
    rows = []
    army_type_hits = []
    for i, v in enumerate(qs):
        lo, hi = v & 0xFFFFFFFF, v >> 32
        row = {"off": hex(i * 8), "u64": hex(v), "lo": hex(lo), "hi": hex(hi)}
        if lo == 0x33:
            row["lo_note"] = "HANDLE_TYPE_ARMY"
            army_type_hits.append(hex(i * 8))
        rows.append(row)
    # overlay assuming object still starts at +0 (often false post-stage)
    overlay = None
    if len(qs) >= 10:
        overlay = {
            "if_units_at_0x28": {
                "units_data": hex(qs[5]),
                "units_capacity_lo": qs[6] & 0xFFFFFFFF,
                "note": "post-stage peek unreliable; prefer on-stage hex",
            }
        }
    return {
        "label": label,
        "rows": rows,
        "army_type_0x33_at_offs": army_type_hits,
        "overlay_attempt": overlay,
        "credibility": "LOW_post_stage_reuse — stage hex preferred (2ev note)",
    }


def load_stage_neighbors() -> dict:
    ex = json.loads((ROOT / "reports" / "phase2ex_assign_edge_heap.json").read_text(encoding="utf-8"))
    fa = json.loads((ROOT / "reports" / "phase2fa_eth_execlist.json").read_text(encoding="utf-8"))
    return {
        "from_2ex_ita": {
            "sight_counts": ex.get("sight_counts"),
            "sight_first": ex.get("sight_first"),
            "neighbors_note": "HourlyTick dominant; Assign stage[9]; Unassign stage[13]; Cancel co-sighted",
            "assign_hits_n": ex.get("assign_hits_n"),
            "vt": {"Assign": "0x2a84498", "Unassign": "0x2a84550"},
        },
        "from_2fa_eth": {
            "sight_counts": (fa.get("observe") or {}).get("sight_counts"),
            "assign_family_sightings": (fa.get("observe") or {}).get("assign_family_sightings"),
            "neighbors_note": "Assign on stage[1]/[45..47]; StrategicRedeploy stage[48]; HourlyTick stage[0]",
        },
    }


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
        "scenario": "ITA@1x Assign/Unassign edge deepen (no Post)",
        "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1",
    }


def bounded_sight(b, base, seconds: float = 75.0) -> dict:
    """Poll stage/pending for Assign/Unassign; capture on-stage hex. Never 5x."""
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    watch = {
        ASSIGN_VT: "COrderAssignCommand",
        UNASSIGN_VT: "COrderUnassignCommand",
        cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]: "COrderNewFallbackCommand",
        cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
        0x29F3710: "CHourlyTickCommand",
    }
    t0 = time.time()
    sight_counts: dict[str, int] = {}
    captures = []
    neighbors_co = []
    polls = 0
    while time.time() - t0 < seconds:
        polls += 1
        stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
        scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
        hits_this = []

        def consider(ptr, source):
            vt = try_u64(b, ptr)
            if vt is None:
                return
            rva = vt - base
            name = watch.get(rva)
            if not name:
                return
            sight_counts[name] = sight_counts.get(name, 0) + 1
            hits_this.append(name)
            if name in ("COrderAssignCommand", "COrderUnassignCommand", "COrderNewFallbackCommand"):
                if len(captures) < 8:
                    try:
                        blob = b.read(ptr, 0x50)
                        captures.append(
                            {
                                "source": source,
                                "name": name,
                                "addr": hex(ptr),
                                "vt_rva": hex(rva),
                                "t": round(time.time() - t0, 3),
                                "decode": decode_assign_unassign(blob, name)
                                if name != "COrderNewFallbackCommand"
                                else {"hex50": blob.hex()},
                            }
                        )
                    except Exception as e:
                        captures.append({"source": source, "name": name, "addr": hex(ptr), "error": str(e)})

        if stage and 0 < scount < 256:
            for i in range(scount):
                ptr = try_u64(b, stage + i * 8)
                if ptr:
                    consider(ptr, f"stage[{i}]")
        cur, seen = pending_h, set()
        while cur and cur not in seen and len(seen) < 32:
            seen.add(cur)
            consider(cur, "pending")
            nxt = try_u64(b, cur + 8)
            if not nxt or nxt == cur:
                break
            cur = nxt
        if any(n in ("COrderAssignCommand", "COrderUnassignCommand") for n in hits_this):
            neighbors_co.append(
                {
                    "t": round(time.time() - t0, 3),
                    "hits": hits_this,
                    "stage_count": scount,
                }
            )
        # tight poll but yield occasionally
        if polls % 500 == 0:
            time.sleep(0)
    return {
        "observe_seconds": seconds,
        "elapsed": round(time.time() - t0, 3),
        "polls": polls,
        "sight_counts": sight_counts,
        "captures": captures,
        "neighbor_windows": neighbors_co[:20],
        "assign_seen": sight_counts.get("COrderAssignCommand", 0) > 0,
        "unassign_seen": sight_counts.get("COrderUnassignCommand", 0) > 0,
        "fallback_seen": sight_counts.get("COrderNewFallbackCommand", 0) > 0,
    }


def patch_catalogs():
    cl = ROOT / "calling" / "cmd_layout.py"
    ct = cl.read_text(encoding="utf-8")
    old_a = (
        '"fields": {"units_data": 0x28, "units_count": 0x34, "order_index": 0x48, "assign_to_minimum_order": 0x4C},'
    )
    new_a = (
        f'"fields": {json.dumps(ASSIGN_FIELDS)},\n'
        '        "fields_note": "2fn: units=CPdxArray@+0x28 (size@+0x34); order_index@+0x48; posting DISABLED",'
    )
    # only first ORDERS occurrence — be careful; count matches
    # Prefer unique context with COrderAssignCommand nearby
    needle_a = (
        '    "COrderAssignCommand": {\n'
        "        \"factory\": 0x18cfca0,\n"
        '        "vt": 0x2A84498, "type_id": 0x303E, "factory_idx": 3350,  # Phase 2fg: tid-0x2328 formula "size": 0x50,\n'
        '        "clone": 0x18CD5B0, "serialize": 0x18E80F0, "deserialize": 0x18E1A70, "execute": 0x18D41B0,\n'
        '        "isvalid": 0x18de900,\n'
        '        "isvalid_kind": "FN",\n'
        '        "fields": {"units_data": 0x28, "units_count": 0x34, "order_index": 0x48, "assign_to_minimum_order": 0x4C},\n'
        "    },"
    )
    repl_a = (
        '    "COrderAssignCommand": {\n'
        "        \"factory\": 0x18cfca0,\n"
        '        "vt": 0x2A84498, "type_id": 0x303E, "factory_idx": 3350,  # Phase 2fg: tid-0x2328 formula "size": 0x50,\n'
        '        "clone": 0x18CD5B0, "serialize": 0x18E80F0, "deserialize": 0x18E1A70, "execute": 0x18D41B0,\n'
        '        "isvalid": 0x18de900,\n'
        '        "isvalid_kind": "FN",\n'
        f'        "fields": {json.dumps(ASSIGN_FIELDS)},\n'
        '        "fields_note": "2fn: units=CPdxArray@+0x28 (size@+0x34); order_index@+0x48; posting DISABLED",\n'
        "    },"
    )
    assert ct.count(needle_a) == 1, f"assign block count={ct.count(needle_a)}"
    ct = ct.replace(needle_a, repl_a, 1)

    needle_u = (
        '    "COrderUnassignCommand": {\n'
        "        \"factory\": 0x18d09b0,\n"
        '        "vt": 0x2A84550, "type_id": 0x304D, "factory_idx": 3365,  # Phase 2fg: tid-0x2328 formula "size": 0x50,\n'
        '        "clone": 0x18CEBB0, "serialize": 0x18E91B0, "deserialize": 0x18E2EE0, "execute": 0x18DB050,\n'
        '        "isvalid": 0x18e01d0,\n'
        '        "isvalid_kind": "FN",\n'
        '        "fields": {"units_data": 0x28, "units_count": 0x34, "unassign_group": 0x48, "unassign_army_group_instances": 0x49},\n'
        "    },"
    )
    repl_u = (
        '    "COrderUnassignCommand": {\n'
        "        \"factory\": 0x18d09b0,\n"
        '        "vt": 0x2A84550, "type_id": 0x304D, "factory_idx": 3365,  # Phase 2fg: tid-0x2328 formula "size": 0x50,\n'
        '        "clone": 0x18CEBB0, "serialize": 0x18E91B0, "deserialize": 0x18E2EE0, "execute": 0x18DB050,\n'
        '        "isvalid": 0x18e01d0,\n'
        '        "isvalid_kind": "FN",\n'
        f'        "fields": {json.dumps(UNASSIGN_FIELDS)},\n'
        '        "fields_note": "2fn: units=CPdxArray@+0x28 (size@+0x34); unassign_group@+0x48; posting DISABLED",\n'
        "    },"
    )
    assert ct.count(needle_u) == 1, f"unassign block count={ct.count(needle_u)}"
    ct = ct.replace(needle_u, repl_u, 1)
    cl.write_text(ct, encoding="utf-8")

    # army_subjects recipes
    asp = ROOT / "calling" / "army_subjects.py"
    at = asp.read_text(encoding="utf-8")

    def replace_fn(src, name, new_body):
        start = src.find(f"def {name}(")
        assert start >= 0, name
        nxt = src.find("\ndef ", start + 1)
        assert nxt > start
        return src[:start] + new_body.rstrip() + "\n\n" + src[nxt + 1 :]

    new_assign = '''def order_assign_recipe(unit_handles: list[list[int]] | None = None,
                         order_index: int = 0,
                         assign_to_minimum_order: int = 0) -> dict[str, Any]:
    """COrderAssignCommand — RO only. units=CPdxArray@+0x28 (2fn)."""
    units = unit_handles or []
    return {
        "units_data_off": 0x28,
        "units_capacity_off": 0x30,
        "units_count_off": 0x34,
        "units_alloc_off": 0x38,
        "unit_handles": [list(h) for h in units],
        "units_count": len(units),
        "order_index_off": 0x48,
        "order_index": order_index,
        "assign_to_minimum_order_off": 0x4C,
        "assign_to_minimum_order": assign_to_minimum_order,
        "cpdxarray": "data@0 cap@8 size@0xC alloc@0x10",
        "note": "2fn: Assign edge; vectors game-alloc; posting DISABLED",
        "posting": "DISABLED",
    }
'''
    new_unassign = '''def order_unassign_recipe(units: list[list[int]] | None = None,
                          unassign_group: int = 0,
                          unassign_army_group_instances: int = 0) -> dict[str, Any]:
    """COrderUnassignCommand — RO only. units=CPdxArray@+0x28 (2fn)."""
    units = units or []
    return {
        "units_data_off": 0x28,
        "units_capacity_off": 0x30,
        "units_count_off": 0x34,
        "units_alloc_off": 0x38,
        "unit_handles": [list(h) for h in units],
        "units_count": len(units),
        "unassign_group_off": 0x48,
        "unassign_group": unassign_group,
        "unassign_army_group_instances_off": 0x49,
        "unassign_army_group_instances": unassign_army_group_instances,
        "cpdxarray": "data@0 cap@8 size@0xC alloc@0x10",
        "note": "2fn: Unassign edge; posting DISABLED",
        "posting": "DISABLED",
    }
'''
    at = replace_fn(at, "order_assign_recipe", new_assign)
    at = replace_fn(at, "order_unassign_recipe", new_unassign)
    asp.write_text(at, encoding="utf-8")


def main():
    pid = find_pid()
    b = Backend(pid)
    base = int(b.image_base)
    live = live_meta(b, base)

    ev = json.loads((ROOT / "reports" / "phase2ev_ro_deepen.json").read_text(encoding="utf-8"))
    peek_assign = decode_peek_qwords(
        ev["ita_unassign_assign_peek"]["assign"]["first_qwords"], "COrderAssignCommand"
    )
    peek_unassign = decode_peek_qwords(
        ev["ita_unassign_assign_peek"]["unassign"]["first_qwords"], "COrderUnassignCommand"
    )
    neighbors = load_stage_neighbors()

    print("starting bounded sight 75s...", flush=True)
    sight = bounded_sight(b, base, 75.0)
    live2 = live_meta(b, base)

    patch_catalogs()
    import importlib

    importlib.reload(cmd_layout)
    import army_subjects

    importlib.reload(army_subjects)
    af = cmd_layout.ORDERS["COrderAssignCommand"]["fields"]
    uf = cmd_layout.ORDERS["COrderUnassignCommand"]["fields"]
    assert af["units_capacity"] == 0x30 and af["units_count"] == 0x34
    assert uf["units_alloc"] == 0x38

    result = "ASSIGN_UNASSIGN_EDGE_DEEPENED"
    works = [
        "Assign/Unassign units@+0x28 = CPdxArray (data/cap/size/alloc) sibling MassCancel/NewFallback",
        f"Assign fields {ASSIGN_FIELDS}",
        f"Unassign fields {UNASSIGN_FIELDS}",
        "Stage neighbors catalogued from 2ex ITA + 2fa ETH (HourlyTick/Cancel/Strategic co-sight)",
        "order_assign_recipe corrected (was wrong subject_or_vec sketch)",
        "HANDLE_TYPE_ARMY=0x33 cheap type-id polish; NewFallback subject type still open",
        f"bounded sight {sight['elapsed']}s polls={sight['polls']} assign_seen={sight['assign_seen']} unassign_seen={sight['unassign_seen']}",
        "allow_post stays False; never 5x; 2fb not executed; tool-gate CLOSED",
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
        "live midflight NewFallback hex" if not sight["fallback_seen"] else "NewFallback hex fully decoded",
    ]
    if not sight["assign_seen"] and not sight["unassign_seen"]:
        works.append("bounded sight honest-empty for Assign/Unassign this window (prior 2ex/2ev still authoritative)")
    next_blocker = (
        "NON-Post: on-stage Assign/Unassign hex with nonzero units_count "
        "OR NewFallback subject type-id from midflight; still NO ALLOW_POST"
    )

    report = {
        "phase": "2fn",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "live": live2,
        "live_at_start": live,
        "parent_sha_base": "87bd306",
        "assign_fields": ASSIGN_FIELDS,
        "unassign_fields": UNASSIGN_FIELDS,
        "cpdxarray": CPDX,
        "handle_type_table_polish": HANDLE_TYPE_TABLE,
        "prior_peek_decode": {"assign": peek_assign, "unassign": peek_unassign},
        "stage_neighbors": neighbors,
        "bounded_sight": sight,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "phase2fn_assign_unassign_edge.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fn",
        "result": result,
        "scenario": live2["scenario"],
        "allow_post": False,
        "tool_gate": "CLOSED",
        "pid": live2["pid"],
        "ui_date": live2["ui_date"],
        "hours": live2["hours"],
        "assign_fields": ASSIGN_FIELDS,
        "unassign_fields": UNASSIGN_FIELDS,
        "sight": {
            "elapsed": sight["elapsed"],
            "assign_seen": sight["assign_seen"],
            "unassign_seen": sight["unassign_seen"],
            "fallback_seen": sight["fallback_seen"],
            "sight_counts": sight["sight_counts"],
            "captures_n": len(sight["captures"]),
        },
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "87bd306",
    }
    (ROOT / "reports" / "phase2fn_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    doc = f"""# Phase 2fn — Assign/Unassign edge deepen

**Result:** `{result}`  
**Base:** `87bd306` (2fm) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## CPdxArray units @ +0x28 (both)

| off | Assign / Unassign |
|-----|-------------------|
| +0x28 | units_data |
| +0x30 | units_capacity |
| +0x34 | units_count (size) |
| +0x38 | units_alloc |

Sibling fit: MassCancel / NewFallback units packing (2fm).

## Trailing fields

- **Assign:** `order_index@+0x48`, `assign_to_minimum_order@+0x4C`
- **Unassign:** `unassign_group@+0x48`, `unassign_army_group_instances@+0x49`

## Stage neighbors (prior)

- **2ex ITA:** HourlyTick · Assign stage[9] · Unassign stage[13] · Cancel
- **2fa ETH:** Assign stage[1]/[45..47] · StrategicRedeploy · HourlyTick

## Type-id polish

`HANDLE_TYPE_ARMY = 0x33` (51). NewFallback `subject_handle` type still open (order-domain).

## Live sight ({sight['elapsed']}s)

assign_seen={sight['assign_seen']} unassign_seen={sight['unassign_seen']} fallback_seen={sight['fallback_seen']}  
counts={json.dumps(sight['sight_counts'])}

```json
{json.dumps(live2, indent=2)}
```

**Next shortest blocker (NON-Post):** {next_blocker}
"""
    (ROOT / "docs" / "PHASE2FN_ASSIGN_UNASSIGN_EDGE.md").write_text(doc, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": result,
                "assign_fields": af,
                "unassign_fields": uf,
                "sight": summary["sight"],
                "pid": live2["pid"],
                "ui": live2["ui_date"],
                "hours": live2["hours"],
                "allow_post": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
