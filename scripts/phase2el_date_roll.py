"""Phase 2el follow: watch GS date fields across hour rollover; never Post."""
from __future__ import annotations
import json, struct, sys, time
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid
import post_abi
from config import allow_post

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2el_gs_datetime.json"


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def i32(p, a):
    return struct.unpack("<i", p.read(a, 4))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def main():
    assert not allow_post()
    p = Proc(find_pid("hoi4.exe"))
    base = p.base
    gs = u64(p, base + OV["G_GAMESTATE"])
    sess = u64(p, base + post_abi.G_SESSION)
    server = u64(p, sess + post_abi.CSession_SERVER)

    def snap():
        # read a denser window around date
        win = {hex(off): i32(p, gs + off) for off in range(0x450, 0x4E0, 4)}
        return {
            "exec": u32(p, sess + post_abi.CSession_EXEC_COUNTER),
            "seq": u32(p, server + 0xD0),
            "year": win["0x478"],
            "aux47c": win["0x47c"],
            "v480": win["0x480"],
            "v484": win["0x484"],
            "v488": win["0x488"],
            "v48c": win["0x48c"],
            "v490": win["0x490"],
            "v494": win["0x494"],
            "v498": win["0x498"],
            "win": win,
        }

    # Also search GS object for i32 month/day/hour candidates that change with v480
    # Poll until v480 increases by >=6 or 90s
    series = []
    s0 = snap()
    series.append(s0)
    t0 = time.time()
    while time.time() - t0 < 90:
        time.sleep(1.0)
        s = snap()
        if s["v480"] != series[-1]["v480"] or s["aux47c"] != series[-1]["aux47c"] or s["year"] != series[-1]["year"] or s["v484"] != series[-1]["v484"]:
            series.append(s)
            print(
                f"t={time.time()-t0:.1f} exec={s['exec']} y={s['year']} aux={s['aux47c']} "
                f"h480={s['v480']} h484={s['v484']} x488={s['v488']} x498={s['v498']}"
            )
        if s["v480"] - s0["v480"] >= 8:
            break
        # detect wrap
        if s["v480"] < series[-2]["v480"] if len(series) > 1 else False:
            print("WRAP detected")
            break

    s1 = series[-1]

    # Diff which win offsets changed
    changed = []
    for k in s0["win"]:
        if s0["win"][k] != s1["win"][k]:
            changed.append({"off": k, "from": s0["win"][k], "to": s1["win"][k], "delta": s1["win"][k] - s0["win"][k]})

    # Preferred decode models ranked
    y, aux, h480, h484 = s1["year"], s1["aux47c"], s1["v480"], s1["v484"]
    models = []

    # Model: HOI4 top-bar often "1936年1月1日 12时" — need Y M D H
    # If aux is day-of-year (1-based): Jan 28
    if 1 <= aux <= 366 and 0 <= h480 <= 23:
        dt = datetime(y, 1, 1) + timedelta(days=aux - 1, hours=h480)
        models.append({"id": "A_year_doy1based_hour480", "ui": dt.strftime("%Y-%m-%d %H:00"), "confidence": "medium",
                       "note": "aux as 1-based DOY; hour=v480 if 0..23"})
    if 0 <= aux <= 365 and 0 <= h480 <= 23:
        dt = datetime(y, 1, 1) + timedelta(days=aux, hours=h480)
        models.append({"id": "A0_year_doy0based_hour480", "ui": dt.strftime("%Y-%m-%d %H:00"), "confidence": "medium"})

    # Model: v480 is hours since 1936-01-01 00:00 (only valid if v480 grows large)
    if 0 <= h480 < 100000:
        dt = datetime(1936, 1, 1) + timedelta(hours=h480)
        models.append({"id": "B_hours_from_1936_01_01_00_via_480", "ui": dt.strftime("%Y-%m-%d %H:00"),
                       "confidence": "low-medium" if h480 < 24 else "medium",
                       "note": "fits early-session if still Jan 1 evening; fails if v480 stays <24 after many days"})

    # Model: v484 hours from 1936-01-01 00:00
    dt = datetime(1936, 1, 1) + timedelta(hours=h484)
    models.append({"id": "C_hours_from_1936_01_01_00_via_484", "ui": dt.strftime("%Y-%m-%d %H:00"),
                   "confidence": "medium", "note": "v484 tracked +2 with v480; larger absolute"})

    # Model: start bookmark 12:00 — elapsed hours = v484 - 12 or v480 related
    for label, elapsed in [("v484", h484), ("v480", h480), ("v484-12", h484 - 12), ("aux", aux)]:
        if elapsed >= 0:
            dt = datetime(1936, 1, 1, 12, 0) + timedelta(hours=elapsed)
            if dt.year == 1936:
                models.append({"id": f"D_from_bookmark_1200_plus_{label}", "ui": dt.strftime("%Y-%m-%d %H:00"), "elapsed": elapsed})

    # Relation v484 - v480
    models.append({"id": "rel_484_minus_480", "value": h484 - h480, "aux": aux, "note": "constant gap?"})

    # Check gap across series
    gaps = [s["v484"] - s["v480"] for s in series]
    auxs = [s["aux47c"] for s in series]
    hours = [s["v480"] for s in series]

    # Load prior report and merge
    prev = {}
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))

    # Best pick heuristic:
    # - v480 in 0..23 and increments by 1 aligned with time => hour-of-day
    # - aux static while hour moves => day component
    # - If session started ~hours ago from 12:00 and v480 now ~19, model B/D fit SAME DAY
    # - aux=28 with only ~7h advance from 12:00 rejects DOY=28 unless game ran much longer wall-clock
    # Wall clock since relaunch ~10:00 local, game at 1x for ~15+ min => roughly tens of game hours not 28 days
    # So aux=28 is NOT day-of-year for this session.

    wall_game_hours_est = (s1["exec"] - 0)  # rough upper if 1 exec ~ 1 hour tick sometime
    best = None
    # Prefer: year@478 + hour@480 (0-23) + need month/day elsewhere
    # OR hours@484 since epoch

    # Scan win for fields that equal month/day
    # If hour is v480, look for day in 1..31 that incremented when hour wrapped — none yet

    conclusion = {
        "proven": {
            "GS_DATE_YEAR": {"off": "G_GAMESTATE+0x478", "type": "i32", "value": y, "meaning": "calendar year (1936)"},
            "GS_TIME_A": {"off": "G_GAMESTATE+0x480", "type": "i32", "value": h480, "meaning_hyp": "hour-like counter; advances with sim; often 0..23 in this session → hour-of-day hyp"},
            "GS_TIME_B": {"off": "G_GAMESTATE+0x484", "type": "i32", "value": h484, "meaning_hyp": "parallel hour-like counter; same delta as +0x480; absolute larger"},
            "GS_DATE_AUX": {"off": "G_GAMESTATE+0x47C", "type": "i32", "value": aux, "meaning_hyp": "NOT day-of-year for short 1x sessions (held 28 while only hours advanced); layout TBD"},
        },
        "ui_best_effort": None,
        "ui_confidence": None,
        "advanced_vs_1936_01_01_12": None,
    }

    # If v480 in 0..23: interpret as hour-of-day on UNKNOWN day
    if 0 <= h480 <= 23:
        # Use hours-from-bookmark via v484 if v484 >= 12
        if h484 >= 12:
            dt = datetime(1936, 1, 1, 0, 0) + timedelta(hours=h484)
            conclusion["ui_best_effort"] = dt.strftime("%Y-%m-%d %H:00")
            conclusion["ui_confidence"] = "medium — via G_GAMESTATE+0x484 as hours-since-1936-01-01 00:00"
            conclusion["advanced_vs_1936_01_01_12"] = h484 >= 13  # past 12:00 on day 1 at least
            conclusion["model"] = "C_hours_from_1936_01_01_00_via_484"
            # cross-check hour-of-day
            conclusion["hour_of_day_from_484"] = h484 % 24
            conclusion["hour_of_day_v480"] = h480
            conclusion["hod_match_480_484"] = (h484 % 24) == h480
        dt2 = datetime(1936, 1, 1, 0, 0) + timedelta(hours=h480)
        conclusion["alt_via_480_hours"] = dt2.strftime("%Y-%m-%d %H:00")

    # If 484%24 == 480, strong evidence 480 is hour-of-day and 484 is total hours
    report = {
        "phase": "2el",
        "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "allow_post": False,
        "allow_post_runtime": bool(allow_post()),
        "never_5x": True,
        "speed": "1x",
        "pid": p.pid,
        "G_GAMESTATE": hex(gs),
        "series_len": len(series),
        "series_tail": [{k: s[k] for k in ("exec", "year", "aux47c", "v480", "v484", "v488", "v498")} for s in series[-12:]],
        "changed_offsets_0x450_0x4e0": changed,
        "gaps_484_minus_480": gaps,
        "aux_series": auxs,
        "v480_series": hours,
        "models": models,
        "conclusion": conclusion,
        "prior_samples_kept": len(prev.get("samples") or []),
    }
    # merge dump from prior if useful
    if prev.get("dump_0x400_0x520_i32"):
        report["dump_0x400_0x520_i32"] = prev["dump_0x400_0x520_i32"]
    report["samples_prior"] = prev.get("samples")

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "wrote": str(OUT),
        "conclusion": conclusion,
        "changed": changed,
        "gaps": gaps[:10],
        "hod_match": conclusion.get("hod_match_480_484"),
        "series": len(series),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())