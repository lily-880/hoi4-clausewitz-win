#!/usr/bin/env python3
"""Phase 2ijt NON-Post: live stack refresh + NON-Post readiness freeze (G4 sole unlock).

Cheap B+A: refresh stack histogram/concentration from proven CA fields; freeze agent
readiness card that NON-Post Path-C ceiling is hit until human G4. NO Post / Instant /
PATH densify / midflight / ring_embed / tool-gate / ask ALLOW_POST. No invent org/str,
controller_tag, theater/frontline, or province adjacency.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from army_subjects import iter_armies_by_index, strategic_redeploy_recipe
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijt_nonpost_readiness_freeze.json"
SUMMARY = ROOT / "reports" / "phase2ijt_nonpost_readiness_freeze_summary.json"
DOC = ROOT / "docs" / "PHASE2IJT_NONPOST_READINESS_FREEZE.md"

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


def git_short(ref: str = "HEAD") -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", ref], cwd=str(ROOT), text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    assert allow_post() is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    scenario = "ITA@1x NON-Post readiness freeze + stack refresh (no Post)"

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

    prov_to: dict[int, list] = defaultdict(list)
    ptr_n = cp_n = 0
    for r in rows:
        try:
            pref = u64(b, r["army"] + CA_PROVINCE_PTR)
        except Exception:
            pref = None
        if pref and r["province"] and pref == r["province"]:
            ptr_n += 1
        cp = None
        try:
            if r["province"]:
                cp = u32(b, r["province"] + CP_ID)
        except Exception:
            pass
        if cp == r["province_id"]:
            cp_n += 1
        prov_to[r["province_id"]].append(
            {"index": r["index"], "handle": list(r["handle"])}
        )

    hist: dict[str, int] = defaultdict(int)
    for armies in prov_to.values():
        hist[str(len(armies))] += 1
    multi = {pid_: a for pid_, a in prov_to.items() if len(a) >= 2}
    max_stack = max((len(a) for a in prov_to.values()), default=0)
    armies_in_multi = sum(len(a) for a in multi.values())
    concentration = (armies_in_multi / len(rows)) if rows else 0.0
    top_stacks = sorted(
        (
            {"province_id": pid_, "stack_depth": len(a), "armies": a}
            for pid_, a in multi.items()
        ),
        key=lambda x: (-x["stack_depth"], x["province_id"]),
    )[:5]

    top_recipes = []
    for st in top_stacks[:3]:
        subj = next(r for r in rows if r["index"] == st["armies"][0]["index"])
        top_recipes.append(
            {
                "province_id": st["province_id"],
                "stack_depth": st["stack_depth"],
                "strategic_redeploy_sample": strategic_redeploy_recipe(
                    subj, int(st["province_id"])
                ),
                "posting": "DISABLED",
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

    freeze = {
        "nonpost_ceiling": "HIT",
        "note": (
            "Further NON-Post Instant/PATH/adjacency/theater polish yields 0pp Path-C unlock. "
            "Sole Path-C unlock is human G4 then G5/G6/G2-live."
        ),
        "do_not_churn": [
            "Instant empty / Inst70/ARR88/tri70",
            "PATH/OG50-only densify",
            "long midflight empty poll",
            "invent adjacency / org/str / controller_tag / theater-frontline",
            "Capstone/121 re-churn",
            "ask user ALLOW_POST from executor",
        ],
        "sole_unlock": "Human G4 CLAUSEWITZ_ALLOW_POST=1",
        "after_g4": "G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x",
        "folded_phases": ["2ijp occupancy", "2ijq catalog", "2ijr stack-encircle", "2ijs strategic catalog"],
        "head": git_short("HEAD"),
        "origin_main": git_short("origin/main"),
    }

    polish_ok = (
        all_subject_ok
        and ptr_n == len(rows)
        and cp_n == len(rows)
        and len(prov_to) > 0
    )
    result_code = (
        "NONPOST_READINESS_FREEZE_HIT"
        if polish_ok and calendar_ok and allow_post() is False
        else "NONPOST_READINESS_FREEZE_PARTIAL"
    )

    report = {
        "phase": "2ijt",
        "result": result_code,
        "allow_post": False,
        "posting": "DISABLED",
        "hard_rules": [
            "no Instant empty / Inst70/ARR88/tri70 poll",
            "no PATH/OG50-only densify",
            "no long midflight empty poll",
            "no Post inject / 2fb/2gk / tool-gate / ring_embed live",
            "no ask ALLOW_POST / no invent org/str / controller_tag / theater / adjacency",
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
        "stack_refresh": {
            "army_count": len(rows),
            "handle_ok_count": handle_ok_n,
            "province_id_ok_count": prov_ok_n,
            "province_ptr_match_count": ptr_n,
            "cp_id_match_count": cp_n,
            "all_subject_ok": all_subject_ok,
            "unique_province_count": len(prov_to),
            "multi_army_province_count": len(multi),
            "max_stack_depth": max_stack,
            "concentration_ratio": round(concentration, 4),
            "stack_depth_histogram": dict(sorted(hist.items(), key=lambda kv: int(kv[0]))),
            "top_stacks": top_stacks,
            "adjacency_graph": {"state": "HONEST_EMPTY"},
        },
        "top_stack_recipes_disabled": top_recipes,
        "readiness_freeze": freeze,
        "gates_g1_g6": gates,
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "0pp (refresh+freeze; NON-Post ceiling HIT; no Path-C unlock)",
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
                "phase": "2ijt",
                "result": result_code,
                "allow_post": False,
                "pid": pid,
                "ui_date": s1["ui_date"],
                "day_index": s1["day_index"],
                "clock_class": s1["clock_class"],
                "drain": s1["drain"],
                "exec": s1["exec"],
                "army_count": len(rows),
                "unique_provinces": len(prov_to),
                "multi_army": len(multi),
                "max_stack": max_stack,
                "concentration_ratio": round(concentration, 4),
                "adjacency": "HONEST_EMPTY",
                "nonpost_ceiling": "HIT",
                "calendar_ok": calendar_ok,
                "crossed_70": False,
                "next": report["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    DOC.write_text(
        f"""# Phase 2ijt — NON-Post readiness freeze + stack refresh

