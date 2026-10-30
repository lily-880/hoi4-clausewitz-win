#!/usr/bin/env python3
"""Bounded live session probe: frontend vs in-game via G_IDLER.

Read-only. Writes research/re-dumps/session_probe.json.
Exits 0 if in_game (CInGameIdler), 3 if frontend/lobby/menu, 1 if not running.

Phase 2g: GS presence alone is NOT in-game — lobby can hold CCurrentGameState
while G_IDLER is still CFrontEndIdler.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

from mem import Proc, find_pid  # noqa: E402
import config  # noqa: E402
from gamestate import detect_session  # noqa: E402
from pe import PE  # noqa: E402


def main() -> int:
    out_path = os.path.join(ROOT, "research", "re-dumps", "session_probe.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    pid = find_pid(config.EXE_NAME)
    if not pid:
        payload = {
            "running": False,
            "session": "not_running",
            "user_action": "LOAD_CAMPAIGN_MAP",
            "guidance": "Start HOI4 and load a campaign/save until the map is visible.",
        }
        json.dump(payload, open(out_path, "w", encoding="utf-8"), indent=2)
        print(json.dumps(payload, indent=2))
        return 1

    p = Proc(pid)
    dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    try:
        pe = PE(dump if os.path.isfile(dump) else p.image_path)
    except Exception:
        pe = None
    session = detect_session(p, pe)
    payload = {
        "running": True,
        "pid": pid,
        "image_base": hex(p.base),
        "phase": "2g",
        "session": session,
        "user_action": session.get("user_action"),
        "command_queue": "DISABLED",
    }
    if session.get("user_action"):
        print(
            "\n*** USER ACTION: %s ***\n%s\n"
            % (session["user_action"], session.get("guidance") or ""),
            file=sys.stderr,
        )
    json.dump(payload, open(out_path, "w", encoding="utf-8"), indent=2)
    print(json.dumps(payload, indent=2))
    p.close()
    return 0 if session.get("in_game") else 3


if __name__ == "__main__":
    raise SystemExit(main())
