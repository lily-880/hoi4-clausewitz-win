#!/usr/bin/env python3
"""Phase 2ijj NON-Post: G1 Strategic-only acceptance path (RO).

Reaffirm live Strategic factory_idx 4753 + VT FN MATCH; fold offline
2fd bit_identical + 2gk DESIGN into SAFE_POST G1 alternate to midflight
CMove. NO Post / Instant / PATH densify / midflight poll / ring_embed exec.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from config import allow_post
from process import Backend, find_pid


def load_hb():
    spec = importlib.util.spec_from_file_location(
        "p2hb", ROOT / "scripts/phase2hb_move_family_fn_polish.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    assert allow_post() is False
    hb = load_hb()
    pid = find_pid()
    assert pid
    b = Backend(pid)
    base = b.image_base
    tag = hb.player_tag(b, base)
    scenario = "ITA@1x G1 Strategic-only acceptance RO (no Post, no Instant, no midflight)"
    s0 = hb.live_meta(b, base, pid, tag, scenario)
    time.sleep(2)
    s1 = hb.live_meta(b, base, pid, tag, scenario)
    polish = hb.factory_and_fn(b, base)
    strat_ok = bool(polish.get("strategic_4753_match")) and bool(
        polish.get("fn_match", {}).get("STRATEGIC")
    )
    family_ok = bool(polish.get("all_factory_match")) and bool(polish.get("all_fn_match"))
    if strat_ok and family_ok:
        result = "G1_STRATEGIC_ONLY_ACCEPTANCE_PATH_HIT"
    elif strat_ok:
        result = "G1_STRATEGIC_FACTORY_FN_HIT_FAMILY_PARTIAL"
    else:
        result = "G1_STRATEGIC_ACCEPTANCE_PARTIAL"

    g1 = {
        "alternate_to_midflight_cmove": True,
        "acceptance_meaning": (
            "G1 may be satisfied for SAFE Post discussion via Strategic-only path "
            "when offline Strategic rebuild bit_identical (2fd) + recipe DESIGN (2gk) "
            "+ live factory 4753 / VT FN MATCH hold — without waiting for ordinary "
            "CMove midflight hex. G2 ring_embed live + G4 human ALLOW_POST still required."
        ),
        "offline_2fd": {
            "result": "STRATEGIC_OFFLINE_REBUILD_PASS",
            "bit_identical": True,
            "factory_idx": 4753,
            "type_id": "0x35b9",
            "size": "0x50",
            "ring_embed_live": "STUBBED",
        },
        "design_2gk": {
            "result": "STRATEGIC_RING_EMBED_DESIGN_V2_STARTGAME_CONCORDANCE",
            "executed_2fb_recipe": False,
            "live_inprocess_ring_embed": "STUBBED",
        },
        "live_reaffirm": {
            "strategic_4753_match": polish.get("strategic_4753_match"),
            "strategic_fn_match": polish.get("fn_match", {}).get("STRATEGIC"),
            "slot": polish.get("slots", {}).get("STRATEGIC"),
            "fn": polish.get("fns", {}).get("STRATEGIC"),
        },
        "still_blocks_allow_post": ["G2", "G3_if_move_path", "G4", "G5", "G6"],
        "ordinary_cmove_midflight": "still STUBBED / PARKED (not required if Strategic-only accepted)",
    }

    calendar_ok = (s1.get("hours") or 0) > (s0.get("hours") or 0) or (
        (s1.get("exec") or 0) > (s0.get("exec") or 0)
    )
    out = {
        "phase": "2ijj",
        "slice": "g1_strategic_only_acceptance_RO_NONPOST",
        "result": result,
        "allow_post": False,
        "post_executed": False,
        "instant_parked": True,
        "path_og50_densify": False,
        "midflight_poll": False,
        "ring_embed_executed": False,
        "g1": g1,
        "move_family_polish": {
            "all_factory_match": polish.get("all_factory_match"),
            "all_fn_match": polish.get("all_fn_match"),
            "factory_match": polish.get("factory_match"),
            "fn_match": polish.get("fn_match"),
            "expected_idx": polish.get("expected_idx"),
        },
        "live": s1,
        "calendar_sample": {"s0": s0, "s1": s1, "calendar_ok": calendar_ok},
        "path_c_progress_honesty": (
            "~60%; G1 Strategic-only acceptance docs+RO reaffirm helps SAFE Post path "
            "clarity but does NOT unlock Post or cross ~70% without G2/G4+"
        ),
        "doc": "docs/PHASE2IJJ_G1_STRATEGIC_ONLY_ACCEPTANCE.md",
        "hard_deny": [
            "ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "ring_embed live",
            "tool-gate",
            "Instant empty re-poll",
            "PATH densify",
            "long midflight empty poll",
            "5x",
        ],
    }
    (ROOT / "reports/phase2ijj_g1_strategic_only_acceptance.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    brief = {
        k: out[k]
        for k in (
            "phase",
            "result",
            "allow_post",
            "g1",
            "move_family_polish",
            "live",
            "calendar_sample",
            "path_c_progress_honesty",
            "doc",
        )
    }
    (ROOT / "reports/phase2ijj_g1_strategic_only_acceptance_summary.json").write_text(
        json.dumps(brief, indent=2, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": result,
                "strategic_4753_match": polish.get("strategic_4753_match"),
                "strategic_fn_match": polish.get("fn_match", {}).get("STRATEGIC"),
                "all_factory_match": polish.get("all_factory_match"),
                "all_fn_match": polish.get("all_fn_match"),
                "calendar_ok": calendar_ok,
                "live": {
                    "pid": s1.get("pid"),
                    "hours": s1.get("hours"),
                    "ui_date": s1.get("ui_date"),
                    "drain": s1.get("drain"),
                    "exec": s1.get("exec"),
                },
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
