import sys, json, os
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pid = find_pid("hoi4.exe")
out = {"pid": pid, "in_game": False}
if not pid:
    Path("research/t189_session_recheck.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    raise SystemExit(0)

p = Proc(pid)
pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
try:
    session = detect_session(p, pe)
    gs = int(session["signals"]["gs_ptr"], 16)
    res = resolve_player_country(p, gs)
    summary = read_campaign_summary(p, gs)
    ver = summary.get("verified", {})
    idler_ptr = int(session["signals"].get("idler_ptr") or "0", 16)
    b6c1 = p.read(idler_ptr+0x6c1, 1)[0] if idler_ptr else None
    out = {
        "pid": pid,
        "in_game": bool(session.get("in_game")),
        "idler": session.get("signals", {}).get("idler_class"),
        "country_ptr": res.get("country_ptr"),
        "gs_ptr": hex(gs),
        "tag": res.get("tag"),
        "player_index": res.get("player_index"),
        "date": ver.get("date_full") or ver.get("date"),
        "speed_notch": ver.get("game_speed_notch"),
        "speed_index": p.i32(gs+0x4bc),
        "hour_progress": ver.get("game_hour_progress"),
        "hour_tick": (ver.get("date_full") or {}).get("hour_tick"),
        "pause_flag_6c1": b6c1,
        "read_only": True,
    }
    Path("research/t189_session_recheck.json").write_text(json.dumps(out, indent=2, default=str)+"\n", encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
finally:
    p.close()
