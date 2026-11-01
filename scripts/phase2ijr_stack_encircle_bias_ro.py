#!/usr/bin/env python3
"""Phase 2ijr NON-Post: stack-depth / encirclement-bias perception polish (proven CA fields only).

Live RO only. NO Post / Instant / PATH densify / midflight / ring_embed exec /
tool-gate / ask ALLOW_POST. Do NOT invent org/str or controller_tag as proven.
Theater/frontline live handles: honest STUBBED. Province adjacency graph: honest EMPTY
(not proven — no invented neighbor edges).
"""
from __future__ import annotations

import json
import os
import struct
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from army_subjects import (
    iter_armies_by_index,
    strategic_redeploy_recipe,
    cancel_movement_recipe,
)
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijr_stack_encircle_bias_ro.json"
SUMMARY = ROOT / "reports" / "phase2ijr_stack_encircle_bias_ro_summary.json"
DOC = ROOT / "docs" / "PHASE2IJR_STACK_ENCIRCLE_BIAS_RO.md"

GS_YEAR = 0x478
GS_DAY = 0x484
CA_PROVINCE_PTR = 0x1F0
CP_ID = 0xA4


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def continuum_live(b, base, pid, tag, scenario):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = i32(b, gs + GS_YEAR)
    day_index = i32(b, gs + GS_DAY)
    ui = None
    if 1 <= year <= 3000 and 0 <= day_index < 400:
        try:
            ui = (datetime(year, 1, 1) + timedelta(days=int(day_index))).strftime("%Y-%m-%d")
        except Exception:
            ui = None
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER) if sess else None
        if server:
            pending = try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
        stage = try_u32(b, sess + post_abi.CSession_STAGE_COUNT) if sess else None
        drain = try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER) if sess else None
        exec_c = try_u32(b, sess + post_abi.CSession_EXEC_COUNTER) if sess else None
    except Exception:
        pass
    clock_class = "CONTINUOUS" if not (year == 1936 and day_index < 48) else "RELOAD_OR_NEW_CAMPAIGN"
    return {
        "pid": pid,
        "year": year,
        "day_index": day_index,
        "ui_date": ui,
        "clock_class": clock_class,
        "speed_policy": "pause-or-1x only (never write speed beyond pause/1x)",
        "country_tag_filter": tag,
        "scenario": scenario,
        "drain": drain,
        "exec": exec_c,
        "pending": pending,
        "stage_count": stage,
        "allow_post": False,
    }


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + 0x518)


