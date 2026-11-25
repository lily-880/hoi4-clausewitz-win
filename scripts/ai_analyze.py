#!/usr/bin/env python3
"""Read-only analysis of how the game AI uses Germany's army right now:
per army group / army: divisions, armour share, where its plans run (which
enemy they face), how deep the offensive lines go and whether they reach
victory-point provinces.

  python -I -X utf8 scripts/ai_analyze.py [--cap research/claude_live/ai_bench/cap_now.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))

ARMOUR = {"light_armor", "medium_armor", "heavy_armor", "modern_armor", "motorized", "mechanized",
          "light_tank_destroyer_brigade", "medium_tank_destroyer_brigade"}


def flat(plans, d=0):
    for p in plans:
        yield d, p
        yield from flat(p.get("children", []), d + 1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=Path, default=ROOT / "research/claude_live/ai_bench/cap_now.json")
    a = ap.parse_args(argv)
    import live_trial as lt
    import orbat
    c = json.loads(a.cap.read_text(encoding="utf-8"))
    w, ext = c["observation"]["world"], c["commander_ext"]
    gt = c["observation"]["meta"]["game_time"]
    prov = {p["province_id"]: p for p in w["provinces"]}
    tag = {1: "GER"}
    for b in ext.get("enemy_border", []):
        tag[b["controller"]["index"]] = b["controller"]["tag"]
    for u in w.get("visible_units", []):
        o = u.get("owner") or {}
        if o.get("tag"):
            tag[o["index"]] = o["tag"]

    S = lt.Session(check_sha=False)
    _tags = {}

    def ctl(pid):
        i = ((prov.get(pid) or {}).get("controller") or {}).get("index")
        if i is None:
            i = S.controller_of(pid)  # the capture only lists provinces near our own land
        if i is None:
            return "?"
        if i not in _tags:
            _tags[i] = tag.get(i) or S.tag(i) or str(i)
        return _tags[i]

    units = {u["unit_id"]: u for u in w["own_units"]}
    snap = orbat.snapshot(lt.Session(check_sha=False))
    lead = {l["leader_id"]: l for l in snap["leaders"]}
    print(f"== {gt['year']}-{gt['month']:02d}-{gt['day']:02d} {gt['hour']}h  divisions {len(units)}  "
          f"enemy provinces {ext.get('enemy_controlled_provinces')}")
    kt = [k for k in ext["topology"]["key_targets"] if k["owner"] == "POL"]
    print("POL VP targets:", [(k["province_id"], k["victory_points"], k["hops_from_our_land"]) for k in kt[:10]])

    def describe(g, kind):
        ld = lead.get(g["leader_id"]) or {}
        uids = g["unit_ids"]
        if kind == "AG":
            uids = [x for t in snap["theatres"] for ar in t["armies"] if ar["id"] in (g.get("army_ids") or [])
                    for x in ar["unit_ids"]]
        arm = sum(1 for x in uids if units.get(x) and any(b["type"] in ARMOUR for b in units[x]["template"]["battalions"]))
        combat = sum(1 for x in uids if units.get(x) and units[x].get("in_combat"))
        where = Counter()
        for x in uids:
            u = units.get(x)
            if u:
                for n in prov.get(u["province_id"], {}).get("neighbors", []):
                    if ctl(n) not in ("GER", "?"):
                        where[ctl(n)] += 1
        print(f"{kind} {g['id']} {g['name']!r} leader={ld.get('key')}({ld.get('rank')}) div={len(uids)} "
              f"armour/mot={arm} in_combat={combat} touching={dict(where)}"
              + (f" armies={g.get('army_ids')}" if kind == "AG" else f" AG={g.get('army_group_id')}"))
        for d, p in flat(g["plans"]):
            path = p["path"]
            sides = Counter(ctl(x) for x in path)
            vps = [(x, prov[x]["victory_points"]["value"]) for x in path
                   if x in prov and (prov[x].get("victory_points") or {}).get("value")]
            print(f"   {'  ' * d}plan type={p['type']} members={p['members']} exec={p['can_execute']} "
                  f"len={len(path)} controllers={dict(sides)} vp_on_path={vps[:6]} ends={path[:1] + path[-1:]}")

    for t in snap["theatres"]:
        for g in t["army_groups"]:
            describe(g, "AG")
        for g in t["armies"]:
            describe(g, "A")
    return 0


if __name__ == "__main__":
    sys.exit(main())
