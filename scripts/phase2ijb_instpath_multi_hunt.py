#!/usr/bin/env python3
"""Phase 2ijb NON-Post: Instant×PATH / tri70_88 hunt on multi_n=2 OIs (CONTINUOUS).
One short 1x nudge only if Instant empty; NO Instant-empty re-poll loops; NO Post.
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

FOCUS_OIS = (65, 448, 450, 478, 45, 55, 58)
MULTI_HINT = {
    2647: {"ois": [65], "dests": [3938, 415]},
    2683: {"ois": [450], "dests": [740, 2601]},
}
FOCUS_DESTS = (415, 740, 2601, 3938, 3945, 6906, 9764, 11707, 9945, 12857, 1903)
NUDGE_WALL_S = 60  # one short 1x nudge max if Instant empty


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
        "path_dest_inter": [],
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
    # Single Instant VT check only
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
                    out["path_dest_inter"] = sorted(set(u70) | set(ids88) & path_union)
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


def run_dig(p, b, base, tag):
    dig = list(dict.fromkeys(list(FOCUS_DESTS) + list(p.DIG_FOCUS_SEED)))
    scan = p.scan_path_armies(b, base, tag, dig_focus=dig)
    army_to_ois, rev_meta = p.reverse_og50(b, base, scan["path_rows"])
    all_ois = sorted(
        {oi for ois in army_to_ois.values() for oi in ois} | set(FOCUS_OIS)
    )
    dig_ois = all_ois[:48]
    oi_digs = {str(oi): dig_oi(p, b, base, oi, scan["path_rows"]) for oi in dig_ois}

    rows = []
    for r in scan["path_rows"]:
        ois = sorted(army_to_ois.get(r["index"], []))
        seed_hit = sorted(set(r["path_ids"]) & set(FOCUS_DESTS))
        focus_oi_hit = sorted(set(ois) & set(FOCUS_OIS))
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
        if r["path_n"] > 1 and cls == "path_only":
            cls = "multi_path"
        rows.append(
            {
                "index": r["index"],
                "path_ids": r["path_ids"],
                "path_n": r["path_n"],
                "seed_hit": seed_hit,
                "ois": ois,
                "focus_ois": focus_oi_hit,
                "kinds": p.classify_ois(ois),
                "class": cls,
                "tri70_path": tri,
                "multi_hint": MULTI_HINT.get(r["index"]),
            }
        )
    by_class = defaultdict(int)
    for r in rows:
        by_class[r["class"]] += 1
    multi = [r for r in rows if r["path_n"] > 1]
    inst_ok_ois = sorted(oi for oi in dig_ois if oi_digs[str(oi)].get("inst_ok"))
    companion = [
        {"oi": oi, **pm}
        for oi in dig_ois
        for pm in (oi_digs[str(oi)].get("path_mem") or [])
    ]
    focus_oi_digs = {str(oi): oi_digs[str(oi)] for oi in FOCUS_OIS if str(oi) in oi_digs}
    return {
        "scan": scan,
        "army_to_ois": army_to_ois,
        "rev_meta": rev_meta,
        "oi_digs": oi_digs,
        "focus_oi_digs": focus_oi_digs,
        "rows": rows,
        "by_class": dict(by_class),
        "multi": multi,
        "inst_ok_ois": inst_ok_ois,
        "companion": companion,
        "dig_ois": dig_ois,
        "all_ois": all_ois,
    }


def main() -> int:
    assert allow_post() is False
    p = load_iu()
    pid = find_pid()
    assert pid
    b = Backend(pid)
    base = b.image_base
    tag = p.player_tag(b, base) or 15

    s0 = sample_clock(p, b, base, pid, tag)
    pass1 = run_dig(p, b, base, tag)
    nudged = False
    if not pass1["inst_ok_ois"]:
        # ONE short 1x nudge then re-dig once — no Instant-empty poll loop
        nudged = True
        time.sleep(NUDGE_WALL_S)
        pid2 = find_pid()
        if not pid2:
            result = "INSTPATH_GAME_DEAD"
            live = {"s0": s0, "nudged": True}
            out = {
                "phase": "2ijb",
                "result": result,
                "allow_post": False,
                "live": live,
            }
            (ROOT / "reports/phase2ijb_instpath_multi_hunt.json").write_text(
                json.dumps(out, indent=2), encoding="utf-8"
            )
            print(json.dumps(out, indent=2))
            return 1
        if pid2 != pid:
            pid = pid2
            b = Backend(pid)
            base = b.image_base
            tag = p.player_tag(b, base) or 15
        pass1 = run_dig(p, b, base, tag)
    s1 = sample_clock(p, b, base, pid, tag)

    rows = pass1["rows"]
    multi = pass1["multi"]
    inst_ok = pass1["inst_ok_ois"]
    by_class = pass1["by_class"]
    scan = pass1["scan"]
    dests = sorted({d for r in rows for d in r["path_ids"]})
    new_dests = sorted(set(dests) - set(FOCUS_DESTS))
    new_ois = sorted(set(pass1["all_ois"]) - set(FOCUS_OIS))

    if any(r["class"] in ("tri70", "tri70_88") for r in rows):
        result = "INSTPATH_TRI70_HIT"
    elif inst_ok:
        result = "INSTPATH_INST_OK_HIT"
    elif multi or scan["multi_n"] > 0:
        result = "INSTPATH_MULTI_PATH_INST_EMPTY"
    elif rows:
        result = "INSTPATH_PATH_ONLY_INST_EMPTY"
    else:
        result = "INSTPATH_EMPTY"

    year = s1["year_at_0x478"]
    day = s1["day_index_at_0x484"]
    live = {
        "pid": pid,
        "tag": tag,
        "year_at_0x478": year,
        "day_index_at_0x484": day,
        "ui_date_corrected": s1["ui_date_corrected"],
        "clock_class": "CONTINUOUS"
        if not (year == 1936 and day < 48)
        else "RELOAD_OR_NEW_CAMPAIGN",
        "drain": s1["drain"],
        "exec": s1["exec"],
        "allow_post": False,
        "speed": "1x_cli_untouched_mem",
        "nudged": nudged,
        "nudge_wall_s": NUDGE_WALL_S if nudged else 0,
        "calendar_sample": {"s0": s0, "s1": s1},
    }
    out = {
        "phase": "2ijb",
        "slice": "instpath_multi_hunt_NONPOST",
        "result": result,
        "allow_post": False,
        "note": "NON-Post Instant×PATH hunt on multi OIs; one nudge max; no Instant-empty re-poll",
        "focus_ois": list(FOCUS_OIS),
        "focus_dests": list(FOCUS_DESTS),
        "multi_hint": {str(k): v for k, v in MULTI_HINT.items()},
        "ita_ok": scan["ita_ok"],
        "empty_n": scan["empty_n"],
        "nonempty_n": scan["nonempty_n"],
        "multi_n": scan["multi_n"],
        "path_army_n": len(rows),
        "by_class": by_class,
        "by_prov_head": scan["by_prov_head"],
        "path_rows": rows,
        "multi_rows": multi,
        "companion_path_mem": pass1["companion"],
        "focus_oi_digs": pass1["focus_oi_digs"],
        "oi_digs_head": {
            str(oi): {
                k: pass1["oi_digs"][str(oi)].get(k)
                for k in (
                    "oi",
                    "inst_ok",
                    "og50_size",
                    "arr70_n",
                    "arr88_ids",
                    "path_mem",
                    "triangle70",
                    "err",
                )
            }
            for oi in pass1["dig_ois"][:24]
            if str(oi) in pass1["oi_digs"]
        },
        "reverse": pass1["rev_meta"],
        "army_to_ois": {str(k): v for k, v in pass1["army_to_ois"].items()},
        "new_dests": new_dests,
        "new_ois": new_ois,
        "inst_ok_ois": inst_ok,
        "arr88_xpath": {
            "in70_and_88": sorted(
                {
                    x
                    for oi in pass1["dig_ois"]
                    for x in (pass1["oi_digs"][str(oi)].get("in70_and_88") or [])
                }
            ),
            "cross70": sorted(
                {
                    x
                    for oi in pass1["dig_ois"]
                    for x in (pass1["oi_digs"][str(oi)].get("triangle70") or [])
                }
            ),
            "cross88": sorted(
                {
                    x
                    for oi in pass1["dig_ois"]
                    for x in (pass1["oi_digs"][str(oi)].get("cross88_path") or [])
                }
            ),
        },
        "live": live,
        "path_inst_drift_honesty": {
            "note": "multi_n PATH can exist with Instant VT false on same OI; do not treat PATH dest as Instant-validated",
            "inst_ok_ois": inst_ok,
            "multi_n": scan["multi_n"],
            "path_army_n": len(rows),
        },
    }
    (ROOT / "reports/phase2ijb_instpath_multi_hunt.json").write_text(
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
        "by_class",
        "by_prov_head",
        "army_to_ois",
        "new_dests",
        "new_ois",
        "inst_ok_ois",
        "multi_rows",
        "companion_path_mem",
        "focus_oi_digs",
        "arr88_xpath",
        "reverse",
        "live",
        "path_rows",
        "path_inst_drift_honesty",
    )
    brief = {k: out[k] for k in keys}
    (ROOT / "reports/phase2ijb_instpath_multi_hunt_summary.json").write_text(
        json.dumps(brief, indent=2, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": result,
                "nudged": nudged,
                "by_class": by_class,
                "nonempty_n": scan["nonempty_n"],
                "multi_n": scan["multi_n"],
                "inst_ok_ois": inst_ok,
                "new_dests": new_dests[:24],
                "new_ois": new_ois[:24],
                "multi_rows": multi,
                "focus_inst": {
                    str(oi): {
                        "inst_ok": pass1["focus_oi_digs"].get(str(oi), {}).get("inst_ok"),
                        "og50": pass1["focus_oi_digs"].get(str(oi), {}).get("og50_size"),
                        "arr70_n": pass1["focus_oi_digs"].get(str(oi), {}).get("arr70_n"),
                    }
                    for oi in FOCUS_OIS
                },
                "live": live,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
