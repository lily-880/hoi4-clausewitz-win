import os, sys, json, struct, time
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from clock import ui_date, ui_hour
from gamestate import resolve_player_country

OUT = Path("research")
p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
idler = p.u64(p.base + O.WINDOWS_GLOBALS["G_IDLER"])
session_slot = O.WINDOWS_GLOBALS.get("G_SESSION") or O.PROVEN_STATIC.get("G_SESSION")
session = p.u64(p.base + session_slot) if session_slot else 0
app = p.u64(idler + 0x530) if idler else 0

def read(addr, n):
    return p.try_read(addr, n) or b""
def i32(b, off):
    return struct.unpack_from("<i", b, off)[0] if off + 4 <= len(b) else None
def u32(b, off):
    return struct.unpack_from("<I", b, off)[0] if off + 4 <= len(b) else None

prev = (OUT / "_t134_speed_after_gamestate.bin").read_bytes()
gs1 = read(gs, 0x1000)
id1 = read(idler, 0x800)
se1 = read(session, 0x800)
ap1 = read(app, 0x800)
time.sleep(0.8)
gs2 = read(gs, 0x1000)
(OUT / "_t135_speed_after_gamestate.bin").write_bytes(gs1)
(OUT / "_t135_speed_after_idler.bin").write_bytes(id1)
(OUT / "_t135_speed_after_session.bin").write_bytes(se1)
(OUT / "_t135_speed_after_app.bin").write_bytes(ap1)

tick = O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"]
year = O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"]
day = O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"]
resolved = resolve_player_country(p, gs)

gs_diffs = []
for off in range(0, min(len(prev), len(gs1)) - 3, 4):
    if prev[off:off+4] != gs1[off:off+4]:
        gs_diffs.append({"off": hex(off), "prev_i32": i32(prev, off), "now_i32": i32(gs1, off)})

ticking = []
for off in range(0, min(len(gs1), len(gs2)) - 3, 4):
    if gs1[off:off+4] != gs2[off:off+4]:
        ticking.append(hex(off))

meta = {
    "captured_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pid": p.pid,
    "gs": hex(gs),
    "player_index": resolved.get("player_index"),
    "player_tag": resolved.get("tag"),
    "date": ui_date(i32(gs1, year), i32(gs1, day)),
    "ui_hour": ui_hour(u32(gs1, tick)),
    "v_0x4bc_t133_baseline": 0,
    "v_0x4bc_t134": i32(prev, 0x4bc),
    "v_0x4bc_t135": i32(gs1, 0x4bc),
    "v_0x4bc_t135_plus_0.8s": i32(gs2, 0x4bc),
    "hour_tick": u32(gs1, tick),
    "hour_tick_plus_0.8s": u32(gs2, tick),
    "clock_moved": u32(gs1, tick) != u32(gs2, tick),
    "gs_diffs_vs_t134": gs_diffs,
    "gs_ticking_offs": ticking,
}
(OUT / "_t135_speed_diff.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False, indent=2))
p.close()
