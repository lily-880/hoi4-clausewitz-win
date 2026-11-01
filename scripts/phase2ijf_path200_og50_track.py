#!/usr/bin/env python3
"""Phase 2ijf NON-Post: PATH200/OG50 polish WITHOUT Instant VT checks.
Instant blocker PARKED (2ijb). No Instant-empty / Inst70 / ARR88 / tri70 polls.
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

FOCUS_OIS = (65, 450, 448, 473, 495, 503, 504, 478, 45, 55, 58)
PRIOR_DESTS = {
    415, 740, 2601, 3938, 3945, 6906, 9764, 11707, 9945, 12857, 1903, 832
}
# known Instant hub — ONE-SHOT OG/order-graph only, not Instant-empty poll
KNOWN_INST_HUB_OI = 481


def load_iu():
    spec = importlib.util.spec_from_file_location(
        "p2iu", ROOT / "scripts/phase2iu_path200_focus740_og50.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def og50_path_mem(p, b, base, oi, path_rows):
    """OG+0x50 membership only — NO Instant VT / Inst70 / ARR88."""
    out = {"oi": oi, "og50_size": 0, "path_mem": [], "err": None}
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
                    "path_n": next(
                        (r["path_n"] for r in path_rows if r["index"] == idx), 0
                    ),
                }
            )
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


def main() -> int:
    assert allow_post() is False
    p = load_iu()
    pid = find_pid()
    assert pid
    b = Backend(pid)
    base = b.image_base
    tag = p.player_tag(b, base) or 15

    s0 = sample_clock(p, b, base, pid, tag)
    time.sleep(3)
    s1 = sample_clock(p, b, base, pid, tag)
    calendar_ok = (s1["day_index_at_0x484"] > s0["day_index_at_0x484"]) or (
        (s1["exec"] or 0) > (s0["exec"] or 0)
    )

    dig = list(dict.fromkeys(list(PRIOR_DESTS) + list(p.DIG_FOCUS_SEED)))
    scan = p.scan_path_armies(b, base, tag, dig_focus=dig)
    army_to_ois, rev_meta = p.reverse_og50(b, base, scan["path_rows"])
    all_ois = sorted(
        {oi for ois in army_to_ois.values() for oi in ois} | set(FOCUS_OIS)
    )
    # OG50-only dig — NO Instant
    og_digs = {
        str(oi): og50_path_mem(p, b, base, oi, scan["path_rows"])
        for oi in sorted(set(all_ois) | set(FOCUS_OIS))[:64]
    }

    rows = []
    for r in scan["path_rows"]:
        ois = sorted(army_to_ois.get(r["index"], []))
        seed_hit = sorted(set(r["path_ids"]) & PRIOR_DESTS)
        focus_oi_hit = sorted(set(ois) & set(FOCUS_OIS))
        cls = "multi_path" if r["path_n"] > 1 else "path_only"
        if focus_oi_hit and seed_hit and cls == "path_only":
            cls = "focus_oi_seed"
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
            }
        )
    by_class = defaultdict(int)
    for r in rows:
        by_class[r["class"]] += 1
    multi = [r for r in rows if r["path_n"] > 1]
    dests = sorted({d for r in rows for d in r["path_ids"]})
    new_dests = sorted(set(dests) - PRIOR_DESTS)
    new_ois = sorted(set(all_ois) - set(FOCUS_OIS))
    companion = [
        {"oi": int(k), **pm}
        for k, d in og_digs.items()
        for pm in (d.get("path_mem") or [])
    ]
    # focus OG50 matrix
    focus_og = {str(oi): og_digs.get(str(oi)) for oi in FOCUS_OIS}

    hub481 = {"skipped": True, "reason": "Instant peacetime PARKED; no 481 Instant dig"}

    year = s1["year_at_0x478"]
    day = s1["day_index_at_0x484"]
    if scan["multi_n"] > 0 and (new_dests or new_ois or companion):
        result = "PATH200_OG50_DENSE2_MULTI_HIT"
    elif scan["multi_n"] > 0:
        result = "PATH200_OG50_DENSE2_MULTI_STABLE"
    elif new_dests or new_ois:
        result = "PATH200_OG50_DENSE2_HIT"
    elif rows:
        result = "PATH200_OG50_DENSE2_PATH_ONLY"
    else:
        result = "PATH200_OG50_DENSE2_EMPTY"

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
        "calendar_ok": calendar_ok,
        "calendar_sample": {"s0": s0, "s1": s1},
    }
    out = {
        "phase": "2ijf",
        "slice": "path200_og50_dense2_NO_INSTANT_NONPOST",
        "result": result,
        "allow_post": False,
        "note": "NON-Post PATH200/OG50 denser track vs 2ije; Instant PARKED; no Instant VT checks",
        "instant_parked": {
            "reason": "INSTPATH_MULTI_PATH_INST_EMPTY peacetime; wait wartime or human midflight CMove",
            "do_not": [
                "Instant map re-poll",
                "Inst70 empty re-poll",
                "ARR88 empty re-poll",
                "tri70 empty re-poll",
                "peacetime path OI Instant VT dig",
            ],
            "path_ne_inst_honesty": True,
        },
        "focus_ois": list(FOCUS_OIS),
        "ita_ok": scan["ita_ok"],
        "empty_n": scan["empty_n"],
        "nonempty_n": scan["nonempty_n"],
        "multi_n": scan["multi_n"],
        "path_army_n": len(rows),
        "by_class": dict(by_class),
        "by_prov_head": scan["by_prov_head"],
        "path_rows": rows,
        "multi_rows": multi,
        "companion_path_mem": companion,
        "focus_og50": focus_og,
        "og_digs_head": {k: og_digs[k] for k in list(og_digs)[:32]},
        "reverse": rev_meta,
        "army_to_ois": {str(k): v for k, v in army_to_ois.items()},
        "new_dests": new_dests,
        "new_ois": new_ois,
        "hub481_oneshot": hub481,
        "vs_2ije": {
            "prior_multi": 1,
            "prior_nonempty": 23,
            "prior_new_ois": [504],
            "prior_new_dests": [832],
            "prior_multi_row": {"index": 2649, "path_ids": [832, 415], "oi": 448},
            "delta_multi": scan["multi_n"] - 1,
            "delta_nonempty": scan["nonempty_n"] - 23,
        },
        "live": live,
        "vt_refs_catalog": {
            "INST_VT": "0x2A02558",
            "CP_VT": "0x29EE248",
            "note": "catalog only this slice; Instant not probed on path OIs",
        },
    }
    (ROOT / "reports/phase2ijf_path200_og50_track.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    keys = (
        "phase",
        "slice",
        "result",
        "allow_post",
        "note",
        "instant_parked",
        "path_army_n",
        "nonempty_n",
        "multi_n",
        "by_class",
        "by_prov_head",
        "army_to_ois",
        "new_dests",
        "new_ois",
        "multi_rows",
        "companion_path_mem",
        "focus_og50",
        "hub481_oneshot",
        "vs_2ije",
        "reverse",
        "live",
        "path_rows",
        "vt_refs_catalog",
    )
    brief = {k: out[k] for k in keys}
    (ROOT / "reports/phase2ijf_path200_og50_track_summary.json").write_text(
        json.dumps(brief, indent=2, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": result,
                "calendar_ok": calendar_ok,
                "by_class": dict(by_class),
                "nonempty_n": scan["nonempty_n"],
                "multi_n": scan["multi_n"],
                "new_dests": new_dests[:32],
                "new_ois": new_ois[:32],
                "multi_rows": multi,
                "focus_og50_sizes": {
                    str(oi): (focus_og.get(str(oi)) or {}).get("og50_size")
                    for oi in FOCUS_OIS
                },
                "hub481_keys": list(hub481.keys())[:12] if isinstance(hub481, dict) else type(hub481).__name__,
                "live": live,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
