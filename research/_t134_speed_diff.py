import os, sys, json, struct, time
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from clock import ui_date, ui_hour
from gamestate import resolve_player_country

OUT = Path("research")
GS_SIZE, OBJ_SIZE = 0x1000, 0x800
CLOCK_OFFS = {
    O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"]: "GS_DATE_HOUR_TICK",
    O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"]: "GS_DATE_YEAR",
    O.HYPOTHESIS_STRUCT.get("GS_DATE_MONTH", 0x47C): "GS_DATE_MONTH?",
    0x480: "GS+0x480_not_hour",
    O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"]: "GS_DATE_HOURS/day",
    O.HYPOTHESIS_STRUCT["GS_PAUSE_HOURS"]: "GS_PAUSE_HOURS_linux",
}
SPEED_FLOATS = {2.0, 0.5, 0.2, 0.1, 0.0}

base_meta = json.loads((OUT / "_t133_speed_baseline.json").read_text(encoding="utf-8"))
base_blobs = {
    "gamestate": (OUT / "_t133_speed_baseline_gamestate.bin").read_bytes(),
    "idler": (OUT / "_t133_speed_baseline_idler.bin").read_bytes(),
    "session": (OUT / "_t133_speed_baseline_session.bin").read_bytes(),
    "app": (OUT / "_t133_speed_baseline_app.bin").read_bytes(),
}

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
idler = p.u64(p.base + O.WINDOWS_GLOBALS["G_IDLER"]) if O.WINDOWS_GLOBALS.get("G_IDLER") else 0
session_slot = O.WINDOWS_GLOBALS.get("G_SESSION") or O.PROVEN_STATIC.get("G_SESSION")
session = p.u64(p.base + session_slot) if session_slot else 0
app = p.u64(idler + 0x530) if idler else 0

def i32a(b, off):
    return struct.unpack_from("<i", b, off)[0] if off + 4 <= len(b) else None
def u32a(b, off):
    return struct.unpack_from("<I", b, off)[0] if off + 4 <= len(b) else None
def f32a(b, off):
    return struct.unpack_from("<f", b, off)[0] if off + 4 <= len(b) else None
def u64a(b, off):
    return struct.unpack_from("<Q", b, off)[0] if off + 8 <= len(b) else None

def read_blob(addr, n):
    return p.try_read(addr, n) or b""

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
    (OUT / f"_t134_speed_after_{name}.bin").write_bytes(blob)
for name, blob in after2.items():
    (OUT / f"_t134_speed_after2_{name}.bin").write_bytes(blob)

def classify_val(iv, fv):
    tags = []
    if iv is not None and 0 <= iv <= 8:
        tags.append("i32_0_8")
    if fv is not None and fv in SPEED_FLOATS:
        tags.append("exact_speed_float")
    if iv is not None and iv in (0, 1):
        tags.append("boolish")
    return tags

def word_diffs(name, a, b, step=4):
    n = min(len(a), len(b))
    out = []
    off = 0
    while off + step <= n:
        if a[off:off+step] != b[off:off+step]:
            rec = {
                "region": name,
                "off": hex(off),
                "off_i": off,
                "before_i32": i32a(a, off),
                "after_i32": i32a(b, off),
                "before_u32": u32a(a, off),
                "after_u32": u32a(b, off),
                "before_f32": f32a(a, off),
                "after_f32": f32a(b, off),
            }
            if name == "gamestate" and off in CLOCK_OFFS:
                rec["known"] = CLOCK_OFFS[off]
            rec["tags"] = classify_val(rec["after_i32"], rec["after_f32"]) + classify_val(rec["before_i32"], rec["before_f32"])
            rec["tags"] = sorted(set(rec["tags"]))
            out.append(rec)
        off += step
    return out

