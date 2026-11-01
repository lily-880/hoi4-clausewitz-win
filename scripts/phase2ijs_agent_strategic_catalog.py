#!/usr/bin/env python3
"""Phase 2ijs NON-Post: agent-card + Strategic-only recipe catalog (no Post execute).

Folds 2ijr stack-encircle-bias into agent consumption card + live Strategic/Cancel/
Move recipe catalog from proven army subjects. NO Post / Instant / PATH densify /
midflight / ring_embed / tool-gate / ask ALLOW_POST. No invent org/str, controller_tag,
theater/frontline, or province adjacency.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from army_subjects import (
    iter_armies_by_index,
    strategic_redeploy_recipe,
    cancel_movement_recipe,
    move_action_recipe,
)
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijs_agent_strategic_catalog.json"
SUMMARY = ROOT / "reports" / "phase2ijs_agent_strategic_catalog_summary.json"
DOC = ROOT / "docs" / "PHASE2IJS_AGENT_STRATEGIC_CATALOG.md"

GS_YEAR = 0x478
GS_DAY = 0x484


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u32(b, a):
    try:
        return struct.unpack("<I", b.read(a, 4))[0]
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
    scenario = "ITA@1x agent-card + Strategic-only recipe catalog (no Post)"

    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(1.0)
    s1 = continuum_live(b, base, pid, tag, scenario)
    calendar_ok = (
        s1["clock_class"] == "CONTINUOUS"
        and (s1["drain"] or 0) >= (s0["drain"] or 0)
        and (s1["exec"] or 0) >= (s0["exec"] or 0)
    )

    ijr = {}
    p_ijr = ROOT / "reports" / "phase2ijr_stack_encircle_bias_ro_summary.json"
    if p_ijr.exists():
        ijr = json.loads(p_ijr.read_text(encoding="utf-8"))

    rows = scan_ita_armies(b, base, tag)
    handle_ok_n = sum(1 for r in rows if r.get("handle_ok"))
    prov_ok_n = sum(1 for r in rows if r.get("province_id_ok"))
    all_subject_ok = len(rows) > 0 and handle_ok_n == len(rows) and prov_ok_n == len(rows)

    # Strategic-only recipe catalog from live subjects (DISABLED posting)
    # Sample: first 5 armies + one cancel-for-batch of first 3
    recipe_samples = []
    for r in rows[:5]:
        dest = int(r["province_id"])  # same-province docs-only sample; no Post
        recipe_samples.append(
            {
                "army_index": r["index"],
                "handle": list(r["handle"]),
                "province_id": r["province_id"],
                "strategic_redeploy": strategic_redeploy_recipe(r, dest),
                "move_action": move_action_recipe(r),
                "posting": "DISABLED",
            }
        )
    cancel_sample = cancel_movement_recipe(rows[:3]) if len(rows) >= 3 else None

    gates = {
        "G1": {
            "state": "ACCEPTABLE",
            "via": "Strategic-only (2ijj)",
            "agent_note": "Only Strategic-family recipes are ACCEPTABLE when Post eventually opens",
        },
        "G2": {
            "state": "RO_PREP_HIT_LIVE_STUBBED",
            "via": "2ijk INLINE_BLOB",
            "agent_note": "ring_embed RO prep done; live execute STUBBED until G4+G5",
        },
        "G3": {
            "state": "PARKED",
            "via": "peacetime Instant",
            "agent_note": "Do NOT poll Instant / Inst70 / ARR88 / tri70",
        },
        "G4": {
            "state": "HARD_DENY_UNTIL_HUMAN",
            "via": "CLAUSEWITZ_ALLOW_POST=1",
            "agent_note": "Executor cannot flip; human must set env; do not ask in-slice",
        },
        "G5": {
            "state": "CLOSED_NOT_OPENED",
            "via": "tool-gate after G4",
            "agent_note": "Do not open tool-gate before G4",
        },
        "G6": {
            "state": "FORBIDDEN_NOW",
            "via": "ONE Strategic Post @1x after G4+G5",
            "agent_note": "Single Strategic Post only; never 5x; Instant PARKED",
        },
    }

    agent_card = {
        "phase_fold": "2ijs folds 2ijr stack-encircle + live Strategic catalog",
        "head": git_short("HEAD"),
        "origin_main": git_short("origin/main"),
        "allow_post": False,
        "posting": "DISABLED",
        "proven_fields_only": {
            "CA_HANDLE": "0x18",
            "CA_PROVINCE_ID": "0x28",
            "CA_COUNTRY_TAG": "0x1e0",
            "CA_PROVINCE_PTR": "0x1f0",
            "CP_ID": "0xa4",
            "HANDLE_TYPE_ARMY": "0x33",
        },
        "stack_encircle_from_2ijr": {
            "army_count": ijr.get("army_count"),
            "unique_provinces": ijr.get("unique_provinces"),
            "multi_army": ijr.get("multi_army"),
            "max_stack": ijr.get("max_stack"),
            "concentration_ratio": ijr.get("concentration_ratio"),
            "adjacency": ijr.get("adjacency", "HONEST_EMPTY"),
            "result": ijr.get("result"),
        },
        "live_refresh": {
            "army_count": len(rows),
            "handle_ok_count": handle_ok_n,
            "province_id_ok_count": prov_ok_n,
            "all_subject_ok": all_subject_ok,
            "country_tag_filter": tag,
        },
        "strategic_recipe_policy": {
            "family": "Strategic-only ACCEPTABLE (G1)",
            "posting": "DISABLED until G4 human + G5 + G6",
            "samples_in_report": len(recipe_samples),
            "cancel_batch_sample": True if cancel_sample else False,
            "move_action_note": "documented; path vectors need game allocs — do NOT WPM hand-wave",
        },
        "hard_denies": [
            "theater/frontline live handles STUBBED",
            "CProvince+0x58 controller_tag hypothesis_strong NOT proven",
            "org/str @0x520/0x6ec HYPOTHESIS_ONLY",
            "province adjacency HONEST_EMPTY",
            "Instant peacetime PARKED",
            "no PATH/OG50 densify unlock",
            "executor cannot flip G4",
        ],
        "gates_g1_g6": gates,
        "next_shortest_blocker": "Human G4 CLAUSEWITZ_ALLOW_POST=1 (executor cannot flip) → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x",
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "0pp catalog (agent card + recipe catalog; no new perception unlock)",
            "crossed_70": False,
        },
    }

    result_code = (
        "AGENT_STRATEGIC_CATALOG_HIT"
        if all_subject_ok and calendar_ok and allow_post() is False
        else "AGENT_STRATEGIC_CATALOG_PARTIAL"
    )

    report = {
        "phase": "2ijs",
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
        "agent_card": agent_card,
        "strategic_recipe_samples": recipe_samples,
        "cancel_movement_sample": cancel_sample,
        "gates_g1_g6": gates,
        "path_c_honesty": agent_card["path_c_honesty"],
        "next_shortest_blocker": agent_card["next_shortest_blocker"],
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijs",
                "result": result_code,
                "allow_post": False,
                "pid": pid,
                "ui_date": s1["ui_date"],
                "day_index": s1["day_index"],
                "clock_class": s1["clock_class"],
                "drain": s1["drain"],
                "exec": s1["exec"],
                "army_count": len(rows),
                "all_subject_ok": all_subject_ok,
                "recipe_samples": len(recipe_samples),
                "ijr_concentration": ijr.get("concentration_ratio"),
                "ijr_max_stack": ijr.get("max_stack"),
                "adjacency": "HONEST_EMPTY",
                "calendar_ok": calendar_ok,
                "head": agent_card["head"],
                "crossed_70": False,
                "next": agent_card["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    DOC.write_text(
        f"""# Phase 2ijs — Agent card + Strategic-only recipe catalog (RO)