**Result:** `{result_code}`  
**allow_post:** False (never flipped)  
**Live:** pid={pid} ITA ui={s1['ui_date']} day={s1['day_index']} clock={s1['clock_class']} drain={s1['drain']} exec={s1['exec']}  
**HEAD:** {freeze['head']}

## Stack refresh (proven fields only)

- armies={len(rows)} unique_provinces={len(prov_to)} multi={len(multi)} max_stack={max_stack}
- concentration_ratio={concentration:.4f}
- handle/province/ptr/cp_id: {handle_ok_n}/{prov_ok_n}/{ptr_n}/{cp_n} of {len(rows)}
- adjacency: **HONEST_EMPTY**

## Readiness freeze

**NON-Post ceiling: HIT.** Further Instant/PATH/adjacency/theater polish does not unlock Path-C.

**Sole unlock:** Human G4 `CLAUSEWITZ_ALLOW_POST=1` (executor cannot flip) → G5 → G2 live / G6 one Strategic Post @1x.

Folded: 2ijp occupancy · 2ijq catalog · 2ijr stack-encircle · 2ijs Strategic catalog.

## Gates G1–G6

- G1 ACCEPTABLE Strategic-only
- G2 RO prep HIT / live STUBBED
- G3 Instant PARKED
- G4 HARD_DENY until human
- G5 CLOSED_NOT_OPENED
- G6 FORBIDDEN now

## Path C honesty

~60–62%; this slice **0pp**; **~70% NOT crossed**.

*Phase 2ijt — 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )

    print(json.dumps({"result": result_code, "allow_post": False, **json.loads(SUMMARY.read_text(encoding="utf-8"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
