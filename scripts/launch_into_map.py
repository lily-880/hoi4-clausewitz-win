#!/usr/bin/env python3
"""Launch HOI4 1.19.4 onto the map WITHOUT UI clicks (safe CLI only).

Default (cool): ``-start_tag=HAI -start_speed=0 -noai`` — 1936 Haiti, paused, AI off.
Avoid ``-hands_off`` for long RE sessions (forces max speed + human AI → fans).

Do NOT use old/incompatible saves. ``-start_save=NAME`` only for same 1.19.4 saves.
Never writes process memory.

Usage:
  python scripts/launch_into_map.py
  python scripts/launch_into_map.py --start-tag GER
  python scripts/launch_into_map.py --hands-off          # max speed; prefer not for RE
  python scripts/launch_into_map.py --start-save MySave  # same-version only
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

DEFAULT_EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"


def stop_hoi4() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "hoi4.exe"], capture_output=True, text=True)
    time.sleep(3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", default=os.environ.get("HOI4_EXE", DEFAULT_EXE))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--paused-haiti", action="store_true", default=True,
                   help="default: -start_tag=HAI -start_speed=0 -noai")
    g.add_argument("--hands-off", action="store_true",
                   help="auto 1936 Haiti MAX SPEED (loud; avoid for long RE)")
    g.add_argument("--start-tag", metavar="TAG", help="1936 start as TAG (add -start_speed=0)")
    g.add_argument("--start-save", metavar="NAME", help="same-version save only")
    ap.add_argument("--speed", type=int, default=0, help="initial speed 0-4 (default 0=pause)")
    ap.add_argument("--no-gdpr", action="store_true")
    ap.add_argument("--allow-ai", action="store_true", help="do not pass -noai")
    args = ap.parse_args()

    if not os.path.isfile(args.exe):
        print(f"EXE missing: {args.exe}", file=sys.stderr)
        return 2

    stop_hoi4()
    argv = [args.exe]
    if not args.no_gdpr:
        argv.append("-gdpr-compliant")

    if args.start_save:
        name = args.start_save
        if name.lower().endswith(".hoi4"):
            name = name[:-5]
        if " " in name or "-" in name:
            print("save name cannot contain spaces or hyphens", file=sys.stderr)
            return 2
        argv.append(f"-start_save={name}")
        print("WARN: -start_save requires SAME game version as the save", file=sys.stderr)
    elif args.hands_off:
        argv.append("-hands_off")
        print("WARN: -hands_off runs at max speed; pause with Space after load", file=sys.stderr)
    else:
        tag = args.start_tag or "HAI"
        argv.append(f"-start_tag={tag}")
        sp = max(0, min(4, args.speed))
        argv.append(f"-start_speed={sp}")
        if not args.allow_ai:
            argv.append("-noai")

    print("Launching:", " ".join(argv))
    subprocess.Popen(argv, cwd=os.path.dirname(args.exe), close_fds=True)
    print("Started. Wait for map, then: python clausewitz_win.py status")
    print("Expect G_IDLER -> CInGameIdler. Posting stays DISABLED. Prefer paused (speed 0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
