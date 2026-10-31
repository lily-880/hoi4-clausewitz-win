#!/usr/bin/env python3
"""Phase 2gi: light ≤60s RO snapshot for LAND_POST_READINESS checklist.
No Post. Never 5x. allow_post False. Does not ask user to right-click.
"""
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
import post_abi

assert allow_post() is False

OBSERVE_S = 12.0
INTERVAL_S = 0.25
TZ = timezone(timedelta(hours=8))


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


def live_snap(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER) if sess else 0
    stage = try_u32(b, sess + post_abi.CSession_STAGE_COUNT) if sess else None
    drain = try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER) if sess else None
    exec_c = try_u32(b, sess + post_abi.CSession_EXEC_COUNTER) if sess else None
    # CPdxArray size typically at +0x0C from array base
    pending = try_u32(b, server + post_abi.CDummyServer_PENDING + 0xC) if server else None
    return {
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "stage": stage,
        "pending": pending,
        "drain": drain,
        "exec": exec_c,
        "gs": hex(gs),
        "session": hex(sess) if sess else None,
    }


def main():
    assert allow_post() is False
    out = {
        "phase": "2gi",
        "result": "land_post_readiness_checklist",
        "allow_post": False,
        "doc": "docs/LAND_POST_READINESS.md",
        "speed_policy": "pause-or-1x only (never 5x)",
        "forbidden": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post",
            "tool-gate",
            "2fb_recipe_execute",
            "ask_user_right_click",
            "Capstone/121 re-churn",
        ],
        "checklist": {
            "cmove_leaf": "STUBBED",
            "ring_embed": "STUBBED",
            "nf_rf_midflight": "STUBBED_EMPTY",
            "allow_post": "HARD_DENY",
            "tool_gate": "CLOSED_NOT_OPENED",
            "strategic_layout_2fb": "MATCH",
            "orders_factory_idx_2fg": "FILLED_MATCH",
            "move_cancel_factory_idx_2fe": "FILLED",
        },
        "next_human_gated": [
            "midflight CMove leaf OR Dummy recreate proof on Strategic sample",
            "ring-embed recreate without corruption",
            "human CLAUSEWITZ_ALLOW_POST=1 for ONE experiment",
            "dedicated tool-gate open with NEVER_POST",
            "one land MOVE|Strategic Post at 1x then unset",
        ],
        "next_shortest_blocker": (
            "NON-Post: gate stays CLOSED; human midflight CMove or recreate proof; "
            "retry GitHub push when reachable — still NO ALLOW_POST"
        ),
    }

    pid = find_pid()
    if not pid:
        out["live"] = None
        out["error"] = "NO_LIVE_PROCESS"
        path = ROOT / "reports" / "phase2gi_land_post_readiness.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2)[:900])
        return 1

    b = Backend()
    base = b.image_base
    t0 = time.time()
    samples = []
    while time.time() - t0 < OBSERVE_S:
        samples.append(live_snap(b, base))
        time.sleep(INTERVAL_S)
    last = samples[-1]
    first = samples[0]
    out["live"] = {
        "pid": pid,
        "hours_start": first["hours"],
        "hours_end": last["hours"],
        "ui_start": first["ui_date"],
        "ui_end": last["ui_date"],
        "stage": last["stage"],
        "pending": last["pending"],
        "drain": last["drain"],
        "exec": last["exec"],
        "samples": len(samples),
        "observe_wall_s": round(time.time() - t0, 2),
        "scenario": "ITA@1x current process (no relaunch; RO snapshot only)",
        "captured_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M Asia/Shanghai"),
    }
    path = ROOT / "reports" / "phase2gi_land_post_readiness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    (ROOT / "reports" / "phase2gi_summary.json").write_text(
        json.dumps(
            {
                "phase": "2gi",
                "result": out["result"],
                "allow_post": False,
                "doc": out["doc"],
                "live": out["live"],
                "checklist": out["checklist"],
                "next_shortest_blocker": out["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(out, indent=2)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
