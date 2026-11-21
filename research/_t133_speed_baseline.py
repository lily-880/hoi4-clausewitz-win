import os, sys, json, struct, time
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from clock import ui_date, ui_hour
from gamestate import detect_session, resolve_player_country

OUT_DIR = Path("research")
GS_SIZE = 0x1000
IDLER_SIZE = 0x800
SESS_SIZE = 0x800
APP_SIZE = 0x800

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
idler_slot = O.WINDOWS_GLOBALS.get("G_IDLER")
idler = p.u64(p.base + idler_slot) if idler_slot else 0
session_slot = O.WINDOWS_GLOBALS.get("G_SESSION") or O.PROVEN_STATIC.get("G_SESSION")
session = p.u64(p.base + session_slot) if session_slot else 0

# try application via idler+0x530 if that hyp is present
app = 0
if idler:
    maybe = p.u64(idler + O.PROVEN_STATIC.get("CInGameIdler_queue_field_hyp", 0x530))
    app = maybe or 0

def i32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<i", b, 0)[0] if b else None

def u32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<I", b, 0)[0] if b else None

def u64(addr):
    b = p.try_read(addr, 8)
    return struct.unpack_from("<Q", b, 0)[0] if b else None

def dump(addr, n, name):
    b = p.try_read(addr, n) or b""
    path = OUT_DIR / f"_t133_speed_baseline_{name}.bin"
    path.write_bytes(b)
    return {"path": str(path), "addr": hex(addr), "len": len(b)}

year = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"])
day = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"])
tick1 = u32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
pause_linux = i32(gs + O.HYPOTHESIS_STRUCT["GS_PAUSE_HOURS"])
resolved = resolve_player_country(p, gs)

blobs = {
    "gamestate": dump(gs, GS_SIZE, "gamestate"),
}
if idler:
    blobs["idler"] = dump(idler, IDLER_SIZE, "idler")
if session:
    blobs["session"] = dump(session, SESS_SIZE, "session")
if app and 0x10000 < app < 0x7FFFFFFFFFFF:
    blobs["app_via_idler_0x530"] = dump(app, APP_SIZE, "app")

# clock stability: two reads ~0.8s apart (user asked not to touch speed)
time.sleep(0.8)
tick2 = u32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
year2 = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"])
day2 = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"])

# interesting scalars on GS (i32 0-8 and f32 that look like speed seconds)
gs_blob = (OUT_DIR / "_t133_speed_baseline_gamestate.bin").read_bytes()
interesting = []
for off in range(0, len(gs_blob) - 3, 4):
    iv = struct.unpack_from("<i", gs_blob, off)[0]
    fv = struct.unpack_from("<f", gs_blob, off)[0]
    rec = {"off": hex(off), "i32": iv, "f32": fv}
    keep = False
    if 0 <= iv <= 8:
        keep = True
        rec["why"] = "i32_0_8"
    if fv in (2.0, 0.5, 0.2, 0.1, 0.0) or (0.05 <= abs(fv) <= 2.5 and abs(fv) not in (1.0,)):
        # loose float note only if finite and not huge
        rec["why"] = (rec.get("why") + "+" if rec.get("why") else "") + "f32_speedish"
        keep = True
    if keep:
        interesting.append(rec)

meta = {
    "captured_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pid": p.pid,
    "gs": hex(gs),
    "idler": hex(idler) if idler else None,
    "session": hex(session) if session else None,
    "app_via_idler_0x530": hex(app) if app else None,
    "player_index": resolved.get("player_index"),
    "player_tag": resolved.get("tag"),
    "date": ui_date(year, day),
    "ui_hour": ui_hour(tick1) if tick1 is not None else None,
    "hour_tick_1": tick1,
    "hour_tick_2": tick2,
    "hour_tick_delta": (None if tick1 is None or tick2 is None else tick2 - tick1),
    "day_1": day,
    "day_2": day2,
    "linux_GS_PAUSE_HOURS_0x908": pause_linux,
    "clock_moved_during_0.8s": bool(tick2 != tick1 or day2 != day),
    "blobs": blobs,
    "gs_interesting_scalars_count": len(interesting),
}
(OUT_DIR / "_t133_speed_baseline.json").write_text(json.dumps({**meta, "gs_interesting_scalars": interesting[:200]}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False, indent=2))
p.close()
