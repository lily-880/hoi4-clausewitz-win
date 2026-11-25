"""Derived views for the commander, built only from proven readings.

- unit_kind(): division type from its template battalions (armor, motorized,
  infantry, ...). Battalion types are live template readings.
- border_sections(): our border split by the enemy it faces, each with the
  divisions standing there. Sections facing an enemy that is not a primary
  offensive target and lying in the home land region form the home defense
  line ("德国本土不能被占领", user 2026-11-24).
- combat_view(): per combat, both sides' average organization and strength,
  with a trend against the previous tick (derived, labelled as such; it is
  not an engine field).
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MEMORY = HERE.parent / "research" / "claude_live" / "combat_memory.json"

# Scenario parameters live in tables/scenario.json (one file per campaign, the
# commander prompt stays generic); environment variables still override.
try:
    SCENARIO = json.loads((HERE / "tables" / "scenario.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    SCENARIO = {}
# Staff default (the commander may decide otherwise): the enemy we attack.
PRIMARY_TARGETS = set(filter(None, os.environ.get(
    "COMMANDER_PRIMARY_TARGETS", ",".join(SCENARIO.get("primary_targets", []))).split(",")))
# Minimum divisions per home-defense border province.
DEFENSE_MIN = int(os.environ.get("COMMANDER_DEFENSE_MIN", str(SCENARIO.get("defense_min_per_province", 2))))
# Countries not at war yet whose border is still defended (likely to declare).
THREATS = set(filter(None, os.environ.get(
    "COMMANDER_THREATS", ",".join(SCENARIO.get("threats", []))).split(",")))

ARMOR = {"light_armor", "medium_armor", "heavy_armor", "modern_armor",
         "amphibious_armor", "super_heavy_armor"}
MOBILE = {"motorized", "mechanized", "amphibious_mechanized", "motorized_rocket_brigade"}
SPECIAL = {"mountaineers": "mountain", "paratrooper": "paratrooper", "marine": "marine",
           "cavalry": "cavalry", "camelry": "cavalry"}

# Base combat width (1.11+ values) and per extra attack direction.
TERRAIN_WIDTH = {"plains": (70, 35), "desert": (75, 25), "forest": (60, 30), "hills": (80, 40),
                 "mountain": (75, 25), "marsh": (50, 25), "jungle": (72, 36), "urban": (96, 32)}
# Rough attacker difficulty used to rank targets (lower = easier).
TERRAIN_PENALTY = {"plains": 0, "desert": 0, "forest": 1, "hills": 2, "jungle": 2,
                   "urban": 3, "marsh": 3, "mountain": 4}


def unit_kind(u: dict) -> str:
    bats = Counter()
    for b in ((u.get("template") or {}).get("battalions") or []):
        bats[b.get("type")] += b.get("count", 1)
    if not bats:
        return "unknown"
    if any(t in ARMOR for t in bats):
        return "armor"
    if any(t in MOBILE for t in bats):
        return "motorized"
    top = bats.most_common(1)[0][0]
    return SPECIAL.get(top, "infantry" if top == "infantry" else top or "unknown")


def width(u: dict) -> float:
    w = (u.get("template") or {}).get("combat_width")
    return float(w) if isinstance(w, (int, float)) and w > 0 else 20.0


def _region(ext: dict, pid):
    reg = ((ext.get("topology") or {}).get("region_of_province") or {})
    return reg.get(pid, reg.get(str(pid)))


def home_region(ext: dict):
    regs = (ext.get("topology") or {}).get("regions") or []
    return max(regs, key=lambda r: r.get("provinces", 0))["region"] if regs else None


def border_sections(doc: dict, primary: set[str] | None = None) -> list[dict]:
    primary = PRIMARY_TARGETS if primary is None else primary
    ext = doc.get("_ext") or {}
    ctrl = {e["province_id"]: (e.get("controller") or {}).get("tag") for e in ext.get("enemy_border", [])}
    present = Counter()
    incoming = Counter()
    for u in (doc.get("world") or {}).get("own_units", []):
        route = (u.get("order") or {}).get("path_province_ids") or []
        if route:
            incoming[route[-1]] += 1
        else:
            present[u.get("province_id")] += 1
    home = home_region(ext)
    sections: dict[tuple, dict] = {}
    for b in ext.get("own_border", []):
        for tag in sorted({ctrl.get(n) for n in b.get("enemy_neighbors", [])} - {None}):
            reg = _region(ext, b["province_id"])
            key = (tag, reg)
            s = sections.setdefault(key, {"enemy": tag, "region": reg, "provinces": []})
            s["provinces"].append(b["province_id"])
    # borders with countries not (yet) at war: likely enemies (France before it
    # declares) are defended too; plain neutrals need no garrison.
    at_war_border = {b["province_id"] for b in ext.get("own_border", [])}
    for pid, tags in (ext.get("own_watch_facing") or {}).items():
        pid = int(pid)
        if pid in at_war_border:
            continue
        for tag in tags:
            reg = _region(ext, pid)
            key = (tag + ("(未宣战)" if tag in THREATS else "(中立)"), reg)
            sections.setdefault(key, {"enemy": key[0], "region": reg, "provinces": []})["provinces"].append(pid)
    out = []
    for (tag, reg), s in sorted(sections.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        provs = sorted(set(s["provinces"]))
        if tag.endswith("(中立)"):
            out.append({"enemy": tag, "region": reg, "role": "neutral_no_garrison_needed",
                        "provinces": [{"prov": p, "divisions": present[p]} for p in provs if present[p]],
                        "divisions": sum(present[p] for p in provs)})
            continue
        defense = tag.split("(")[0] not in primary and reg == home
        row = {"enemy": tag, "region": reg, "role": "home_defense" if defense else "offensive",
               "provinces": [{"prov": p, "divisions": present[p], "incoming": incoming[p]} for p in provs],
               "divisions": sum(present[p] for p in provs),
               "empty_provinces": [p for p in provs if present[p] == 0]}
        if defense:
            row["min_per_province"] = DEFENSE_MIN
            row["short_provinces"] = [p for p in provs if present[p] + incoming[p] < DEFENSE_MIN]
        out.append(row)
    return out


def defense_provinces(doc: dict) -> set[int]:
    return {p["prov"] for s in border_sections(doc) if s["role"] == "home_defense" for p in s["provinces"]}


def combat_view(doc: dict, remember: bool = False) -> list[dict]:
    world = doc.get("world") or {}
    units = {u["unit_id"]: u for u in world.get("own_units", [])}
    units.update({v["unit_id"]: v for v in world.get("visible_units", [])})
    own_ids = {u["unit_id"] for u in world.get("own_units", [])}
    try:
        prev = json.loads(MEMORY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prev = {}
    now_key = json.dumps((doc.get("meta") or {}).get("game_time"), sort_keys=True)
    out, mem = [], {}

    def side(ids):
        rows = [units[i] for i in ids if i in units]
        if not rows:
            return None
        org = sum(r.get("organization") or 0 for r in rows) / len(rows)
        hp = sum((r.get("strength") or {}).get("current") or 0 for r in rows)
        return {"n": len(ids), "seen": len(rows), "avg_org": round(org, 1), "hp": round(hp, 1)}

    for c in world.get("combats", []):
        att, dfn = c.get("attacker_unit_ids") or [], c.get("defender_unit_ids") or []
        we_attack = bool(set(att) & own_ids)
        ours, theirs = (att, dfn) if we_attack else (dfn, att)
        o, t = side(ours), side(theirs)
        row = {"id": c["combat_id"], "prov": c.get("province_id"), "we_attack": we_attack,
               "ours": o, "enemy": t}
        if o and t:
            key = str(c["combat_id"]) + "@" + str(c.get("province_id"))
            mem[key] = {"t": now_key, "our_org": o["avg_org"], "enemy_org": t["avg_org"]}
            p = prev.get(key)
            if p and p.get("t") != now_key:
                d_our = o["avg_org"] - p["our_org"]
                d_en = t["avg_org"] - p["enemy_org"]
                row["org_change_since_last_tick"] = {"ours": round(d_our, 1), "enemy": round(d_en, 1)}
                row["trend"] = ("winning" if d_en < d_our - 3 else "losing" if d_our < d_en - 3 else "even")
            elif t["avg_org"] < o["avg_org"] * 0.6:
                row["trend"] = "winning"
            elif o["avg_org"] < t["avg_org"] * 0.6:
                row["trend"] = "losing"
        cas = c.get("casualties") or {}
        if cas:
            row["org_damage_total"] = {"ours": cas.get("our_org_loss"), "enemy": cas.get("enemy_org_loss")}
        out.append(row)
    if remember:
        try:
            MEMORY.parent.mkdir(parents=True, exist_ok=True)
            MEMORY.write_text(json.dumps(mem), encoding="utf-8")
        except OSError:
            pass
    return out
