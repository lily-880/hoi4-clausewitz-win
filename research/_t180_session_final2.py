import json, os, sys, struct
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0, str(Path("calling").resolve()))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, read_campaign_summary

p = Proc(find_pid("hoi4.exe"))
try:
    pe = PE(p.image_path)
    session = detect_session(p, pe)
    gs = int(session["signals"]["gs_ptr"], 16)
    res = resolve_player_country(p, gs)
    summary = read_campaign_summary(p, gs)
    # speed at known offset? prev used speed_index
    out = {
        "pid": p.pid,
        "pid_matches": p.pid==26976,
        "in_game": session["in_game"],
        "session": session["session"],
        "player": res,
        "summary": summary,
        "read_only": True,
        "no_game_method_execution": True,
        "stop": not session["in_game"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:4000])
    Path("research/t180_session_recheck_final.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
finally:
    p.close()
