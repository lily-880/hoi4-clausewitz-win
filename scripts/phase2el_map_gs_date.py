"""Phase 2el: RO-map G_GAMESTATE UI date/time fields. Never Post / never 5x."""
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


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def i32(p, a):
    return struct.unpack("<i", p.read(a, 4))[0]


def main():
    assert not allow_post(), "allow_post must stay False"
    p = Proc(find_pid("hoi4.exe"))
    base = p.base
    gs = u64(p, base + OV["G_GAMESTATE"])
    sess = u64(p, base + post_abi.G_SESSION)
    server = u64(p, sess + post_abi.CSession_SERVER)

    dump = {hex(off): i32(p, gs + off) for off in range(0x400, 0x520, 4)}

    def snap():
        return {
            "exec": u32(p, sess + post_abi.CSession_EXEC_COUNTER),
            "seq": u32(p, server + 0xD0),
            "drain": u32(p, sess + post_abi.CSession_DRAIN_COUNTER),
            "year": i32(p, gs + 0x478),
            "aux47c": i32(p, gs + 0x47C),
            "v480": i32(p, gs + 0x480),
            "v484": i32(p, gs + 0x484),
            "v488": i32(p, gs + 0x488),
            "v48c": i32(p, gs + 0x48C),
            "v490": i32(p, gs + 0x490),
            "v494": i32(p, gs + 0x494),
            "v498": i32(p, gs + 0x498),
            "v49c": i32(p, gs + 0x49C),
            "v470": i32(p, gs + 0x470),
            "v474": i32(p, gs + 0x474),
            # wider candidates that looked date-like in prior dumps
            "v4b0": i32(p, gs + 0x4B0),
            "v4b8": i32(p, gs + 0x4B8),
            "v498": i32(p, gs + 0x498),
        }

    samples = []
    t_end = time.time() + 55
    prev = snap()
    samples.append({"t": 0.0, **prev})
    t0 = time.time()
    while time.time() < t_end:
        time.sleep(1.5)
        s = snap()
        if (
            s["exec"] != prev["exec"]
            or s["v480"] != prev["v480"]
            or s["aux47c"] != prev["aux47c"]
            or s["v484"] != prev["v484"]
            or s["v488"] != prev["v488"]
            or s["year"] != prev["year"]
        ):
            samples.append({"t": round(time.time() - t0, 2), **s})
            prev = s
            if len(samples) >= 24:
                break

    # Hypothesis evaluation
    # H1: year@478, month@47c, day@480, hour@484  — reject if month>12 or day>31 at live
    # H2: year@478, doy@47c (1-366), hour@480
    # H3: year@478; hours-since-year-start @480 (or @47c)
    # H4: Paradox date as hours since 1.1.1 00:00 or since bookmark

    s0, s1 = samples[0], samples[-1]
    hyps = []

    def add(name, ok, detail):
        hyps.append({"name": name, "plausible": ok, "detail": detail})

    y, a, h, h2 = s1["year"], s1["aux47c"], s1["v480"], s1["v484"]
    add(
        "YMDH_consecutive_478",
        1930 <= y <= 1950 and 1 <= a <= 12 and 1 <= h <= 31 and 0 <= h2 <= 23,
        f"y={y} mon?={a} day?={h} hour?={h2}",
    )
    add(
        "year_doy_hour",
        1930 <= y <= 1950 and 1 <= a <= 366 and 0 <= h <= 23,
        f"y={y} doy?={a} hour?={h} twin484={h2}",
    )
    add(
        "year_and_hour_at_480",
        1930 <= y <= 1950 and 0 <= h <= 48 and h2 == h,
        f"y={y} hour_or_counter={h} twin={h2} aux={a}",
    )

    # If v480 increments ~1 per ~1 HourlyTick/exec cluster:
    d_exec = s1["exec"] - s0["exec"]
    d480 = s1["v480"] - s0["v480"]
    d484 = s1["v484"] - s0["v484"]
    daux = s1["aux47c"] - s0["aux47c"]

    # Decode attempts for UI string
    decoded = []

    # Attempt A: year + doy + hour(480) -> date
    if 1930 <= y <= 1950 and 1 <= a <= 366 and 0 <= (h % 24) <= 23:
        try:
            dt = datetime(y, 1, 1) + timedelta(days=a - 1, hours=h % 24)
            decoded.append({"model": "year_doy(aux47c)_hour(v480)", "iso": dt.strftime("%Y-%m-%d %H:00"), "dt": str(dt)})
        except Exception as e:
            decoded.append({"model": "year_doy_hour", "error": str(e)})

    # Attempt B: year + month(47c) + day(480) + hour(484) — only if ranges ok
    if 1 <= a <= 12 and 1 <= h <= 31 and 0 <= h2 <= 23:
        try:
            dt = datetime(y, a, h, h2)
            decoded.append({"model": "Y-M-D-H@478/47c/480/484", "iso": dt.strftime("%Y-%m-%d %H:00"), "dt": str(dt)})
        except Exception as e:
            decoded.append({"model": "YMDH", "error": str(e)})

    # Attempt C: hours since 1936-01-01 00:00 stored at 480 (or 47c)
    for label, val in [("v480", h), ("aux47c", a), ("v484", h2)]:
        if 0 <= val <= 90000:
            dt = datetime(1936, 1, 1) + timedelta(hours=val)
            if dt.year <= 1940:
                decoded.append({"model": f"hours_since_1936_01_01@{label}", "iso": dt.strftime("%Y-%m-%d %H:00"), "hours": val})

    # Attempt D: days since 1936-01-01 at aux, hour at 480
    if 0 <= a <= 2000 and 0 <= (h % 24) <= 23:
        dt = datetime(1936, 1, 1) + timedelta(days=a, hours=h % 24)
        if dt.year <= 1940:
            decoded.append({"model": "days_since_1936_01_01@aux47c + hour@480", "iso": dt.strftime("%Y-%m-%d %H:00"), "days": a, "hour": h % 24})

    # Attempt E: Clausewitz sometimes uses date as (year<<...) — check raw 64-bit at 478
    raw64 = u64(p, gs + 0x478)
    decoded.append({"model": "raw_u64@478", "hex": hex(raw64), "u64": raw64})

    # Scan for classic 1936,1,1,12 quadruplet anywhere in first 0x800 of GS
    hits = []
    blob = p.read(gs, 0x800)
    for off in range(0, 0x800 - 16, 4):
        vals = struct.unpack_from("<iiii", blob, off)
        if vals[0] == 1936 and vals[1] == 1 and vals[2] == 1 and 0 <= vals[3] <= 23:
            hits.append({"off": hex(off), "vals": list(vals)})
        if vals[0] == 1936 and 1 <= vals[1] <= 12 and 1 <= vals[2] <= 31 and 0 <= vals[3] <= 23:
            if abs(off - 0x478) < 0x80:
                hits.append({"off": hex(off), "vals": list(vals), "near_date_region": True})

    # Also find any 1936 followed by small ints
    ymd_near = []
    for off in range(0x450, 0x500, 4):
        vals = [i32(p, gs + off + i * 4) for i in range(6)]
        ymd_near.append({"off": hex(off), "six_i32": vals})

    report = {
        "phase": "2el",
        "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "allow_post": False,
        "allow_post_runtime": bool(allow_post()),
        "never_5x": True,
        "speed": "1x",
        "pid": p.pid,
        "G_GAMESTATE": hex(gs),
        "dump_0x400_0x520_i32": dump,
        "samples": samples,
        "deltas": {
            "exec": d_exec,
            "v480": d480,
            "v484": d484,
            "aux47c": daux,
            "year": s1["year"] - s0["year"],
        },
        "hypotheses": hyps,
        "decoded_candidates": decoded,
        "ymd_hits_in_gs_0x800": hits[:20],
        "near_478_windows": ymd_near,
        "bookmark_compare": "1936-01-01 12:00 start expected for -start_tag",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "wrote": str(OUT),
        "samples": len(samples),
        "s0": {k: s0[k] for k in ("year", "aux47c", "v480", "v484", "exec")},
        "s1": {k: s1[k] for k in ("year", "aux47c", "v480", "v484", "exec")},
        "deltas": report["deltas"],
        "decoded": decoded[:8],
        "ymd_hits": hits[:5],
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())