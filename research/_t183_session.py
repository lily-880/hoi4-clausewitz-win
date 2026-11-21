import sys, json, os
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"] = "0"
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary

out = {"read_only": True, "expected_pid": 26976}
try:
    pid = find_pid("hoi4.exe")
    out["pid_found"] = pid
    if not pid:
        out["in_game"] = False
        out["stop"] = "no hoi4.exe"
    else:
        p = Proc(pid)
        try:
            pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
            session = detect_session(p, pe)
            out["session"] = session
            sig = session.get("signals") or {}
            gs = sig.get("gs_ptr")
            out["in_game"] = bool(session.get("in_game") or sig.get("in_game"))
            if gs:
                gs_ptr = int(gs, 16) if isinstance(gs, str) else gs
                res = resolve_player_country(p, gs_ptr)
                out["country"] = res
                try:
                    out["campaign"] = read_campaign_summary(p, pe, gs_ptr)
                except Exception as e:
                    out["campaign_error"] = str(e)
        finally:
            p.close()
except Exception as e:
    out["error"] = repr(e)
Path("research/t183_session_recheck.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({k: out[k] for k in out if k not in ("session", "campaign")}, indent=2, default=str, ensure_ascii=False))
if "session" in out:
    sig = (out["session"] or {}).get("signals") or out["session"]
    print("session_keys", list(out["session"].keys())[:20] if isinstance(out["session"], dict) else type(out["session"]))
    print(json.dumps(out["session"], indent=2, default=str, ensure_ascii=False)[:2500])
