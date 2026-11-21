import json, os, sys
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0, str(Path("calling").resolve()))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, read_campaign_summary

pid = find_pid("hoi4.exe")
out = {"expected_pid": 26976, "read_only": True, "no_game_method_execution": True, "pid": pid}
if pid is None:
    out.update({"present": False, "in_game": False, "stop": True, "reason": "no hoi4.exe"})
    Path("research/t181_session_recheck.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(out))
    raise SystemExit(0)
p = Proc(pid)
try:
    pe = PE(p.image_path)
    session = detect_session(p, pe)
    out["pid_matches"] = pid == 26976
    out["in_game"] = bool(session.get("in_game"))
    out["session"] = session.get("session")
    out["frontend"] = session.get("frontend")
    if out["in_game"]:
        gs = int(session["signals"]["gs_ptr"], 16) if isinstance(session["signals"]["gs_ptr"], str) else session["signals"]["gs_ptr"]
        res = resolve_player_country(p, gs)
        summary = read_campaign_summary(p, gs)
        f = summary["fields"]
        out.update({
            "tag": res.get("tag") or f.get("player_tag_letter"),
            "player_index": res.get("player_index"),
            "country_ptr": res.get("country_ptr"),
            "date": f["date_full"]["ui"],
            "ui_hour": f["date_full"]["ui_hour"],
            "hour_tick": f["date_full"]["hour_tick"],
            "speed_index": f.get("game_speed_index"),
            "speed_notch": f.get("game_speed_notch"),
        })
    out["stop"] = not out["in_game"]
    Path("research/t181_session_recheck.json").write_text(json.dumps(out, indent=2, default=str)+"\n", encoding="utf-8")
    print(json.dumps(out, default=str))
finally:
    p.close()
