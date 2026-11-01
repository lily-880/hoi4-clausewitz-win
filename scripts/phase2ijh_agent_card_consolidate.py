#!/usr/bin/env python3
"""Phase 2ijh NON-Post: agent-card READY/PARKED/HARD_DENY consolidate.
NO PATH/OG50 densify. NO Instant polls. Clock reaffirm only.
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
            "year_at_0x478": y,
            "day_index_at_0x484": d,
            "ui_date_corrected": ui_date(y, d),
            "drain": meta.get("drain"),
            "exec": meta.get("exec"),
            "pending": meta.get("pending"),
            "clock_class": "CONTINUOUS"
            if not (y == 1936 and d < 48)
            else "RELOAD_OR_NEW_CAMPAIGN",
        }

    s0 = sample()
    time.sleep(3)
    s1 = sample()
    out = {
        "phase": "2ijh",
        "slice": "agent_card_ready_parked_deny_NO_PATH_OG50_DENSE_NONPOST",
        "result": "AGENT_CARD_READY_PARKED_DENY_CONSOLIDATE",
        "allow_post": False,
        "instant_parked": True,
        "path_og50_densify": False,
        "diminishing_returns_note": "2ijg MULTI_STABLE; further PATH/OG50-only will not unlock ~70%",
        "agent_card_doc": "docs/PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md",
        "live_clock_reaffirm": {
            "s0": s0,
            "s1": s1,
            "calendar_ok": (s1["day_index_at_0x484"] > s0["day_index_at_0x484"])
            or ((s1["exec"] or 0) > (s0["exec"] or 0)),
            "exec_delta": (s1["exec"] or 0) - (s0["exec"] or 0),
        },
        "vt_refs_catalog": {"INST_VT": "0x2A02558", "CP_VT": "0x29EE248"},
        "path_c_progress_honesty": "~60%; not +10pp; ~70% NOT crossed",
    }
    (ROOT / "reports/phase2ijh_agent_card_consolidate.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": out["result"],
                "calendar_ok": out["live_clock_reaffirm"]["calendar_ok"],
                "live": s1,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
