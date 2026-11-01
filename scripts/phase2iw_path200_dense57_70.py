#!/usr/bin/env python3
"""Phase 2iw NON-Post: denser PATH200 / OG50 on oi=57/70. Does NOT call Post inject."""
from __future__ import annotations
import json, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import importlib.util
from calling.process import Backend, find_pid
from calling.config import allow_post
from calling.clock import ui_date
from calling.handle import resolve_handle

FOCUS_OIS = (57, 70)
SEED_PROVS = (9945, 12857)

def load_iu():
    spec = importlib.util.spec_from_file_location("p2iu", ROOT / "scripts/phase2iu_path200_focus740_og50.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def dig_oi(p, b, base, oi, path_rows):
    out = {"oi": oi, "inst_ok": False, "og50_size": 0, "arr70_n": 0, "arr88_ids": [], "path_mem": [],
           "triangle70": [], "in70_not_88": [], "in70_and_88": [], "cross88_path": []}
    try:
        hdr = resolve_handle(b, p.TYPE_OG, oi, base)
    except Exception as e:
        out["err"] = type(e).__name__; return out
    if not hdr:
        out["err"] = "no_hdr"; return out
    og = hdr + 0x10
    arr50 = p.read_cpdx_ptrs(b, base, og + 0x50, 64) or {}
    ptrs = arr50.get("ptrs") or []
    out["og50_size"] = len(ptrs)
    want = {}
    for r in path_rows:
        want[r["army"]] = r["index"]; want[r["army"] + p.CA_MI_OFF] = r["index"]
    for ptr in ptrs:
        if not ptr: continue
        idx = want.get(ptr) or want.get(ptr - p.CA_MI_OFF)
        if idx is not None:
            out["path_mem"].append({"index": idx, "path_ids": next((r["path_ids"] for r in path_rows if r["index"] == idx), [])})
    # Single Instant VT check only — no Instant-map / empty re-poll
    try:
        if hasattr(p, "TYPE_INST"):
            ih = resolve_handle(b, p.TYPE_INST, oi, base)
            if ih:
                inst = ih + 0x10
                vt = p.try_u64(b, inst)
                out["inst_ok"] = bool(vt and ((vt - base) & 0xFFFFFFFF) == p.INST_VT)
                if out["inst_ok"]:
                    a70 = p.read_cpdx_u32(b, base, inst + 0x70, 64) or {}
                    a88 = p.read_cpdx_ptrs(b, base, inst + 0x88, 48) or {}
                    u70 = a70.get("u32s") or a70.get("ids") or []
                    out["arr70_n"] = len(u70)
                    ids88 = []
                    for cp in (a88.get("ptrs") or [])[:48]:
                        if not cp: continue
                        cvt = p.try_u64(b, cp)
                        if cvt and ((cvt - base) & 0xFFFFFFFF) == p.CP_VT:
                            pid_ = p.try_u32(b, cp + 0xA4)
                            if pid_ and p.looks_like_province(pid_):
                                ids88.append(pid_)
                    out["arr88_ids"] = ids88
                    path_union = set(x for r in path_rows for x in r["path_ids"])
                    in70 = set(u70) & path_union; in88 = set(ids88) & path_union
                    out["triangle70"] = sorted(in70)
                    out["in70_and_88"] = sorted(in70 & in88)
                    out["in70_not_88"] = sorted(in70 - in88)
                    out["cross88_path"] = sorted(in88)
    except Exception as e:
        out["inst_exc"] = type(e).__name__
    return out

def main() -> int:
    assert allow_post() is False
    p = load_iu(); pid = find_pid(); assert pid
    b = Backend(pid); base = b.image_base; tag = p.player_tag(b, base) or 15
    meta = p.live_meta(b, base, pid, tag)
    year = int(meta.get("year_at_0x478") or 0); day = int(meta.get("hours") or 0)
    dig = list(dict.fromkeys(list(SEED_PROVS) + list(p.DIG_FOCUS_SEED)))
    scan = p.scan_path_armies(b, base, tag, dig_focus=dig)
    army_to_ois, rev_meta = p.reverse_og50(b, base, scan["path_rows"])
    oi_digs = {str(oi): dig_oi(p, b, base, oi, scan["path_rows"]) for oi in FOCUS_OIS}
    rows = []
    for r in scan["path_rows"]:
        ois = sorted(army_to_ois.get(r["index"], []))
        seed_hit = sorted(set(r["path_ids"]) & set(SEED_PROVS))
        dig_hit = sorted(set(r["path_ids"]) & set(dig))
        focus_oi_hit = sorted(set(ois) & set(FOCUS_OIS))
        cls = "path_only"; tri = []
        for oi in ois:
            d = oi_digs.get(str(oi)) or {}
            inter = sorted(set(r["path_ids"]) & set(d.get("triangle70") or []))
            if inter:
                cls = "tri70"; tri = inter; break
        if focus_oi_hit and seed_hit and cls == "path_only":
            cls = "focus_oi_seed"
        rows.append({"index": r["index"], "path_ids": r["path_ids"], "path_n": r["path_n"], "dig_hit": dig_hit,
                     "seed_hit": seed_hit, "ois": ois, "focus_ois": focus_oi_hit, "kinds": p.classify_ois(ois),
                     "class": cls, "tri70_path": tri})
    companion = [{"oi": oi, **pm} for oi in FOCUS_OIS for pm in (oi_digs[str(oi)].get("path_mem") or [])]
    by_class = defaultdict(int)
    for r in rows: by_class[r["class"]] += 1
    focus_rows = [r for r in rows if r["seed_hit"] or r["focus_ois"] or r["dig_hit"]]
    multi = [r for r in rows if r["path_n"] > 1]
    result = "PATH200_OI57_70_TRI70_HIT" if any(r["class"] == "tri70" for r in rows) else (
        "PATH200_OI57_70_DENSE_HIT" if (multi or len(focus_rows) >= 2 or any(len(oi_digs[str(oi)].get("path_mem") or []) > 1 for oi in FOCUS_OIS)) else (
        "PATH200_OI57_70_PATH_ONLY" if rows else "PATH200_OI57_70_EMPTY"))
    live = {"pid": pid, "tag": tag, "year_at_0x478": year, "day_index_at_0x484": day,
            "ui_date_corrected": ui_date(year, day),
            "clock_class": "RELOAD_OR_NEW_CAMPAIGN" if year == 1936 and day < 48 else "CONTINUOUS",
            "drain": meta.get("drain"), "exec": meta.get("exec"), "allow_post": False, "speed": "1x_cli_untouched_mem"}
    out = {"phase": "2iw", "slice": "path200_dense_oi57_70_NONPOST", "result": result, "allow_post": False,
           "note": "NON-Post denser PATH200; historical Post scripts NOT re-run",
           "focus_ois": list(FOCUS_OIS), "seed_provs": list(SEED_PROVS), "dig_focus": dig,
           "ita_ok": scan["ita_ok"], "empty_n": scan["empty_n"], "nonempty_n": scan["nonempty_n"], "multi_n": scan["multi_n"],
           "path_army_n": len(rows), "focus_row_n": len(focus_rows), "by_class": dict(by_class),
           "by_prov_head": scan["by_prov_head"], "path_rows": rows, "companion_path_mem": companion,
           "oi_digs": oi_digs, "reverse": rev_meta, "army_to_ois": {str(k): v for k, v in army_to_ois.items()},
           "arr88_xpath": {"in70_and_88": sorted({x for oi in FOCUS_OIS for x in (oi_digs[str(oi)].get("in70_and_88") or [])}),
                           "in70_not_88": sorted({x for oi in FOCUS_OIS for x in (oi_digs[str(oi)].get("in70_not_88") or [])}),
                           "cross70": sorted({x for oi in FOCUS_OIS for x in (oi_digs[str(oi)].get("triangle70") or [])}),
                           "cross88": sorted({x for oi in FOCUS_OIS for x in (oi_digs[str(oi)].get("cross88_path") or [])})},
           "live": live}
    (ROOT / "reports/phase2iw_path200_dense57_70.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    brief = {k: out[k] for k in ("phase","slice","result","allow_post","note","focus_ois","path_army_n","nonempty_n","multi_n","focus_row_n","by_class","by_prov_head","army_to_ois","companion_path_mem","arr88_xpath","reverse","live","path_rows")}
    (ROOT / "reports/phase2iw_path200_dense57_70_summary.json").write_text(json.dumps(brief, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"result": result, "by_class": dict(by_class), "army_to_ois": out["army_to_ois"], "live": live}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
