#!/usr/bin/env python3
"""hoi4-clausewitz-win — Windows port inspired by Clausewitz-MCP.

Commands:
  doctor   check install + (if running) attach read-only to hoi4.exe
  status   attach and print what Phase 1 can safely prove
  peinfo   static summary of hoi4.exe (no process needed)
  serve    start a minimal MCP stdio stub (Phase 1 tools only)
  probe    scan for a few string signatures in the live image (read-only)

Read-only by default. Never claims full upstream tool parity.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CALLING = os.path.join(ROOT, "calling")
sys.path.insert(0, CALLING)


def cmd_doctor(args):
    ok = True
    print("hoi4-clausewitz-win installation check")
    print("-" * 56)
    print("  python      : %s" % sys.version.split()[0])
    print("  platform    : %s (%s)" % (platform.system(), platform.machine()))
    print("  target pin  : Windows HOI4 1.19.4.0 (Operation Postern)")
    if sys.version_info < (3, 8):
        print("  ! Python 3.8+ required")
        ok = False
    if platform.system() != "Windows":
        print("  ! Runtime attach requires Windows (you can still run peinfo on a copied exe)")
        # not a hard fail for packaging on Linux box
    import config

    game = config.find_game_dir()
    print("  game dir    : %s" % (game or "NOT FOUND"))
    if not game:
        print("    -> set HOI4_PATH")
        ok = False
    else:
        exe = config.binary_path(required=False)
        print("  executable  : %s" % (exe or "none"))
        if not exe:
            ok = False
        else:
            try:
                from pe import PE

                pe = PE(exe)
                print("  pe imagebase: %#x" % pe.image_base)
                print("  pe imagesize: %#x (%d MB)" % (pe.size_of_image, pe.size_of_image // (1024 * 1024)))
                print("  pe sections : %d" % len(pe.sections))
            except Exception as e:
                print("  pe parse    : FAIL (%s)" % e)
                ok = False
        ver = config.read_launcher_version(game)
        print("  launcher ver: %s" % (ver or "(unknown)"))
        if ver and "1.19.4" not in str(ver):
            print("  ! WARNING: this tree is pinned for 1.19.4; found %s" % ver)
        for sub in (
            "map/definition.csv",
            "common/terrain/00_terrain.txt",
            "common/defines/00_defines.lua",
            "history/states",
        ):
            p = os.path.join(game, sub)
            mark = "ok " if os.path.exists(p) else "--"
            print("    [%s] %s" % (mark, sub))
            if not os.path.exists(p):
                ok = False

    # live process
    if platform.system() == "Windows":
        try:
            from mem import find_pid

            pid = find_pid(config.EXE_NAME)
            print("  running     : %s" % (("pid %d" % pid) if pid else "none (start the game)"))
            if pid:
                from mem import Proc

                p = Proc(pid)
                print("  attach      : OK")
                print("  image base  : %#x" % p.base)
                print("  image size  : %#x" % p.image_size)
                print("  image path  : %s" % p.image_path)
                # prove a read of DOS header at image base
                hdr = p.try_read(p.base, 2)
                print("  read MZ     : %s" % (hdr == b"MZ"))
                if hdr != b"MZ":
                    ok = False
                print("  regions     : %d committed" % len(p.maps))
                p.close()
        except Exception as e:
            print("  attach      : FAIL (%s)" % e)
            ok = False
    else:
        print("  running     : (skip attach — not Windows)")

    print("-" * 56)
    print("RESULT: %s" % ("ready (Phase 1 read path)" if ok else "problems found"))
    print("NOTE: game-state globals / CCommandQueue are NOT recovered yet.")
    return 0 if ok else 1


def cmd_status(args):
    if platform.system() != "Windows":
        print("status requires Windows + a running hoi4.exe")
        return 1
    import config
    from mem import Proc, find_pid
    import offsets as O

    pid = find_pid(config.EXE_NAME)
    if not pid:
        print("hoi4.exe not running")
        return 1
    p = Proc(pid)
    proven = {
        "phase": 1,
        "read_only": True,
        "pid": p.pid,
        "image_base": hex(p.base),
        "image_size": hex(p.image_size),
        "image_path": p.image_path,
        "regions_committed": len(p.maps),
        "mz_ok": p.try_read(p.base, 2) == b"MZ",
        "target": O.TARGET,
        "globals_ready": {k: v is not None for k, v in O.WINDOWS_GLOBALS.items()},
        "game_state": "unavailable until G_GAMESTATE RVA recovered",
        "command_queue": "unavailable (Phase 2)",
    }
    # Optional: search for a few distinctive ASCII strings inside the module mapping
    strings = []
    for s in (b"CGameState", b"CCommandQueue", b"CLandCombat", b"Hearts of Iron"):
        # scan only the main image mapping range
        region = [dict(start=p.base, end=p.base + p.image_size, perms="r--p", path="hoi4.exe")]
        hits = p.scan_value(s, regions=region, limit=3, align=1)
        strings.append({"needle": s.decode("ascii", "replace"), "hits": [hex(h) for h in hits]})
    proven["string_hits_in_image"] = strings
    print(json.dumps(proven, indent=2))
    p.close()
    return 0


def cmd_peinfo(args):
    import config
    from pe import PE

    path = args.exe or config.binary_path(required=True)
    pe = PE(path)
    print(json.dumps(pe.summary(), indent=2))
    return 0


def cmd_probe(args):
    return cmd_status(args)


def cmd_serve(args):
    os.execv(
        sys.executable,
        [sys.executable, os.path.join(ROOT, "mcp", "server.py")],
    )


COMMANDS = {
    "doctor": cmd_doctor,
    "status": cmd_status,
    "peinfo": cmd_peinfo,
    "probe": cmd_probe,
    "serve": cmd_serve,
}


def main():
    ap = argparse.ArgumentParser(
        prog="clausewitz_win",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("command", nargs="?", default="doctor", choices=sorted(COMMANDS))
    ap.add_argument("--exe", help="path to hoi4.exe for peinfo")
    args = ap.parse_args()
    try:
        sys.exit(COMMANDS[args.command](args) or 0)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
