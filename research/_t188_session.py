import sys, json, os
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, read_campaign_summary
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

# find rtti helper
import t156_objects as t156
fn = getattr(t156, "_rtti_name_from_vtable", None)
print("t156 has rtti", callable(fn))

pid = find_pid("hoi4.exe")
out = {"pid": pid, "in_game": False}
if not pid:
    Path("research/t188_session_recheck.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    raise SystemExit(0)

# t156 constructs P at import - close it if present
if hasattr(t156, "P") and t156.P is not None:
    try:
        t156.P.close()
    except Exception:
        pass

p = Proc(pid)
pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
try:
    session = detect_session(p, pe)
    gs = int(session["signals"]["gs_ptr"], 16) if session.get("signals", {}).get("gs_ptr") else 0
    summary = read_campaign_summary(p, gs) if gs else {}
    ver = summary.get("verified", {})
    idler_ptr = int(session["signals"].get("idler_ptr") or "0", 16)
    b6c1 = p.read(idler_ptr+0x6c1, 1)[0] if idler_ptr else None
    idler_name = None
    if idler_ptr and fn:
        vt = p.u64(idler_ptr)
        idler_name = fn(pe, vt - p.base)
    out = {
        "pid": pid,
        "in_game": bool(session.get("in_game")),
        "idler": idler_name,
        "country_ptr": session["signals"].get("country_ptr"),
        "gs_ptr": session["signals"].get("gs_ptr"),
        "tag": ver.get("tag") or session.get("tag"),
        "player_index": ver.get("player_index") or session.get("player_index"),
        "date": ver.get("date_full") or ver.get("date"),
        "speed_notch": ver.get("game_speed_notch"),
        "speed_index": p.i32(gs+0x4bc) if gs else None,
        "hour_progress": ver.get("game_hour_progress"),
        "hour_tick": (ver.get("date_full") or {}).get("hour_tick"),
        "pause_flag_6c1": b6c1,
        "armies_size": ver.get("own_units_count") or ver.get("armies_size"),
        "read_only": True,
    }
    Path("research/t188_session_recheck.json").write_text(json.dumps(out, indent=2, default=str)+"\n", encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
    print("session keys", session.keys())
    print("signals", json.dumps(session.get("signals", {}), default=str)[:1500])
finally:
    p.close()
