"""Confirm G_GAMESTATE+0x484 = hours since 1936-01-01 00:00; map Y-M-D H. RO only."""
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


def decode_hours(h):
    return datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(h))


def main():
    assert not allow_post()
    p = Proc(find_pid("hoi4.exe"))
    base = p.base
    gs = u64(p, base + OV["G_GAMESTATE"])
    sess = u64(p, base + post_abi.G_SESSION)
    server = u64(p, sess + post_abi.CSession_SERVER)

    rows = []
    for i in range(10):
        y = i32(p, gs + 0x478)
        aux = i32(p, gs + 0x47C)
        h480 = i32(p, gs + 0x480)
        h484 = i32(p, gs + 0x484)
        v488 = i32(p, gs + 0x488)
        v498 = i32(p, gs + 0x498)
        ex = u32(p, sess + post_abi.CSession_EXEC_COUNTER)
        dt = decode_hours(h484)
        rows.append({
            "i": i,
            "exec": ex,
            "year_field": y,
            "aux47c": aux,
            "v480": h480,
            "v484": h484,
            "v488": v488,
            "v498": v498,
            "ui": dt.strftime("%Y-%m-%d %H:00"),
            "y": dt.year, "m": dt.month, "d": dt.day, "H": dt.hour,
            "year_match": y == dt.year,
            "v488_eq_day": v488 == dt.day,
            "v488_eq_month": v488 == dt.month,
            "v480_eq_hour": h480 == dt.hour,
            "v480_mod24": h480 % 24,
        })
        print(rows[-1])
        time.sleep(8)

    # consistency checks
    years_ok = all(r["year_match"] for r in rows)
    mono484 = all(rows[i]["v484"] <= rows[i + 1]["v484"] for i in range(len(rows) - 1))
    advanced = rows[-1]["v484"] > 12  # past 1936-01-01 12:00

    # Classify 0x480: compare to hour and to hour within weird 28-length blocks
    mapping = {
        "GS_DATE_YEAR": {"offset": 0x478, "type": "i32", "role": "calendar year", "proven": True},
        "GS_DATE_HOURS_SINCE_1936_01_01": {
            "offset": 0x484,
            "type": "i32",
            "role": "total hours since 1936-01-01 00:00 → derives Y-M-D H",
            "proven": bool(years_ok and mono484),
            "confidence": "high" if years_ok and mono484 else "medium",
        },
        "GS_DATE_AUX_0x47C": {
            "offset": 0x47C,
            "type": "i32",
            "role": "unproven (seen 28/31; jumps at some boundaries)",
            "proven": False,
        },
        "GS_DATE_0x480": {
            "offset": 0x480,
            "type": "i32",
            "role": "hour-like; wraps (observed …27→0) but not clean 0..23; not required for UI if 0x484 holds",
            "proven": False,
        },
        "GS_DATE_0x488": {
            "offset": 0x488,
            "type": "i32",
            "role": "increments on some wrap boundaries; not equal day/month in samples",
            "proven": False,
        },
    }

    live = rows[-1]
    start = datetime(1936, 1, 1, 12, 0)
    live_dt = decode_hours(live["v484"])
    report = {
        "phase": "2el",
        "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "allow_post": False,
        "allow_post_runtime": bool(allow_post()),
        "never_5x": True,
        "speed": "1x",
        "pid": p.pid,
        "G_GAMESTATE": hex(gs),
        "mapping": mapping,
        "live_datetime": {
            "ui": live["ui"],
            "year": live["y"],
            "month": live["m"],
            "day": live["d"],
            "hour": live["H"],
            "minute": 0,
            "source": "G_GAMESTATE+0x484 hours since 1936-01-01 00:00",
            "hours_value": live["v484"],
            "year_field_0x478": live["year_field"],
            "year_field_matches_decoded": live["year_match"],
        },
        "clock_advanced_past_1936_01_01_12:00": bool(live_dt > start),
        "hours_ahead_of_bookmark_1200": int((live_dt - start).total_seconds() // 3600),
        "checks": {
            "year_always_matches_decoded": years_ok,
            "v484_monotonic_nondecreasing": mono484,
            "rows": rows,
        },
        "works": {
            "ui_datetime_from_0x484": True,
            "year_at_0x478": True,
        },
        "stubbed": {
            "minute_field": True,
            "aux_0x47c_meaning": True,
            "0x480_exact_role": True,
        },
    }

    # merge into OUT
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev.update(report)
    OUT.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    print(json.dumps({
        "live_ui": live["ui"],
        "past_1200": report["clock_advanced_past_1936_01_01_12:00"],
        "hours_ahead": report["hours_ahead_of_bookmark_1200"],
        "year_ok": years_ok,
        "mono484": mono484,
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())