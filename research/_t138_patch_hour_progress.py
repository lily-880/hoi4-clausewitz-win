from pathlib import Path

p = Path("calling/offsets.py")
text = p.read_text(encoding="utf-8")
old = (
    "    # NOT the pause/running flag; that address is still unknown on Windows.\n"
    '    "GS_GAME_SPEED_INDEX": 0x4BC,\n'
)
new = (
    "    # NOT the pause/running flag; that address is still unknown on Windows.\n"
    "    # Observed live 2026-11-14 (pid 36620, 1x unpaused):\n"
    "    # f32 at CGameState+0x4B8, immediately before the speed index.\n"
    "    # Frozen at 0.0 while paused; while running at 1x it advances at\n"
    "    # about 0.5 per real second (0.378->0.780 in 0.8s; 0.045->0.544 in 1.0s),\n"
    "    # i.e. 0..1 over the 2 real seconds of one game hour at speed 1.\n"
    "    # This is hour progress inside the current UI hour, not a pause bool.\n"
    "    # Pause can be inferred only by sampling this (or the hour tick) twice.\n"
    '    "GS_HOUR_PROGRESS_F32": 0x4B8,\n'
    '    "GS_GAME_SPEED_INDEX": 0x4BC,\n'
)
if old not in text:
    raise SystemExit("offsets.py anchor not found")
if "GS_HOUR_PROGRESS_F32" in text:
    raise SystemExit("already present in offsets.py")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched offsets.py")

g = Path("calling/gamestate.py")
gt = g.read_text(encoding="utf-8")
oldg = '''        out["fields"]["game_speed_note"] = (
            "GS+0x4BC i32, 0-based UI speed setting (notch=index+1); "
            "not pause/running; pause address unknown on Windows"
        )
        if 0 <= speed_index <= 4:
            out["verified"]["game_speed_index"] = speed_index
            out["verified"]["game_speed_notch"] = speed_index + 1
'''
newg = '''        out["fields"]["game_speed_note"] = (
            "GS+0x4BC i32, 0-based UI speed setting (notch=index+1); "
            "GS+0x4B8 f32 is 0..1 progress inside the current game hour "
            "(ticks only while unpaused); pause bool address still unknown"
        )
        if 0 <= speed_index <= 4:
            out["verified"]["game_speed_index"] = speed_index
            out["verified"]["game_speed_notch"] = speed_index + 1
        prog_off = O.HYPOTHESIS_STRUCT.get("GS_HOUR_PROGRESS_F32", 0x4B8)
        if len(blob) >= prog_off + 4:
            hour_progress = struct.unpack_from("<f", blob, prog_off)[0]
            out["fields"]["game_hour_progress"] = hour_progress
            if 0.0 <= hour_progress <= 1.0:
                out["verified"]["game_hour_progress"] = hour_progress
'''
if oldg not in gt:
    raise SystemExit("gamestate.py anchor not found")
if "game_hour_progress" in gt:
    raise SystemExit("already present in gamestate.py")
g.write_text(gt.replace(oldg, newg, 1), encoding="utf-8")
print("patched gamestate.py")