def scan_ita_armies(b, base, tag: int):
    rows = []
    for lo in range(0, 5000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    return rows


def main() -> int:
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    assert allow_post() is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    scenario = "ITA@1x stack-depth / encirclement-bias perception RO (no Post)"

    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(1.0)
    s1 = continuum_live(b, base, pid, tag, scenario)
    calendar_ok = (
        s1["clock_class"] == "CONTINUOUS"
        and (s1["drain"] or 0) >= (s0["drain"] or 0)
        and (s1["exec"] or 0) >= (s0["exec"] or 0)
    )

    rows = scan_ita_armies(b, base, tag)
    handle_ok_n = sum(1 for r in rows if r.get("handle_ok"))
    prov_ok_n = sum(1 for r in rows if r.get("province_id_ok"))
    all_subject_ok = len(rows) > 0 and handle_ok_n == len(rows) and prov_ok_n == len(rows)

    prov_to_armies: dict[int, list[dict]] = defaultdict(list)
    ptr_match_n = 0
    cp_id_match_n = 0

    for r in rows:
        army = r["army"]
        try:
            pref_direct = u64(b, army + CA_PROVINCE_PTR)
        except Exception:
            pref_direct = None
        ptr_match = bool(pref_direct and r["province"] and pref_direct == r["province"])
        if ptr_match:
            ptr_match_n += 1
        cp_id = None
        try:
            if r["province"]:
                cp_id = u32(b, r["province"] + CP_ID)
        except Exception:
            cp_id = None
        if cp_id == r["province_id"]:
            cp_id_match_n += 1
        prov_to_armies[r["province_id"]].append(
            {
                "index": r["index"],
                "handle": list(r["handle"]),
                "army": hex(army),
                "province_id": r["province_id"],
                "country_tag": r["country_tag"],
                "handle_ok": r["handle_ok"],
                "province_id_ok": r["province_id_ok"],
                "province_ptr_0x1f0_match": ptr_match,
                "cp_id_match": cp_id == r["province_id"],
            }
        )

    # Stack-depth ranked clusters (encirclement-bias perception primitive — RO)
    stack_hist: dict[str, int] = defaultdict(int)
    ranked_stacks = []
    for pid_, armies in prov_to_armies.items():
        depth = len(armies)
        stack_hist[str(depth)] += 1
        ranked_stacks.append(
            {
                "province_id": pid_,
                "stack_depth": depth,
                "armies": armies,
                "concentration_score": depth,  # RO proxy only; no adjacency graph
            }
        )
    ranked_stacks.sort(key=lambda x: (-x["stack_depth"], x["province_id"]))
    multi = [s for s in ranked_stacks if s["stack_depth"] >= 2]
    singleton_n = sum(1 for s in ranked_stacks if s["stack_depth"] == 1)
    max_stack = ranked_stacks[0]["stack_depth"] if ranked_stacks else 0
    armies_in_multi = sum(s["stack_depth"] for s in multi)
    concentration_ratio = (armies_in_multi / len(rows)) if rows else 0.0

    # Top-N stacks → Strategic/Cancel recipe catalogs (DISABLED posting)
    top_n = multi[:5]
    recipe_catalog = []
    for st in top_n:
        # pick first army as subject; dest = same province (docs-only, no Post)
        subj = next(r for r in rows if r["index"] == st["armies"][0]["index"])
        recipe_catalog.append(
            {
                "province_id": st["province_id"],
                "stack_depth": st["stack_depth"],
                "strategic_redeploy_sample": strategic_redeploy_recipe(
                    subj, int(st["province_id"])
                ),
                "cancel_movement_for_stack": cancel_movement_recipe(
                    [next(r for r in rows if r["index"] == a["index"]) for a in st["armies"]]
                ),
                "posting": "DISABLED",
            }
        )

    # Honest empty: province adjacency / frontier ring not proven
    adjacency_graph = {
        "state": "HONEST_EMPTY",
        "note": "No proven province-neighbor edges in RO offsets; do NOT invent adjacency for encircle math",
        "used_for_bias": False,
    }

    gates = {
        "G1": {"state": "ACCEPTABLE", "via": "Strategic-only (2ijj)"},
        "G2": {"state": "RO_PREP_HIT_LIVE_STUBBED", "via": "2ijk INLINE_BLOB"},
        "G3": {"state": "PARKED", "via": "peacetime Instant"},
        "G4": {"state": "HARD_DENY_UNTIL_HUMAN", "via": "CLAUSEWITZ_ALLOW_POST=1; executor cannot flip"},
        "G5": {"state": "CLOSED_NOT_OPENED", "via": "tool-gate after G4"},
        "G6": {"state": "FORBIDDEN_NOW", "via": "ONE Strategic Post @1x after G4+G5"},
    }

    theater_frontline = {
        "live_handle_scan": "STUBBED",
        "note": "HANDLE_TYPE_ARMY=0x33 proven only; theater/frontline handle types NOT proven — do not invent",
        "recipes_docs_only": True,
        "controller_tag_cprovince_0x58": "HYPOTHESIS_STRONG_2ct_NOT_PROVEN — not used as feed",
        "org_str_carmy_0x520_0x6ec": "HYPOTHESIS_ONLY_2ct_REJECTED — not invented",
    }

    polish_ok = (
        all_subject_ok
        and ptr_match_n == len(rows)
        and cp_id_match_n == len(rows)
        and len(ranked_stacks) > 0
        and max_stack >= 1
    )

    result_code = (
        "STACK_ENCIRCLE_BIAS_RO_HIT"
        if polish_ok and calendar_ok and allow_post() is False
        else "STACK_ENCIRCLE_BIAS_RO_PARTIAL"
    )

    report = {
        "phase": "2ijr",
        "result": result_code,
        "allow_post": False,
        "posting": "DISABLED",
        "hard_rules": [
            "no Instant empty / Inst70/ARR88/tri70 poll",
            "no PATH/OG50-only densify",
            "no long midflight empty poll",
            "no Post inject / 2fb/2gk / tool-gate / ring_embed live",
            "no ask ALLOW_POST / no invent org/str or controller_tag as proven",
            "no invent province adjacency edges",
        ],
        "live_s0": s0,
        "live_s1": s1,
        "calendar_ok": calendar_ok,
        "drain_delta": (s1["drain"] or 0) - (s0["drain"] or 0),
        "exec_delta": (s1["exec"] or 0) - (s0["exec"] or 0),
        "proven_fields_used": {
            "CA_HANDLE": "0x18",
            "CA_PROVINCE_ID": "0x28",
            "CA_COUNTRY_TAG": "0x1e0",
            "CA_PROVINCE_PTR": "0x1f0",
            "CP_ID": "0xa4",
            "HANDLE_TYPE_ARMY": "0x33",
        },
        "stack_encircle_bias": {
            "country_tag_filter": tag,
            "army_count": len(rows),
            "handle_ok_count": handle_ok_n,
            "province_id_ok_count": prov_ok_n,
            "province_ptr_match_count": ptr_match_n,
            "cp_id_match_count": cp_id_match_n,
            "all_subject_ok": all_subject_ok,
            "unique_province_count": len(ranked_stacks),
            "singleton_province_count": singleton_n,
            "multi_army_province_count": len(multi),
            "max_stack_depth": max_stack,
            "armies_in_multi_stacks": armies_in_multi,
            "concentration_ratio": round(concentration_ratio, 4),
            "stack_depth_histogram": dict(sorted(stack_hist.items(), key=lambda kv: int(kv[0]))),
            "ranked_stacks_top": ranked_stacks[:12],
            "multi_army_clusters": multi,
            "adjacency_graph": adjacency_graph,
            "perception_primitive": {
                "name": "stack_depth_concentration_RO",
                "inputs": ["CA_HANDLE", "CA_PROVINCE_ID", "CA_COUNTRY_TAG", "CA_PROVINCE_PTR", "CP_ID"],
                "outputs": ["ranked_stacks", "concentration_ratio", "stack_depth_histogram"],
                "encirclement_bias_note": "Prefer acting on/around high stack_depth provinces when Post opens; adjacency STILL empty until proven",
            },
        },
        "strategic_recipe_catalog_top_stacks": recipe_catalog,
        "theater_frontline": theater_frontline,
        "gates_g1_g6": gates,
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "<=+1pp perception polish (stack-depth / concentration; no adjacency invent)",
            "crossed_70": False,
            "note": "~70% NOT crossed while G2 live / G4+ block Post",
        },
        "next_shortest_blocker": "Human G4 CLAUSEWITZ_ALLOW_POST=1 (executor cannot flip) → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x",
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijr",
                "result": result_code,
                "allow_post": False,
                "pid": pid,
                "ui_date": s1["ui_date"],
                "day_index": s1["day_index"],
                "clock_class": s1["clock_class"],
                "drain": s1["drain"],
                "exec": s1["exec"],
                "army_count": len(rows),
                "unique_provinces": len(ranked_stacks),
                "multi_army": len(multi),
                "max_stack": max_stack,
                "concentration_ratio": round(concentration_ratio, 4),
                "adjacency": "HONEST_EMPTY",
                "calendar_ok": calendar_ok,
                "polish_ok": polish_ok,
                "crossed_70": False,
                "next": report["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    DOC.write_text(
        f"""# Phase 2ijr — Stack-depth / encirclement-bias perception (RO)

**Result:** `{result_code}`  
**allow_post:** False (never flipped)  
**Live:** pid={pid} ITA ui={s1['ui_date']} day={s1['day_index']} clock={s1['clock_class']} drain={s1['drain']} exec={s1['exec']}

## What this adds

- Ranked province stacks by depth (proven CA fields only).
- Concentration ratio = armies in multi-army provinces / total armies.
- Stack-depth histogram + top multi-army clusters.
- Strategic/Cancel recipe catalog for top stacks — **posting DISABLED**.
- Province adjacency graph: **HONEST_EMPTY** (not invented).

## Proven fields only

| Field | Offset |
|-------|--------|
| CA_HANDLE | +0x18 |
| CA_PROVINCE_ID | +0x28 |
| CA_COUNTRY_TAG | +0x1E0 |
| CA_PROVINCE_PTR | +0x1F0 |
| CP_ID | +0xA4 |
| HANDLE_TYPE_ARMY | 0x33 |

## Live snapshot

- armies={len(rows)} unique_provinces={len(ranked_stacks)} multi={len(multi)} max_stack={max_stack}
- concentration_ratio={concentration_ratio:.4f}
- handle/province/ptr/cp_id match: {handle_ok_n}/{prov_ok_n}/{ptr_match_n}/{cp_id_match_n} of {len(rows)}

## Gates G1–G6

- G1 ACCEPTABLE Strategic-only
- G2 RO prep HIT / live STUBBED
- G3 Instant PARKED
- G4 HARD_DENY until human CLAUSEWITZ_ALLOW_POST=1
- G5 CLOSED_NOT_OPENED
- G6 FORBIDDEN now

## Stubbed / not invented

- Theater/frontline live handles STUBBED
- CProvince+0x58 controller_tag hypothesis_strong — not fed as proven
- org/str @0x520/0x6ec HYPOTHESIS_ONLY — not invented
- Province neighbor edges: HONEST_EMPTY

## Path C honesty

~60–62% baseline; this slice ≤+1pp perception polish; **~70% NOT crossed**.

## Next

Human G4 → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x.

*Phase 2ijr — 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )

    print(json.dumps({"result": result_code, "allow_post": False, **json.loads(SUMMARY.read_text(encoding="utf-8"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
