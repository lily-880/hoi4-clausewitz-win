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
CLOCK_OFFS = {
    O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"]: "GS_DATE_HOUR_TICK",
    O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"]: "GS_DATE_YEAR",
    O.HYPOTHESIS_STRUCT["GS_DATE_AUX"]: "GS_DATE_AUX",
    O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_LIKE"]: "GS_DATE_HOUR_LIKE",
    O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"]: "GS_DATE_HOURS",
    O.HYPOTHESIS_STRUCT["GS_PAUSE_HOURS"]: "GS_PAUSE_HOURS_linux",
    O.HYPOTHESIS_STRUCT["GS_GAME_SPEED_INDEX"]: "GS_GAME_SPEED_INDEX",
}

base_meta = json.loads((OUT / "_t137_pause_baseline.json").read_text(encoding="utf-8"))
base = {
    "gamestate": (OUT / "_t137_pause_baseline_gamestate.bin").read_bytes(),
    "idler": (OUT / "_t137_pause_baseline_idler.bin").read_bytes(),
    "session": (OUT / "_t137_pause_baseline_session.bin").read_bytes(),
    "app": (OUT / "_t137_pause_baseline_app.bin").read_bytes(),
}

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
idler = p.u64(p.base + O.WINDOWS_GLOBALS["G_IDLER"])
session_slot = O.WINDOWS_GLOBALS.get("G_SESSION") or O.PROVEN_STATIC.get("G_SESSION")
session = p.u64(p.base + session_slot) if session_slot else 0
app = p.u64(idler + 0x530) if idler else 0

def read_blob(addr, n):
    return p.try_read(addr, n) or b""
def i32a(b, off):
    return struct.unpack_from("<i", b, off)[0] if off + 4 <= len(b) else None
def u32a(b, off):
    return struct.unpack_from("<I", b, off)[0] if off + 4 <= len(b) else None
def f32a(b, off):
    return struct.unpack_from("<f", b, off)[0] if off + 4 <= len(b) else None

after1 = {
    "gamestate": read_blob(gs, GS_SIZE),
    "idler": read_blob(idler, OBJ_SIZE) if idler else b"",
    "session": read_blob(session, OBJ_SIZE) if session else b"",
    "app": read_blob(app, OBJ_SIZE) if app else b"",
}
time.sleep(0.8)
after2 = {
    "gamestate": read_blob(gs, GS_SIZE),
    "idler": read_blob(idler, OBJ_SIZE) if idler else b"",
    "session": read_blob(session, OBJ_SIZE) if session else b"",
    "app": read_blob(app, OBJ_SIZE) if app else b"",
}
for name, blob in after1.items():
    (OUT / f"_t138_unpause_{name}.bin").write_bytes(blob)
for name, blob in after2.items():
    (OUT / f"_t138_unpause2_{name}.bin").write_bytes(blob)

def word_diffs(name, a, b):
    n = min(len(a), len(b))
    out = []
    for off in range(0, n - 3, 4):
        if a[off:off+4] != b[off:off+4]:
            rec = {
                "region": name, "off": hex(off), "off_i": off,
                "before_i32": i32a(a, off), "after_i32": i32a(b, off),
                "before_u32": u32a(a, off), "after_u32": u32a(b, off),
                "before_f32": f32a(a, off), "after_f32": f32a(b, off),
            }
            if name == "gamestate" and off in CLOCK_OFFS:
                rec["known"] = CLOCK_OFFS[off]
            out.append(rec)
    return out

def slim(r):
    return {k: r[k] for k in r if k != "off_i"}

stable, ticking, summary = [], [], {}
all_one_shot = []
for name in ("gamestate", "idler", "session", "app"):
    d1 = word_diffs(name, base[name], after1[name])
    d2 = {r["off_i"] for r in word_diffs(name, after1[name], after2[name])}
    one, tick = [], []
    for r in d1:
        r["changed_again_0.8s_later"] = r["off_i"] in d2
        (tick if r["changed_again_0.8s_later"] else one).append(r)
    bi = next((r for r in one if r["region"]==name), None)
    for r in one:
        bi, ai = r["before_i32"], r["after_i32"]
        if {bi, ai} <= {0, 1} and bi != ai:
            r["likely"] = "bool_flipped"
            stable.append(r)
        elif bi is not None and ai is not None and 0 <= bi <= 8 and 0 <= ai <= 8 and bi != ai:
            r["likely"] = "enum_0_8"
            stable.append(r)
        all_one_shot.append(slim(r))
    ticking.extend(tick)
    summary[name] = {
        "words_changed_vs_baseline": len(d1),
        "one_shot_stable": len(one),
        "also_ticking": len(tick),
        "words_ticking_after1_to_after2": len(d2),
    }

tick_off = O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"]
resolved = resolve_player_country(p, gs)
summary_read = read_campaign_summary(p, gs)
year = i32a(after1["gamestate"], O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"])
day = i32a(after1["gamestate"], O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"])
t1 = u32a(after1["gamestate"], tick_off)
t2 = u32a(after2["gamestate"], tick_off)

meta = {
    "captured_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pid": p.pid,
    "same_pid": p.pid == base_meta["pid"],
    "gs_same": hex(gs) == base_meta["gs"],
    "player_tag": resolved.get("tag"),
    "date": ui_date(year, day),
    "ui_hour": ui_hour(t1),
    "game_speed_index": summary_read.get("fields", {}).get("game_speed_index"),
    "game_speed_notch": summary_read.get("fields", {}).get("game_speed_notch"),
    "hour_tick_baseline": base_meta.get("hour_tick_1"),
    "hour_tick_after1": t1,
    "hour_tick_after2": t2,
    "clock_moved_during_0.8s": t1 != t2,
    "linux_0x908_base": base_meta.get("linux_GS_PAUSE_HOURS_0x908"),
    "linux_0x908_after": i32a(after1["gamestate"], 0x908),
    "region_summary": summary,
    "stable_bool_or_enum": [slim(r) for r in stable],
    "one_shot_diff_count": len(all_one_shot),
    "one_shot_diffs": all_one_shot,
    "ticking_known_clock": [slim(r) for r in ticking if r.get("known")],
}
(OUT / "_t138_unpause_diff.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: meta[k] for k in meta if k != "one_shot_diffs"}, ensure_ascii=False, indent=2))
print("--- ONE-SHOT ---")
print(json.dumps(all_one_shot, ensure_ascii=False, indent=2))
p.close()
