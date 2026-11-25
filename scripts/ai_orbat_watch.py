#!/usr/bin/env python3
"""Read-only: record how the game's own AI organises Germany's army while
ai_benchmark.py runs (armies, army groups, leaders, front / offensive-line plans).

  python -I scripts/ai_orbat_watch.py --every 120 --count 60

Appends one line per sample to research/claude_live/ai_bench/orbat.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))
OUT = ROOT / "research" / "claude_live" / "ai_bench" / "orbat.jsonl"


def _plans(plans):
    """Flatten a plan tree into (class, path length, members, depth)."""
    out = []

    def walk(p, d):
        out.append({"cls": p["class"].replace(".?AV", "").replace("@@", ""), "type": p["type"],
                    "path_len": len(p["path"]), "path_ends": [p["path"][0], p["path"][-1]] if p["path"] else [],
                    "members": p["members"], "depth": d, "exec": p["can_execute"]})
        for c in p.get("children", []):
            walk(c, d + 1)
    for p in plans:
        walk(p, 0)
    return out


def sample() -> dict:
    import live_trial as lt
    import orbat
    s = lt.Session(check_sha=False)
    clk = s.clock()
    snap = orbat.snapshot(s)
    lead = {l["leader_id"]: l for l in snap["leaders"]}
    armies, groups = [], []
    for t in snap["theatres"]:
        for a in t["armies"]:
            ld = lead.get(a["leader_id"]) or {}
            armies.append({"theatre": t["name"], "id": a["id"], "name": a["name"], "divisions": len(a["unit_ids"]),
                           "leader": ld.get("key"), "rank": ld.get("rank"), "army_group": a.get("army_group_id"),
                           "plans": _plans(a["plans"])})
        for g in t["army_groups"]:
            ld = lead.get(g["leader_id"]) or {}
            groups.append({"theatre": t["name"], "id": g["id"], "name": g["name"], "armies": g.get("army_ids"),
                           "leader": ld.get("key"), "rank": ld.get("rank"), "plans": _plans(g["plans"])})
    return {"at": datetime.now().isoformat(timespec="seconds"), "game": f"{clk['ui_date']} {clk['ui_hour']}h",
            "theatres": [{"name": t["name"], "units": len(t["unit_ids"])} for t in snap["theatres"]],
            "armies": armies, "army_groups": groups,
            "plan_kinds": dict(Counter(p["cls"] for a in armies for p in a["plans"]))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=float, default=120)
    ap.add_argument("--count", type=int, default=1)
    a = ap.parse_args(argv)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for i in range(a.count):
        try:
            row = sample()
        except Exception as e:
            row = {"at": datetime.now().isoformat(timespec="seconds"), "error": f"{type(e).__name__}: {e}"[:300]}
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if a.count == 1:
            print(json.dumps(row, ensure_ascii=False, indent=1))
        if i + 1 < a.count:
            time.sleep(a.every)
    return 0


if __name__ == "__main__":
    sys.exit(main())