**Result:** `{result_code}`  
**allow_post:** False (never flipped)  
**Live:** pid={pid} ITA ui={s1['ui_date']} day={s1['day_index']} clock={s1['clock_class']} drain={s1['drain']} exec={s1['exec']}  
**HEAD:** {agent_card['head']}

## Agent card (consumption)

- Folds **2ijr** stack-encircle: armies={ijr.get('army_count')} → provinces={ijr.get('unique_provinces')}; multi={ijr.get('multi_army')}; max_stack={ijr.get('max_stack')}; concentration≈{ijr.get('concentration_ratio')}; adjacency=HONEST_EMPTY
- Live refresh: armies={len(rows)}; handle_ok={handle_ok_n}; province_id_ok={prov_ok_n}; all_subject_ok={all_subject_ok}
- Proven fields only: CA_HANDLE / CA_PROVINCE_ID / CA_COUNTRY_TAG / CA_PROVINCE_PTR / CP_ID / HANDLE_TYPE_ARMY=0x33

## Strategic-only recipe catalog

- Family: Strategic ACCEPTABLE (G1); samples={len(recipe_samples)}; cancel-batch sample included
- MoveAction documented (path vectors need game allocs — do NOT WPM hand-wave)
- **posting DISABLED** until human G4 → G5 → G6

## Gates G1–G6 (crisp)

| Gate | State | Agent note |
|------|-------|------------|
| G1 | ACCEPTABLE | Strategic-only when Post opens |
| G2 | RO_PREP_HIT / live STUBBED | ring_embed live blocked |
| G3 | PARKED | Instant peacetime — do not poll |
| G4 | HARD_DENY_UNTIL_HUMAN | CLAUSEWITZ_ALLOW_POST=1; executor cannot flip |
| G5 | CLOSED_NOT_OPENED | tool-gate after G4 |
| G6 | FORBIDDEN_NOW | ONE Strategic Post @1x after G4+G5 |

## Stubbed / not invented

- Theater/frontline live handles STUBBED
- CProvince+0x58 controller_tag hypothesis_strong — not proven
- org/str @0x520/0x6ec HYPOTHESIS_ONLY
- Province adjacency HONEST_EMPTY

## Path C honesty

~60–62% baseline; this slice **0pp** catalog; **~70% NOT crossed**.

## Next

Human G4 → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x.

*Phase 2ijs — 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )

    print(json.dumps({"result": result_code, "allow_post": False, **json.loads(SUMMARY.read_text(encoding="utf-8"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
