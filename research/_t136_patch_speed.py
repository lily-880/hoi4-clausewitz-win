from pathlib import Path

p = Path("calling/offsets.py")
text = p.read_text(encoding="utf-8")
old = '    "GS_PAUSE_HOURS": 0x908,  # Linux; NOT verified on Windows (garbage)\n'
new = (
    '    "GS_PAUSE_HOURS": 0x908,  # Linux; NOT verified on Windows (garbage)\n'
    "    # Observed live 2026-11-14 (pid 36620, USA 68, clock frozen):\n"
    "    # i32 at CGameState+0x4BC. User increased UI speed one notch twice;\n"
    "    # this was the only CGameState word that changed (0 -> 1 -> 2) and\n"
    "    # it stayed put while GS_DATE_HOUR_TICK@0x468 did not advance.\n"
    "    # Speed setting, 0-based; UI notch = value+1 (live values 0,1,2).\n"
    "    # NOT the pause/running flag; that address is still unknown on Windows.\n"
    '    "GS_GAME_SPEED_INDEX": 0x4BC,\n'
)
if old not in text:
    raise SystemExit("offsets.py anchor not found")
if "GS_GAME_SPEED_INDEX" in text:
    raise SystemExit("already present in offsets.py")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched offsets.py")

g = Path("calling/gamestate.py")
gt = g.read_text(encoding="utf-8")
anchor = '    out["fields"]["divisions_count"] = None\n'
insert = '''    # Speed setting @+0x4BC (live 2026-11-14). Index is 0-based UI notch;
    # this is not a pause flag, so meta.speed pause|1x stays incomplete.
    speed_off = O.HYPOTHESIS_STRUCT.get("GS_GAME_SPEED_INDEX", 0x4BC)
    if len(blob) >= speed_off + 4:
        speed_index = struct.unpack_from("<i", blob, speed_off)[0]
        out["fields"]["game_speed_index"] = speed_index
        out["fields"]["game_speed_notch"] = speed_index + 1 if 0 <= speed_index <= 4 else None
        out["fields"]["game_speed_note"] = (
            "GS+0x4BC i32, 0-based UI speed setting (notch=index+1); "
            "not pause/running; pause address unknown on Windows"
        )
        if 0 <= speed_index <= 4:
            out["verified"]["game_speed_index"] = speed_index
            out["verified"]["game_speed_notch"] = speed_index + 1

    out["fields"]["divisions_count"] = None
'''
if anchor not in gt:
    raise SystemExit("gamestate.py anchor not found")
if "game_speed_index" in gt:
    raise SystemExit("already present in gamestate.py")
g.write_text(gt.replace(anchor, insert, 1), encoding="utf-8")
print("patched gamestate.py")
