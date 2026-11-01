#!/usr/bin/env python3
"""Phase 2iji NON-Post: SAFE Post gate checklist from 2ijh agent card.
NO PATH densify. NO Instant polls. NO Post. Clock reaffirm only.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import importlib.util
from calling.process import Backend, find_pid
from calling.config import allow_post
from calling.clock import ui_date


def load_iu():
    spec = importlib.util.spec_from_file_location(
        "p2iu", ROOT / "scripts/phase2iu_path200_focus740_og50.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    assert allow_post() is False
    p = load_iu()
    pid = find_pid()
    assert pid
    b = Backend(pid)
    base = b.image_base
    tag = p.player_tag(b, base) or 15

    def sample():
        meta = p.live_meta(b, base, pid, tag)
        y = int(meta.get("year_at_0x478") or 0)
        d = int(meta.get("hours") or 0)
        return {
            "pid": pid,
            "tag": tag,
            "year": y,
            "day": d,
            "ui": ui_date(y, d),
            "drain": meta.get("drain"),
            "exec": meta.get("exec"),
            "pending": meta.get("pending"),
            "clock_class": "CONTINUOUS"
            if not (y == 1936 and d < 48)
            else "RELOAD_OR_NEW_CAMPAIGN",
        }

    s0 = sample()
    time.sleep(2)
    s1 = sample()
    out = {
        "phase": "2iji",
        "slice": "safe_post_gate_checklist_from_agent_card_NONPOST",
        "result": "SAFE_POST_GATE_CHECKLIST_POLISH",
        "allow_post": False,
        "instant_parked": True,
        "path_og50_densify": False,
        "post_executed": False,
        "doc": "docs/PHASE2IJI_SAFE_POST_GATE_CHECKLIST.md",
        "gates_missing": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "live_clock_reaffirm": {
            "s0": s0,
            "s1": s1,
            "calendar_ok": (s1["day"] > s0["day"])
            or ((s1["exec"] or 0) > (s0["exec"] or 0)),
            "exec_delta": (s1["exec"] or 0) - (s0["exec"] or 0),
        },
        "path_c_progress_honesty": "~60%; not +10pp; ~70% NOT crossed",
    }
    (ROOT / "reports/phase2iji_safe_post_gate_checklist.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(json.dumps({"result": out["result"], "live": s1, "gates_missing": out["gates_missing"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
