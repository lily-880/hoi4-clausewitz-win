import os, sys, json, struct, time
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from clock import ui_date, ui_hour
from gamestate import resolve_player_country, read_campaign_summary

OUT = Path("research")
GS_SIZE, OBJ_SIZE = 0x1000, 0x800
p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
idler = p.u64(p.base + O.WINDOWS_GLOBALS["G_IDLER"])
session_slot = O.WINDOWS_GLOBALS.get("G_SESSION") or O.PROVEN_STATIC.get("G_SESSION")
session = p.u64(p.base + session_slot) if session_slot else 0
app = p.u64(idler + 0x530) if idler else 0

def dump(addr, n, name):
    b = p.try_read(addr, n) or b""
    path = OUT / f"_t137_pause_baseline_{name}.bin"
    path.write_bytes(b)
    return {"path": str(path), "addr": hex(addr) if addr else None, "len": len(b)}

def i32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<i", b, 0)[0] if b else None
def u32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<I", b, 0)[0] if b else None

blobs = {"gamestate": dump(gs, GS_SIZE, "gamestate")}
if idler:
    blobs["idler"] = dump(idler, OBJ_SIZE, "idler")
if session:
    blobs["session"] = dump(session, OBJ_SIZE, "session")
if app:
    blobs["app"] = dump(app, OBJ_SIZE, "app")

tick1 = u32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
time.sleep(0.8)
tick2 = u32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
resolved = resolve_player_country(p, gs)
summary = read_campaign_summary(p, gs)
year = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"])
day = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"])
meta = {
    "captured_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "expected": "user reports 1x paused; will unpause and stay at 1x",
    "pid": p.pid,
    "gs": hex(gs),
    "idler": hex(idler) if idler else None,
    "session": hex(session) if session else None,
    "app": hex(app) if app else None,
    "player_index": resolved.get("player_index"),
    "player_tag": resolved.get("tag"),
    "date": ui_date(year, day),
    "ui_hour": ui_hour(tick1),
    "hour_tick_1": tick1,
    "hour_tick_2": tick2,
    "clock_moved_during_0.8s": tick1 != tick2,
    "game_speed_index": summary.get("fields", {}).get("game_speed_index"),
    "game_speed_notch": summary.get("fields", {}).get("game_speed_notch"),
    "linux_GS_PAUSE_HOURS_0x908": i32(gs + 0x908),
    "blobs": blobs,
}
(OUT / "_t137_pause_baseline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False, indent=2))
p.close()
