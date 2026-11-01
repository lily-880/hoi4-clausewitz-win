#!/usr/bin/env python3
"""Phase 2iz NON-Post: 1x calendar advance then denser PATH200 (oi=45/55 + new).
Does NOT Post / ALLOW_POST / Instant-empty re-poll / speed-mem write.
"""
from __future__ import annotations
import json, sys, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import importlib.util
from calling.process import Backend, find_pid
from calling.config import allow_post
from calling.clock import ui_date
from calling.handle import resolve_handle

SEED_PROVS = (9945, 12857)
KNOWN_FOCUS_OIS = (45, 55, 57, 70)
PRIOR_DESTS = {9945, 12857}
ADVANCE_WALL_S = 150  # ~meaningful days @1x; no speed-mem write


def load_iu():
    spec = importlib.util.spec_from_file_location(
        "p2iu", ROOT / "scripts/phase2iu_path200_focus740_og50.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dig_oi(p, b, base, oi, path_rows):
    out = {
        "oi": oi,
        "inst_ok": False,
        "og50_size": 0,
        "arr70_n": 0,
        "arr88_ids": [],
        "path_mem": [],
        "triangle70": [],
        "in70_not_88": [],
        "in70_and_88": [],
        "cross88_path": [],
    }
    try:
        hdr = resolve_handle(b, p.TYPE_OG, oi, base)
    except Exception as e:
        out["err"] = type(e).__name__
        return out
    if not hdr:
        out["err"] = "no_hdr"
        return out
    og = hdr + 0x10
    arr50 = p.read_cpdx_ptrs(b, base, og + 0x50, 64) or {}
    ptrs = arr50.get("ptrs") or []
    out["og50_size"] = len(ptrs)
    want = {}
    for r in path_rows:
        want[r["army"]] = r["index"]
        want[r["army"] + p.CA_MI_OFF] = r["index"]
    for ptr in ptrs:
        if not ptr:
            continue
        idx = want.get(ptr) or want.get(ptr - p.CA_MI_OFF)
        if idx is not None:
            out["path_mem"].append(
                {
                    "index": idx,
                    "path_ids": next(
                        (r["path_ids"] for r in path_rows if r["index"] == idx), []
                    ),
                }
            )
    try:
        if hasattr(p, "TYPE_INST"):
            ih = resolve_handle(b, p.TYPE_INST, oi, base)
            if ih:
                inst = ih + 0x10
                vt = p.try_u64(b, inst)
                out["inst_ok"] = bool(
                    vt and ((vt - base) & 0xFFFFFFFF) == p.INST_VT
                )
                if out["inst_ok"]:
                    a70 = p.read_cpdx_u32(b, base, inst + 0x70, 64) or {}
                    a88 = p.read_cpdx_ptrs(b, base, inst + 0x88, 48) or {}
                    u70 = a70.get("u32s") or a70.get("ids") or []
                    out["arr70_n"] = len(u70)
                    ids88 = []
                    for cp in (a88.get("ptrs") or [])[:48]:
                        if not cp:
                            continue
                        cvt = p.try_u64(b, cp)
                        if cvt and ((cvt - base) & 0xFFFFFFFF) == p.CP_VT:
                            pid_ = p.try_u32(b, cp + 0xA4)
                            if pid_ and p.looks_like_province(pid_):
                                ids88.append(pid_)
                    out["arr88_ids"] = ids88
                    path_union = set(x for r in path_rows for x in r["path_ids"])
                    in70 = set(u70) & path_union
                    in88 = set(ids88) & path_union
                    out["triangle70"] = sorted(in70)
                    out["in70_and_88"] = sorted(in70 & in88)
                    out["in70_not_88"] = sorted(in70 - in88)
                    out["cross88_path"] = sorted(in88)
    except Exception as e:
        out["inst_exc"] = type(e).__name__
    return out


def sample_clock(p, b, base, pid, tag):
    m = p.live_meta(b, base, pid, tag)
    y = int(m.get("year_at_0x478") or 0)
    d = int(m.get("hours") or 0)
    return {
        "day_index_at_0x484": d,
        "ui_date_corrected": ui_date(y, d),
        "year_at_0x478": y,
        "drain": m.get("drain"),
        "exec": m.get("exec"),
        "pending": m.get("pending"),
    }


def ws_mb():
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        # fallback: skip — caller uses live health from outer
        return None
    except Exception:
        return None


def main() -> int:
    assert allow_post() is False
    p = load_iu()
    pid = find_pid()
    assert pid
    b = Backend(pid)
    base = b.image_base
    tag = p.player_tag(b, base) or 15

    s0 = sample_clock(p, b, base, pid, tag)
    # Advance at current 1x (CLI); do NOT write speed memory
    time.sleep(ADVANCE_WALL_S)
    # re-attach in case
    pid2 = find_pid()
    if not pid2:
        out_dead = {
            "phase": "2iz",
            "result": "PATH200_ADVANCE_GAME_DEAD",
            "allow_post": False,
            "live": {"s0": s0},
        }
        (ROOT / "reports/phase2iz_path200_advance_dense.json").write_text(
            json.dumps(out_dead, indent=2), encoding="utf-8"
        )
        print(json.dumps(out_dead, indent=2))
        return 1
    if pid2 != pid:
        pid = pid2
        b = Backend(pid)
        base = b.image_base
        tag = p.player_tag(b, base) or 15
    s1 = sample_clock(p, b, base, pid, tag)
    calendar_ok = (s1["day_index_at_0x484"] > s0["day_index_at_0x484"]) or (
        (s1["exec"] or 0) > (s0["exec"] or 0)
    )
    day_delta = s1["day_index_at_0x484"] - s0["day_index_at_0x484"]

    dig = list(
        dict.fromkeys(
            list(SEED_PROVS)
            + list(p.DIG_FOCUS_SEED)
            + [256, 915, 3816, 3938, 4527, 6867, 884, 918, 932, 885, 1053, 1869]
        )
    )
    scan = p.scan_path_armies(b, base, tag, dig_focus=dig)
    army_to_ois, rev_meta = p.reverse_og50(b, base, scan["path_rows"])
    all_ois = sorted(
        {oi for ois in army_to_ois.values() for oi in ois} | set(KNOWN_FOCUS_OIS)
    )
    dig_ois = all_ois[:32]
    oi_digs = {str(oi): dig_oi(p, b, base, oi, scan["path_rows"]) for oi in dig_ois}

    rows = []
    for r in scan["path_rows"]:
        ois = sorted(army_to_ois.get(r["index"], []))
        seed_hit = sorted(set(r["path_ids"]) & set(SEED_PROVS))
        dig_hit = sorted(set(r["path_ids"]) & set(dig))
        focus_oi_hit = sorted(set(ois) & set(KNOWN_FOCUS_OIS))
        cls = "path_only"
        tri = []
        for oi in ois:
            d = oi_digs.get(str(oi)) or {}
            inter = sorted(set(r["path_ids"]) & set(d.get("triangle70") or []))
            if inter:
                cls = "tri70"
                tri = inter
                break
            if d.get("inst_ok") and set(r["path_ids"]) & set(d.get("arr88_ids") or []):
                cls = "tri70_88"
                tri = sorted(set(r["path_ids"]) & set(d.get("arr88_ids") or []))
                break
        if focus_oi_hit and seed_hit and cls == "path_only":
            cls = "focus_oi_seed"
        rows.append(
            {
                "index": r["index"],
                "path_ids": r["path_ids"],
                "path_n": r["path_n"],
                "dig_hit": dig_hit,
                "seed_hit": seed_hit,
                "ois": ois,
                "focus_ois": focus_oi_hit,
                "kinds": p.classify_ois(ois),
                "class": cls,
                "tri70_path": tri,
            }
        )

    by_class = defaultdict(int)
    for r in rows:
        by_class[r["class"]] += 1
    multi = [r for r in rows if r["path_n"] > 1]
    focus_rows = [r for r in rows if r["seed_hit"] or r["focus_ois"] or r["dig_hit"]]
    dests = sorted({pid_ for r in rows for pid_ in r["path_ids"]})
    new_dests = sorted(set(dests) - PRIOR_DESTS)
    new_ois = sorted(set(all_ois) - set(KNOWN_FOCUS_OIS))
    inst_ok_ois = sorted(oi for oi in dig_ois if oi_digs[str(oi)].get("inst_ok"))
    companion = [
        {"oi": oi, **pm}
        for oi in dig_ois
        for pm in (oi_digs[str(oi)].get("path_mem") or [])
    ]

    if not calendar_ok:
        result = "PATH200_ADVANCE_STALL"
    elif any(r["class"] in ("tri70", "tri70_88") for r in rows):
        result = "PATH200_ADVANCE_TRI70_HIT"
    elif multi or new_dests or (scan["multi_n"] > 0):
        result = "PATH200_ADVANCE_MULTI_HIT"
    elif new_ois or len(focus_rows) >= 2 or companion:
        result = "PATH200_ADVANCE_DENSE_HIT"
    elif rows:
        result = "PATH200_ADVANCE_PATH_ONLY"
    else:
        result = "PATH200_ADVANCE_EMPTY"

    year = s1["year_at_0x478"]
    day = s1["day_index_at_0x484"]
    live = {
        "pid": pid,
        "tag": tag,
        "year_at_0x478": year,
        "day_index_at_0x484": day,
        "ui_date_corrected": s1["ui_date_corrected"],
        "clock_class": "RELOAD_OR_NEW_CAMPAIGN"
        if year == 1936 and day < 48
        else "CONTINUOUS",
        "drain": s1["drain"],
        "exec": s1["exec"],
        "allow_post": False,
        "speed": "1x_cli_untouched_mem",
        "advance_wall_s": ADVANCE_WALL_S,
        "day_delta": day_delta,
        "calendar_sample": {"s0": s0, "s1": s1, "calendar_ok": calendar_ok},
        "ws_note": "outer_shell_reports_WS; dig does not write speed",
    }
    out = {
        "phase": "2iz",
        "slice": "path200_advance_dense_NONPOST",
        "result": result,
        "allow_post": False,
        "note": "NON-Post; 1x wall advance then denser PATH200; Post scripts NOT re-run",
        "focus_ois_known": list(KNOWN_FOCUS_OIS),
        "seed_provs": list(SEED_PROVS),
        "dig_focus": dig,
        "ita_ok": scan["ita_ok"],
        "empty_n": scan["empty_n"],
        "nonempty_n": scan["nonempty_n"],
        "multi_n": scan["multi_n"],
        "path_army_n": len(rows),
        "focus_row_n": len(focus_rows),
        "by_class": dict(by_class),
        "by_prov_head": scan["by_prov_head"],
        "path_rows": rows,
        "companion_path_mem": companion,
        "oi_digs": oi_digs,
        "reverse": rev_meta,
        "army_to_ois": {str(k): v for k, v in army_to_ois.items()},
        "new_dests": new_dests,
        "new_ois": new_ois,
        "inst_ok_ois": inst_ok_ois,
        "vs_2iy": {
            "prior_nonempty": 2,
            "prior_multi": 0,
            "prior_dests": [9945, 12857],
            "prior_ois": [45, 55],
            "delta_nonempty": scan["nonempty_n"] - 2,
            "delta_multi": scan["multi_n"] - 0,
        },
        "arr88_xpath": {
            "in70_and_88": sorted(
                {
                    x
                    for oi in dig_ois
                    for x in (oi_digs[str(oi)].get("in70_and_88") or [])
                }
            ),
            "in70_not_88": sorted(
                {
                    x
                    for oi in dig_ois
                    for x in (oi_digs[str(oi)].get("in70_not_88") or [])
                }
            ),
            "cross70": sorted(
                {
                    x
                    for oi in dig_ois
                    for x in (oi_digs[str(oi)].get("triangle70") or [])
                }
            ),
            "cross88": sorted(
                {
                    x
                    for oi in dig_ois
                    for x in (oi_digs[str(oi)].get("cross88_path") or [])
                }
            ),
        },
        "live": live,
        "path_inst_drift_honesty": {
            "note": "PATH nonempty may exist without Instant VT on same OI; agent must not treat PATH dest as Instant-validated order",
            "inst_ok_ois": inst_ok_ois,
            "path_army_n": len(rows),
        },
    }
    (ROOT / "reports/phase2iz_path200_advance_dense.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    keys = (
        "phase",
        "slice",
        "result",
        "allow_post",
        "note",
        "path_army_n",
        "nonempty_n",
        "multi_n",
        "focus_row_n",
        "by_class",
        "by_prov_head",
        "army_to_ois",
        "new_dests",
        "new_ois",
        "inst_ok_ois",
        "companion_path_mem",
        "arr88_xpath",
        "vs_2iy",
        "reverse",
        "live",
        "path_rows",
        "path_inst_drift_honesty",
    )
    brief = {k: out[k] for k in keys}
    (ROOT / "reports/phase2iz_path200_advance_dense_summary.json").write_text(
        json.dumps(brief, indent=2, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": result,
                "calendar_ok": calendar_ok,
                "day_delta": day_delta,
                "by_class": dict(by_class),
                "nonempty_n": scan["nonempty_n"],
                "multi_n": scan["multi_n"],
                "new_dests": new_dests[:32],
                "new_ois": new_ois[:32],
                "inst_ok_ois": inst_ok_ois,
                "army_to_ois": out["army_to_ois"],
                "live": live,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
