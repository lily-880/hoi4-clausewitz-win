#!/usr/bin/env python3
"""Phase 2ijp NON-Post: ITA army→province occupancy map (proven CA fields only).

Live RO only. NO Post / Instant / PATH densify / midflight / ring_embed exec /
tool-gate / ask ALLOW_POST. Do NOT invent org/str or controller_tag as proven.
Theater/frontline live handles: honest STUBBED (recipes docs-only).
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
)
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijp_army_province_map_ro.json"
SUMMARY = ROOT / "reports" / "phase2ijp_army_province_map_ro_summary.json"
DOC = ROOT / "docs" / "PHASE2IJP_ARMY_PROVINCE_MAP_RO.md"

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
    sess = None
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
    scenario = "ITA@1x army→province occupancy map RO (no Post)"

    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(1.2)
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

    army_to_prov = []
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
        cp_ok = cp_id == r["province_id"]
        if cp_ok:
            cp_id_match_n += 1

        entry = {
            "index": r["index"],
            "handle": list(r["handle"]),
            "army": hex(army),
            "province_id": r["province_id"],
            "province": hex(r["province"]) if r["province"] else None,
            "province_ptr_0x1f0_match": ptr_match,
            "cp_id_0xa4": cp_id,
            "cp_id_match": cp_ok,
            "country_tag": r["country_tag"],
            "handle_ok": r["handle_ok"],
            "province_id_ok": r["province_id_ok"],
        }
        army_to_prov.append(entry)
        prov_to_armies[r["province_id"]].append(
            {"index": r["index"], "handle": list(r["handle"]), "army": hex(army)}
        )

    # Co-location clusters (encirclement-bias perception primitive — RO only)
    colocated = {
        str(pid_): armies
        for pid_, armies in sorted(prov_to_armies.items())
        if len(armies) >= 2
    }
    singleton_n = sum(1 for a in prov_to_armies.values() if len(a) == 1)
    multi_n = sum(1 for a in prov_to_armies.values() if len(a) >= 2)
    max_stack = max((len(a) for a in prov_to_armies.values()), default=0)

    # Sample Strategic recipes still DISABLED (docs continuity with 2ijn)
    sample_recipes = []
    for r in rows[:3]:
        sample_recipes.append(
            {
                "army_index": r["index"],
                "strategic": strategic_redeploy_recipe(r, int(r["province_id"])),
            }
        )

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

    map_ok = (
        all_subject_ok
        and ptr_match_n == len(rows)
        and cp_id_match_n == len(rows)
        and len(prov_to_armies) > 0
    )

    result_code = (
        "ARMY_PROVINCE_MAP_RO_HIT"
        if map_ok and calendar_ok and allow_post() is False
        else "ARMY_PROVINCE_MAP_RO_PARTIAL"
    )

    report = {
        "phase": "2ijp",
        "result": result_code,
        "allow_post": False,
        "posting": "DISABLED",
        "hard_rules": [
            "no Instant empty / Inst70/ARR88/tri70 poll",
            "no PATH/OG50-only densify",
            "no long midflight empty poll",
            "no Post inject / 2fb/2gk / tool-gate / ring_embed live",
            "no ask ALLOW_POST / no invent org/str or controller_tag as proven",
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
        "army_province_map": {
            "country_tag_filter": tag,
            "army_count": len(rows),
            "handle_ok_count": handle_ok_n,
            "province_id_ok_count": prov_ok_n,
            "province_ptr_match_count": ptr_match_n,
            "cp_id_match_count": cp_id_match_n,
            "all_subject_ok": all_subject_ok,
            "unique_province_count": len(prov_to_armies),
            "singleton_province_count": singleton_n,
            "multi_army_province_count": multi_n,
            "max_armies_in_one_province": max_stack,
            "army_to_province": army_to_prov,
            "province_to_armies": {str(k): v for k, v in sorted(prov_to_armies.items())},
            "colocated_clusters": colocated,
        },
        "strategic_recipe_sample": sample_recipes,
        "theater_frontline": theater_frontline,
        "gates_g1_g6": gates,
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "<=+1-2pp perception (occupancy map primitive for encirclement bias)",
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
                "phase": "2ijp",
                "result": result_code,
                "allow_post": False,
                "pid": pid,
                "ui_date": s1["ui_date"],
                "day_index": s1["day_index"],
                "clock_class": s1["clock_class"],
                "drain": s1["drain"],
                "exec": s1["exec"],
                "army_count": len(rows),
                "unique_provinces": len(prov_to_armies),
                "multi_army_provinces": multi_n,
                "max_stack": max_stack,
                "map_ok": map_ok,
                "calendar_ok": calendar_ok,
                "crossed_70": False,
                "next": report["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    md = "\n".join(
        [
            "# Phase 2ijp — ITA army→province occupancy map RO",
            "",
            f"**Result:** `{result_code}`  ",
            "**allow_post:** **False** · Post **NOT** called · Instant **PARKED** · never 5x",
            "",
            "## Live clock / queue",
            "",
            f"pid {pid} · {s1['clock_class']} · day_index={s1['day_index']} ui={s1['ui_date']} ·  ",
            f"drain={s1['drain']} exec={s1['exec']} pending={s1['pending']} · calendar_ok={calendar_ok}",
            "",
            "## Army → province map (proven fields only)",
            "",
            f"- armies={len(rows)} · handle_ok={handle_ok_n} · province_id_ok={prov_ok_n}",
            f"- province_ptr@+0x1F0 match={ptr_match_n}/{len(rows)} · CP_ID@+0xA4 match={cp_id_match_n}/{len(rows)}",
            f"- unique_provinces={len(prov_to_armies)} · singleton={singleton_n} · multi_army={multi_n} · max_stack={max_stack}",
            "- Proven used: CA_HANDLE / CA_PROVINCE_ID / CA_COUNTRY_TAG / CA_PROVINCE_PTR / CP_ID",
            "- Co-location clusters exported for encirclement-bias perception (RO only)",
            "",
            "## Honest STUBBED / NOT invented",
            "",
            "- Theater/frontline **live handles** STUBBED (only HANDLE_TYPE_ARMY=0x33 proven)",
            "- CProvince+0x58 controller_tag remains hypothesis_strong (2ct) — **not** fed as proven",
            "- CArmy+0x520/+0x6ec org/str remain HYPOTHESIS_ONLY — **not** invented",
            "",
            "## G1–G6",
            "",
            "| Gate | State |",
            "| --- | --- |",
            "| G1 | ACCEPTABLE Strategic-only |",
            "| G2 | RO prep HIT · live STUBBED |",
            "| G3 | PARKED |",
            "| G4 | HARD_DENY until human |",
            "| G5 | CLOSED_NOT_OPENED |",
            "| G6 | FORBIDDEN now |",
            "",
            "## Path C honesty (t50u)",
            "",
            "~60–62% baseline; occupancy-map perception ≤+1–2pp, **not** +10pp. **~70% NOT crossed.**",
            "",
            "## Next",
            "",
            "Human G4 → G5 → G2 live / G6. No densify/poll churn.",
            "",
            "*Phase 2ijp · 2026-11-01 Asia/Shanghai*",
            "",
        ]
    )
    DOC.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": result_code,
                "armies": len(rows),
                "unique_provs": len(prov_to_armies),
                "multi": multi_n,
                "max_stack": max_stack,
                "map_ok": map_ok,
                "ui": s1["ui_date"],
                "day": s1["day_index"],
                "allow_post": allow_post(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