# baseline -> after1, and after1 -> after2 (ticking)
stable_speedish = []
ticking = []
all_base_after = {}
summary = {}
for name in ("gamestate", "idler", "session", "app"):
    d1 = word_diffs(name, base_blobs[name], after1[name])
    d2 = {r["off_i"] for r in word_diffs(name, after1[name], after2[name])}
    all_base_after[name] = d1
    one_shot = []
    tick = []
    for r in d1:
        r["changed_again_0.8s_later"] = r["off_i"] in d2
        if r["changed_again_0.8s_later"]:
            tick.append(r)
        else:
            one_shot.append(r)
            # highlight likely speed
            bi, ai = r["before_i32"], r["after_i32"]
            bf, af = r["before_f32"], r["after_f32"]
            likely = False
            reason = []
            if ai is not None and bi is not None and 0 <= bi <= 8 and 0 <= ai <= 8 and bi != ai:
                likely = True
                reason.append("enum_0_8_changed")
            if (bf in SPEED_FLOATS or af in SPEED_FLOATS) and bf != af:
                likely = True
                reason.append("speed_float_changed")
            if {bi, ai} <= {0, 1} and bi != ai:
                likely = True
                reason.append("bool_flipped")
            if likely:
                r["likely_reasons"] = reason
                stable_speedish.append(r)
    ticking.extend(tick)
    summary[name] = {
        "bytes_base": len(base_blobs[name]),
        "bytes_after": len(after1[name]),
        "words_changed_vs_baseline": len(d1),
        "one_shot_stable": len(one_shot),
        "also_ticking": len(tick),
        "words_ticking_after1_to_after2": len(d2),
    }

tick1 = u32a(after1["gamestate"], O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
tick2 = u32a(after2["gamestate"], O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
year = i32a(after1["gamestate"], O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"])
day = i32a(after1["gamestate"], O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"])
resolved = resolve_player_country(p, gs)

# also note 8-byte one-shots that look like pointers (exclude from speed claim)
def slim(r):
    out = {k: r[k] for k in (
        "region","off","before_i32","after_i32","before_u32","after_u32",
        "before_f32","after_f32","known","tags","likely_reasons","changed_again_0.8s_later"
    ) if k in r}
    return out

# include ALL one-shot diffs (not just speedish) for inspection, capped
all_one_shot = []
for name, d1 in all_base_after.items():
    for r in d1:
        if not r["changed_again_0.8s_later"]:
            all_one_shot.append(slim(r))

meta = {
    "captured_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pid": p.pid,
    "same_pid_as_baseline": p.pid == base_meta["pid"],
    "gs": hex(gs),
    "gs_same": hex(gs) == base_meta["gs"],
    "player_index": resolved.get("player_index"),
    "player_tag": resolved.get("tag"),
    "date": ui_date(year, day),
    "ui_hour": ui_hour(tick1) if tick1 is not None else None,
    "hour_tick_after1": tick1,
    "hour_tick_after2": tick2,
    "hour_tick_delta_0.8s": None if tick1 is None or tick2 is None else tick2 - tick1,
    "clock_moved_during_0.8s": bool(tick2 != tick1),
    "linux_GS_PAUSE_HOURS_0x908_after": i32a(after1["gamestate"], 0x908),
    "linux_GS_PAUSE_HOURS_0x908_baseline": base_meta.get("linux_GS_PAUSE_HOURS_0x908"),
    "region_summary": summary,
    "stable_speedish_candidates": [slim(r) for r in stable_speedish],
    "one_shot_diff_count": len(all_one_shot),
    "one_shot_diffs": all_one_shot,
    "ticking_diff_count": len(ticking),
    "ticking_known_clock": [slim(r) for r in ticking if r.get("known")],
}
(OUT / "_t134_speed_diff.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: meta[k] for k in meta if k not in ("one_shot_diffs",)}, ensure_ascii=False, indent=2))
print("--- ONE-SHOT DIFFS ---")
print(json.dumps(all_one_shot, ensure_ascii=False, indent=2))
p.close()
