#!/usr/bin/env python3
"""Phase 2iv relaunch: PATH200 + OG50 reverse after fresh ITA launch. NON-Post only."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import importlib.util
from calling.process import Backend, find_pid
from calling.clock import ui_date

def load_iu():
    spec = importlib.util.spec_from_file_location("p2iu", ROOT / "scripts/phase2iu_path200_focus740_og50.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def main() -> int:
    p = load_iu()
    pid = find_pid()
    if not pid:
        print("NO_PID"); return 2
    b = Backend(pid); base = b.image_base; tag = p.player_tag(b, base) or 15
    meta = p.live_meta(b, base, pid, tag)
    year = int(meta.get("year_at_0x478") or 0)
    day_index = int(meta.get("hours") or 0)
    dig = list(p.DIG_FOCUS_SEED)
    scan = p.scan_path_armies(b, base, tag, dig_focus=dig)
    army_to_ois, rev_meta = p.reverse_og50(b, base, scan["path_rows"])
    rows = []
    for r in scan["path_rows"]:
        ois = sorted(army_to_ois.get(r["index"], []))
        focus = r.get("focus_hit") or []
        rows.append({
            "index": r["index"], "path_ids": r["path_ids"], "path_n": r["path_n"],
            "focus_hit": focus, "ois": ois, "kinds": p.classify_ois(ois),
            "class": "focus_hit" if focus else "path_only", "row_kind": "path_only",
        })
    focus_hits = [h for h in rows if h["focus_hit"]]
    result = "PATH200_RELAUNCH_FOCUS740_HIT" if focus_hits else ("PATH200_RELAUNCH_PATH_ONLY_HIT" if rows else "PATH200_RELAUNCH_EMPTY")
    live = {
        "pid": pid, "tag": tag, "year_at_0x478": year, "day_index_at_0x484": day_index,
        "ui_date_corrected": ui_date(year, day_index), "clock_class": "RELOAD_OR_NEW_CAMPAIGN",
        "drain": meta.get("drain"), "exec": meta.get("exec"), "allow_post": False,
        "speed": "1x_cli_start_untouched_mem",
    }
    out = {
        "phase": "2iv", "slice": "relaunch_path200_after_reconcile", "result": result,
        "allow_post": False, "dig_focus": dig, "ita_ok": scan["ita_ok"], "empty_n": scan["empty_n"],
        "nonempty_n": scan["nonempty_n"], "multi_n": scan["multi_n"], "path_army_n": len(rows),
        "focus_hit_n": len(focus_hits), "by_prov_head": scan["by_prov_head"],
        "by_class": {"path_only": len(rows), "focus_hit": len(focus_hits)},
        "path_rows": rows, "reverse": rev_meta,
        "army_to_ois": {str(k): v for k, v in army_to_ois.items()}, "live": live,
    }
    (ROOT / "reports/phase2iv_relaunch_path200.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    (ROOT / "reports/phase2iv_relaunch_summary.json").write_text(json.dumps({k: out[k] for k in ("phase","slice","result","allow_post","path_army_n","nonempty_n","focus_hit_n","army_to_ois","live","path_rows","by_prov_head","reverse")}, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"result": result, "path_army_n": len(rows), "army_to_ois": out["army_to_ois"], "live": live}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
