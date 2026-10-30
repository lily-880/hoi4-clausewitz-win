#!/usr/bin/env python3
"""hoi4-clausewitz-win — Windows port inspired by Clausewitz-MCP.

Commands:
  doctor   check install + (if running) attach read-only to hoi4.exe
  status   attach and print proven live facts (+ gamestate probe if offsets known)
  peinfo   static summary of hoi4.exe
  scan     static RTTI/string offset scan (writes research/re-dumps/static_scan.json)
  probe    alias for status
  live-gs  live scan for G_GAMESTATE using RTTI vtable candidates (read-only)
  serve    minimal MCP stdio stub

Read-only by default. Command-queue posting stays disabled until offsets verified.
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
    print("  target pin  : Windows HOI4 1.19.4.x (Operation Postern)")
    if sys.version_info < (3, 8):
        print("  ! Python 3.8+ required"); ok = False
    if platform.system() != "Windows":
        print("  ! Runtime attach requires Windows")
    import config
    game = config.find_game_dir()
    print("  game dir    : %s" % (game or "NOT FOUND"))
    if not game:
        print("    -> set HOI4_PATH"); ok = False
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
                print("  pe parse    : FAIL (%s)" % e); ok = False
        ver = config.read_launcher_version(game)
        print("  launcher ver: %s" % (ver or "(unknown)"))
        if ver and "1.19.4" not in str(ver):
            print("  ! WARNING: pinned for 1.19.4; found %s" % ver)
        for sub in ("map/definition.csv", "common/terrain/00_terrain.txt",
                    "common/defines/00_defines.lua", "history/states"):
            path = os.path.join(game, sub)
            mark = "ok " if os.path.exists(path) else "--"
            print("    [%s] %s" % (mark, sub))
            if not os.path.exists(path):
                ok = False
    if platform.system() == "Windows":
        try:
            from mem import find_pid, Proc
            import config
            pid = find_pid(config.EXE_NAME)
            print("  running     : %s" % (("pid %d" % pid) if pid else "none (start the game)"))
            if pid:
                p = Proc(pid)
                print("  attach      : OK")
                print("  image base  : %#x" % p.base)
                print("  image size  : %#x" % p.image_size)
                print("  read MZ     : %s" % (p.try_read(p.base, 2) == b"MZ"))
                print("  regions     : %d committed" % len(p.maps))
                p.close()
        except Exception as e:
            print("  attach      : FAIL (%s)" % e); ok = False
    else:
        print("  running     : (skip attach — not Windows)")
    import offsets as O
    known = {k: v for k, v in O.WINDOWS_GLOBALS.items() if v is not None}
    print("  known RVAs  : %s" % (known or "(none yet)"))
    print("-" * 56)
    print("RESULT: %s" % ("ready" if ok else "problems found"))
    print("NOTE: command-queue posting remains DISABLED until FN_CMD_QUEUE_POST verified.")
    return 0 if ok else 1


def cmd_status(args):
    if platform.system() != "Windows":
        print("status requires Windows + running hoi4.exe"); return 1
    import config
    from mem import Proc, find_pid
    import offsets as O
    pid = find_pid(config.EXE_NAME)
    if not pid:
        print("hoi4.exe not running"); return 1
    p = Proc(pid)
    O.RUNTIME.update(image_base=p.base, image_size=p.image_size, pid=p.pid)
    proven = {
        "phase": 2,
        "read_only": True,
        "pid": p.pid,
        "image_base": hex(p.base),
        "image_size": hex(p.image_size),
        "image_path": p.image_path,
        "regions_committed": len(p.maps),
        "mz_ok": p.try_read(p.base, 2) == b"MZ",
        "target": O.TARGET,
        "globals": {k: (hex(v) if isinstance(v, int) else v) for k, v in O.WINDOWS_GLOBALS.items()},
        "command_queue": "disabled (need verified FN_CMD_QUEUE_POST)",
    }
    strings = []
    for s in (b"CGameState", b"CCommandQueue", b"CLandCombat", b"Hearts of Iron", b".?AVCGameState@@"):
        region = [dict(start=p.base, end=p.base + p.image_size, perms="r--p", path="hoi4.exe")]
        hits = p.scan_value(s, regions=region, limit=5, align=1)
        strings.append({"needle": s.decode("ascii", "replace"), "hits": [hex(h) for h in hits]})
    proven["string_hits_in_image"] = strings
    # Session classification (G_IDLER type — not mere GS presence)
    from gamestate import detect_session, try_global_summary, probe_player_armies
    from pe import PE
    pe = None
    try:
        dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
        pe = PE(dump if os.path.isfile(dump) else (p.image_path or ""))
    except Exception:
        pe = None
    session = detect_session(p, pe)
    proven["session"] = session
    if session.get("user_action"):
        proven["user_action"] = session["user_action"]
        print(
            "\n*** USER ACTION: %s ***\n%s\n"
            % (session["user_action"], session.get("guidance") or ""),
            file=sys.stderr,
        )

    # If G_GAMESTATE known, probe + campaign summary fields
    if O.WINDOWS_GLOBALS.get("G_GAMESTATE") is not None:
        proven["gamestate_probe"] = try_global_summary(p, O.WINDOWS_GLOBALS["G_GAMESTATE"])
        camp = proven["gamestate_probe"].get("campaign") or {}
        proven["campaign"] = camp.get("verified") or {}
        proven["campaign_fields_raw"] = {
            k: camp.get("fields", {}).get(k)
            for k in ("player_tag_raw", "date_year_hypothesis", "date_aux_0x47c", "divisions_count", "divisions_note", "armies_count", "armies_note")
        }
        # In-game: fill armies_count from CO_ARMIES@0x290 (CArmy*)
        if session.get("in_game") and pe is not None:
            gs_val = (proven["gamestate_probe"] or {}).get("value")
            if gs_val:
                armies = probe_player_armies(p, pe, int(gs_val, 16))
                proven["armies"] = armies
                if armies.get("ok"):
                    proven["campaign"]["armies_count"] = armies["armies_count"]
                    proven["campaign_fields_raw"]["armies_count"] = armies["armies_count"]
                    proven["campaign_fields_raw"]["armies_note"] = armies.get("note")
                    if armies.get("divisions_count") is not None:
                        proven["campaign"]["divisions_count"] = armies["divisions_count"]
                        proven["campaign_fields_raw"]["divisions_count"] = armies["divisions_count"]
                        proven["campaign_fields_raw"]["divisions_note"] = armies.get("divisions_note")
                    proven["campaign_fields_raw"]["division_like_sample"] = armies.get("division_like_sample")
                    if armies.get("fleets_count") is not None:
                        proven["campaign"]["fleets_count"] = armies["fleets_count"]
                        proven["campaign_fields_raw"]["fleets_count"] = armies["fleets_count"]
                        proven["campaign_fields_raw"]["fleets_rtti"] = armies.get("fleets_rtti")
                    if armies.get("div_templates_count") is not None:
                        proven["campaign"]["div_templates_count"] = armies["div_templates_count"]
                        proven["campaign_fields_raw"]["div_templates_count"] = armies["div_templates_count"]
                    if armies.get("theatres_count") is not None:
                        proven["campaign"]["theatres_count"] = armies["theatres_count"]
                        proven["campaign_fields_raw"]["theatres_count"] = armies["theatres_count"]
                    if armies.get("states_count") is not None:
                        proven["campaign"]["states_count"] = armies["states_count"]
                        proven["campaign_fields_raw"]["states_count"] = armies["states_count"]
                    for _fk in (
                        "fronts_count",
                        "controller_areas_count",
                        "owner_areas_count",
                        "modifiers_count",
                    ):
                        if armies.get(_fk) is not None:
                            proven["campaign"][_fk] = armies[_fk]
                            proven["campaign_fields_raw"][_fk] = armies[_fk]
                        proven["campaign_fields_raw"]["div_templates_rtti"] = armies.get("div_templates_rtti")
    proven["phase"] = "2l"
    print(json.dumps(proven, indent=2))
    p.close()
    return 0


def cmd_peinfo(args):
    import config
    from pe import PE
    path = args.exe or config.binary_path(required=True)
    print(json.dumps(PE(path).summary(), indent=2))
    return 0


def cmd_scan(args):
    script = os.path.join(ROOT, "scripts", "scan_static_offsets.py")
    import subprocess
    return subprocess.call([sys.executable, script])


def cmd_live_gs(args):
    """Live G_GAMESTATE discovery: session check + .data slot probe + heap vptr scan.

    Requires an in-campaign session (map visible). Lobby/menu yields 0 hits by design.
    """
    if platform.system() != "Windows":
        print("live-gs requires Windows"); return 1
    import config
    from mem import Proc, find_pid
    from gamestate import (
        scan_candidate_globals,
        heap_find_gamestate,
        probe_zero_data_slots,
        detect_session,
    )
    import offsets as O

    pid = find_pid(config.EXE_NAME)
    if not pid:
        print(json.dumps({"error": "hoi4.exe not running", "guidance": "Start HOI4 and load a campaign/save until the map is visible."}, indent=2))
        return 1
    vt = [
        O.PROVEN_STATIC["CGameState_vtable"],
        O.PROVEN_STATIC["CGameState_vtable_secondary"],
        O.PROVEN_STATIC["CCurrentGameState_vtable"],
        O.PROVEN_STATIC["CCurrentGameState_vtable_secondary"],
    ]
    p = Proc(pid)
    pe = None
    try:
        from pe import PE
        dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
        pe = PE(dump if os.path.isfile(dump) else (p.image_path or ""))
    except Exception:
        pe = None
    session = detect_session(p, pe)
    result = {
        "pid": pid,
        "session": session,
        "vtable_rva_candidates": [hex(x) for x in vt],
        "global_slot_hits": [],
        "zero_slot_hits": [],
        "heap_object_hits": [],
        "verified": None,
        "command_queue": "DISABLED",
    }
    if not session.get("in_game"):
        result["note"] = session.get("guidance")
        result["user_action"] = session.get("user_action") or "LOAD_CAMPAIGN_MAP"
        if session.get("user_action"):
            print(
                "\n*** USER ACTION: %s ***\n%s\n"
                % (result["user_action"], session.get("guidance") or ""),
                file=sys.stderr,
            )
        print(json.dumps(result, indent=2))
        p.close()
        return 3

    # 1) image .data slots holding ptr to GS-vptr object
    result["global_slot_hits"] = scan_candidate_globals(p, vt)
    # 2) static zero-init written .data slots
    slots_path = os.path.join(ROOT, "research", "re-dumps", "data_zero_ptr_slots.json")
    if os.path.isfile(slots_path):
        slot_rvas = [int(x, 16) for x in json.load(open(slots_path, encoding="utf-8")).get("zero_data_ptr_slots", [])]
        result["zero_slot_hits"] = probe_zero_data_slots(p, slot_rvas, vt)
    # 3) heap objects even without a known global
    result["heap_object_hits"] = heap_find_gamestate(p, vt)

    def _commit(rva, probe, how):
        result["verified"] = {"G_GAMESTATE": hex(rva) if rva is not None else None, "how": how, "probe": probe}
        if rva is not None:
            ov = os.path.join(ROOT, "calling", "offsets_runtime.json")
            json.dump({"G_GAMESTATE": rva, "status": "live-verified-heuristic", "how": how, "probe": probe}, open(ov, "w"), indent=2)
            O.WINDOWS_GLOBALS["G_GAMESTATE"] = rva

    for h in result["zero_slot_hits"] + result["global_slot_hits"]:
        if h.get("probe", {}).get("ok"):
            _commit(int(h["global_rva"], 16), h["probe"], "data_slot")
            break
    if result["verified"] is None:
        for h in result["heap_object_hits"]:
            if h.get("probe", {}).get("ok"):
                # object found but global RVA unknown — still useful for read-only status
                result["verified"] = {"G_GAMESTATE": None, "object": h["object"], "how": "heap_only", "probe": h["probe"]}
                ov = os.path.join(ROOT, "calling", "offsets_runtime.json")
                json.dump({"G_GAMESTATE_OBJECT": h["object"], "status": "heap-only-heuristic", "probe": h["probe"]}, open(ov, "w"), indent=2)
                break

    print(json.dumps(result, indent=2))
    p.close()
    return 0 if result["verified"] else 3


def cmd_session_probe(args):
    """Report lobby vs in-campaign; optionally probe G_GAMESTATE candidates."""
    import subprocess
    script = os.path.join(ROOT, "scripts", "session_probe.py")
    return subprocess.call([sys.executable, script])


def cmd_probe(args):
    return cmd_status(args)


def cmd_serve(args):
    os.execv(sys.executable, [sys.executable, os.path.join(ROOT, "mcp", "server.py")])


COMMANDS = {
    "doctor": cmd_doctor,
    "session-probe": cmd_session_probe,
    "status": cmd_status,
    "peinfo": cmd_peinfo,
    "scan": cmd_scan,
    "live-gs": cmd_live_gs,
    "probe": cmd_probe,
    "serve": cmd_serve,
}


def main():
    ap = argparse.ArgumentParser(prog="clausewitz_win", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="doctor", choices=sorted(COMMANDS))
    ap.add_argument("--exe", help="path to hoi4.exe for peinfo")
    args = ap.parse_args()
    try:
        sys.exit(COMMANDS[args.command](args) or 0)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
