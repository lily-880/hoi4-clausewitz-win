import sys, json, os
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"] = "0"
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country

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
            pe = PE(p.image_path or r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
            session = detect_session(p, pe)
            out["session"] = session.get("session")
            out["in_game"] = bool(session.get("in_game"))
            out["frontend"] = session.get("frontend")
            sig = session.get("signals") or {}
            out["signals"] = sig
            gs = sig.get("gs_ptr")
            if gs:
                gs_ptr = int(gs, 16) if isinstance(gs, str) else gs
                res = resolve_player_country(p, gs_ptr)
                out["country"] = {
                    "ok": res.get("ok"),
                    "player_index": res.get("player_index"),
                    "tag": res.get("tag"),
                    "country_ptr": res.get("country_ptr"),
                    "same_country": res.get("country_ptr") in (0x26c4b672530, "0x26c4b672530"),
                    "same_gs": gs_ptr == 0x26c259d0ff0 or (isinstance(gs, str) and int(gs, 16) == 0x26c259d0ff0),
                }
        finally:
            p.close()
except Exception as e:
    out["error"] = repr(e)
Path("research/t185_session_recheck.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({k: out[k] for k in out if k != "signals"}, indent=2, default=str, ensure_ascii=False))
if out.get("signals"):
    print("gs", out["signals"].get("gs_ptr"), "idler", out["signals"].get("idler_class"))
