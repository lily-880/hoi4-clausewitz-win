# reuse prior session detector if possible; otherwise compact recheck
import json, os, struct
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
import sys
sys.path.insert(0, str(Path("calling").resolve()))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, read_campaign_summary

pid = find_pid("hoi4.exe")
print("find_pid", pid)
if pid is None:
    Path("research/t180_session_recheck_final.json").write_text(json.dumps({"present": False, "reason": "no hoi4.exe"}), encoding="utf-8")
    raise SystemExit("NO_HOI4")
p = Proc(pid)
try:
    pe = PE(p.image_path)
    session = detect_session(p, pe)
    print("session keys", session.keys() if isinstance(session, dict) else type(session))
    # detect_session returns dict with session/gs etc. Print compact.
    out = {"pid": p.pid, "present": True}
    if isinstance(session, dict):
        out["session"] = {k: (hex(v) if isinstance(v,int) and v>0x10000 else v) for k,v in session.items() if k!="raw"}
        # try to show inner
        if "session" in session and isinstance(session["session"], dict):
            s=session["session"]
            out["inner"] = {k: (hex(v) if isinstance(v,int) and v>0x10000 else v) for k,v in s.items() if not isinstance(v, (bytes, list, dict))}
    gs = session.get("gs_ptr") or session.get("gs") or (session.get("session") or {}).get("gs_ptr") or (session.get("session") or {}).get("gs")
    print("gs", hex(gs) if isinstance(gs,int) else gs)
    if gs:
        res = resolve_player_country(p, gs)
        summary = read_campaign_summary(p, gs)
        out["player"] = res
        out["summary"] = summary
        print("player", res)
        print("summary", json.dumps(summary, default=str)[:2000])
    Path("research/t180_session_recheck_final.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
finally:
    p.close()
