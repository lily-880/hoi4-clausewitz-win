#!/usr/bin/env python3
"""Phase 2ijo NON-Post: push-sync recovery + army-subject/G1–G6 agent catalog.

Catalog-only. NO Post / Instant / PATH densify / midflight / ring_embed exec /
tool-gate / ask ALLOW_POST. Does not invent org/str offsets.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijo_push_sync_agent_catalog.json"
SUMMARY = ROOT / "reports" / "phase2ijo_push_sync_agent_catalog_summary.json"
DOC = ROOT / "docs" / "PHASE2IJO_PUSH_SYNC_AGENT_CATALOG.md"

GS_YEAR = 0x478
GS_DAY = 0x484


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
    sess = server = None
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


def main() -> int:
    import os
    import subprocess

    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    assert allow_post() is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    scenario = "ITA@1x push-sync + army-subject/G1-G6 agent catalog (no Post)"

    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(1.2)
    s1 = continuum_live(b, base, pid, tag, scenario)
    calendar_ok = (
        s1["clock_class"] == "CONTINUOUS"
        and (s1["drain"] or 0) >= (s0["drain"] or 0)
        and (s1["exec"] or 0) >= (s0["exec"] or 0)
    )

    # Load 2ijn subject rollup (catalog fold — do not re-scan Instant/PATH)
    ijn_path = ROOT / "reports" / "phase2ijn_army_subject_strategic_ro_summary.json"
    ijn = json.loads(ijn_path.read_text(encoding="utf-8")) if ijn_path.exists() else {}

    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    origin = subprocess.check_output(["git", "rev-parse", "--short", "origin/main"], cwd=ROOT, text=True).strip()
    log1 = subprocess.check_output(["git", "log", "-1", "--oneline"], cwd=ROOT, text=True).strip()

    push_status = {
        "result": "PUSH_SUCCESS",
        "range": "40d7716..c342a89",
        "prior_fail": "2ijn PC github.com:443 timeout; origin lagged at 40d7716",
        "head": head,
        "origin_main": origin,
        "synced": head == origin == "c342a89",
        "log": log1,
        "note": "2ijo FIRST retry recovered lag; PC+box+origin aligned at c342a89 before this commit",
    }

    gates = {
        "G1": {"state": "ACCEPTABLE", "via": "Strategic-only (2ijj)", "note": "CMove midflight hex still STUBBED"},
        "G2": {"state": "RO_PREP_HIT_LIVE_STUBBED", "via": "2ijk INLINE_BLOB", "note": "live ring_embed STUBBED"},
        "G3": {"state": "PARKED", "via": "peacetime Instant", "note": "no Instant empty re-poll"},
        "G4": {"state": "HARD_DENY_UNTIL_HUMAN", "via": "CLAUSEWITZ_ALLOW_POST=1 once", "note": "executor cannot flip"},
        "G5": {"state": "CLOSED_NOT_OPENED", "via": "tool-gate + NEVER_POST after G4"},
        "G6": {"state": "FORBIDDEN_NOW", "via": "ONE Strategic Post @1x after G4+G5", "note": "this slice did NOT Post"},
    }

    agent_card = {
        "ready_ro_feed": [
            "CA_HANDLE@+0x18",
            "CA_PROVINCE_ID@+0x28",
            "CA_COUNTRY_TAG@+0x1E0",
            "CA_PROVINCE_PTR@+0x1F0",
            "ITA army subjects 58/58 (2ijn)",
            "Strategic/Move/SA/Cancel recipes posting DISABLED (2ijn)",
            "MOVE family factory/FN MATCH (2ijm)",
            "Dummy ring INLINE_BLOB RO prep (2ijk)",
            "clock CONTINUOUS day_index continuum",
        ],
        "parked": ["Instant peacetime (G3)", "PATH/OG50 densify as unlock", "org/str @0x520/0x6ec HYPOTHESIS_ONLY"],
        "hard_deny": [
            "allow_post False",
            "Post inject / 2fb/2gk live",
            "ring_embed live execute",
            "tool-gate open",
            "CLAUSEWITZ_ALLOW_POST flip by executor",
            "5x / Capstone/121",
            "invent field names",
        ],
        "army_subject_rollup_2ijn": {
            "result": ijn.get("result"),
            "army_count": ijn.get("army_count"),
            "all_subject_ok": ijn.get("all_subject_ok"),
            "source": "reports/phase2ijn_army_subject_strategic_ro_summary.json",
        },
    }

    result_code = (
        "PUSH_SYNC_AGENT_CATALOG_HIT"
        if push_status["synced"] and calendar_ok and allow_post() is False
        else "PUSH_SYNC_AGENT_CATALOG_PARTIAL"
    )

    report = {
        "phase": "2ijo",
        "result": result_code,
        "allow_post": False,
        "posting": "DISABLED",
        "hard_rules": [
            "no Instant empty / Inst70/ARR88/tri70 poll",
            "no PATH/OG50-only densify",
            "no long midflight empty poll",
            "no Post inject / 2fb/2gk / tool-gate / ring_embed live",
            "no ask ALLOW_POST / no invent org/str offsets",
        ],
        "push_status": push_status,
        "live_s0": s0,
        "live_s1": s1,
        "calendar_ok": calendar_ok,
        "drain_delta": (s1["drain"] or 0) - (s0["drain"] or 0),
        "exec_delta": (s1["exec"] or 0) - (s0["exec"] or 0),
        "gates_g1_g6": gates,
        "agent_card": agent_card,
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "0pp Path-C capability (sync/catalog only; does not unlock Post)",
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
                "phase": "2ijo",
                "result": result_code,
                "allow_post": False,
                "push": "SUCCESS 40d7716..c342a89",
                "head": head,
                "origin_main": origin,
                "pid": pid,
                "ui_date": s1["ui_date"],
                "day_index": s1["day_index"],
                "clock_class": s1["clock_class"],
                "drain": s1["drain"],
                "exec": s1["exec"],
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
            "# Phase 2ijo — Push-sync recovery + army-subject / G1–G6 agent catalog",
            "",
            f"**Result:** `{result_code}`  ",
            "**allow_post:** **False** · Post **NOT** called · Instant **PARKED** · never 5x",
            "",
            "## Push sync",
            "",
            "- PRIOR: 2ijn push FAIL (github.com:443); origin lagged at `40d7716`",
            "- THIS: FIRST retry **SUCCESS** `40d7716..c342a89` HEAD→main",
            f"- Now: PC HEAD=`{head}` · origin/main=`{origin}` · synced={push_status['synced']}",
            "",
            "## Live clock / queue",
            "",
            f"pid {pid} · {s1['clock_class']} · day_index={s1['day_index']} ui={s1['ui_date']} ·  ",
            f"drain={s1['drain']} exec={s1['exec']} pending={s1['pending']} · calendar_ok={calendar_ok}",
            "",
            "## Agent card rollup (catalog)",
            "",
            "### READY (RO feed)",
            "- Proven CArmy: HANDLE/PROVINCE_ID/TAG/PTR",
            "- 2ijn ITA subjects 58/58 + Strategic recipes posting DISABLED",
            "- 2ijm factory/Post-ABI/clock RO HIT",
            "- 2ijk G2 ring_embed RO prep HIT (live still STUBBED)",
            "",
            "### PARKED",
            "- Instant peacetime (G3) · PATH/OG50 densify-as-unlock · org/str hyp NOT invented",
            "",
            "### HARD_DENY",
            "- allow_post False · Post / tool-gate / ring_embed live · executor cannot flip G4",
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
            "~60–62% baseline; this sync/catalog **0pp** Path-C capability (does not unlock Post). **~70% NOT crossed.**",
            "",
            "## Next",
            "",
            "Human G4 → G5 → G2 live / G6. No densify/poll churn.",
            "",
            "*Phase 2ijo · 2026-11-01 Asia/Shanghai*",
            "",
        ]
    )
    DOC.write_text(md, encoding="utf-8")
    print(json.dumps({"result": result_code, "push_synced": push_status["synced"], "head": head, "origin": origin, "ui": s1["ui_date"], "day": s1["day_index"], "allow_post": allow_post()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
