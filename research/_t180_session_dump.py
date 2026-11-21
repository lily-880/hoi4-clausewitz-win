import json, os, sys
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0, str(Path("calling").resolve()))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, read_campaign_summary

pid = find_pid("hoi4.exe")
p = Proc(pid)
try:
    pe = PE(p.image_path)
    session = detect_session(p, pe)
    print("in_game", session.get("in_game"))
    print("frontend", session.get("frontend"))
    print("session field", session.get("session"))
    print("guidance", session.get("guidance"))
    print("signals", session.get("signals"))
    def slim(o, depth=0):
        if depth>3: return type(o).__name__
        if isinstance(o, dict):
            return {k: slim(v, depth+1) for k,v in o.items()}
        if isinstance(o, (list,tuple)):
            return [slim(x, depth+1) for x in o[:20]]
        if isinstance(o, int) and o>0x10000:
            return hex(o)
        return o
    print(json.dumps(slim(session), ensure_ascii=False, indent=2, default=str)[:4000])
    # prior recheck format
    prev=json.loads(Path("research/t180_session_recheck.json").read_text(encoding="utf-8"))
    print("prev keys", prev.keys())
finally:
    p.close()
