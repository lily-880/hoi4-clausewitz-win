#!/usr/bin/env python3
"""Read-only recorder for a human demonstration (user 2026-11-26: "I can make Poland surrender
within 30 days myself; watch how I do it").

While the user plays, every RECORD_HOURS of game time it writes one JSON line with:
  game clock; armies, army groups, fronts, offensive lines and whether they execute; every own
  division (province, order target/path, organisation, in combat); combats (sides, province);
  air wings (type, mission, attached army); Poland's (= the scenario's primary targets')
  surrender progress and province counts.
and every SHOT_HOURS a screenshot of the game window only (PrintWindow, never the screen).

It posts no command and no key, never touches the foreground, and works at any game speed
(a capture that is inconsistent because the clock moved is retried, then reduced to the plans).

  python -I scripts/demo_recorder.py            # until the game closes or STOP_DEMO appears
Output: research/claude_live/demo/<start time>/record.jsonl and shot_<date>.png
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "calling"), str(ROOT / "scripts")]

RECORD_HOURS = 6
SHOT_HOURS = 24
POLL_S = 2.0
OUT = ROOT / "research" / "claude_live" / "demo" / (sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S"))
STOP = ROOT / "research" / "claude_live" / "demo" / "STOP_DEMO"


def clock():
    import live_trial as lt
    return lt.Session(check_sha=False).clock()


def plans() -> dict:
    import orbat
    snap = orbat.snapshot()
    out = []
    for th in snap["theatres"]:
        for a in th["armies"]:
            out.append({"army_id": a["id"], "name": a["name"], "army_group_id": a.get("army_group_id"),
                        "leader_id": a.get("leader_id"),
                        "divisions": len(a["unit_ids"]), "unit_ids": a["unit_ids"],
                        "plans": [{"plan_id": p["plan_id"], "front": p["path"], "executing": p.get("can_execute"),
                                   "sub_executing": p.get("sub_executing"),
                                   "lines": [c["path"] for c in p["children"]]} for p in a["plans"]]})
        for g in th.get("army_groups", []):
            out.append({"army_group_id": g["id"], "name": g["name"], "army_ids": g.get("army_ids"),
                        "leader_id": g.get("leader_id"),
                        "plans": [{"plan_id": p["plan_id"], "front": p["path"], "executing": p.get("can_execute"),
                                   "sub_executing": p.get("sub_executing"),
                                   "lines": [c["path"] for c in p["children"]]} for p in g.get("plans", [])]})
    return {"armies": out}


def full() -> dict:
    import live_input
    r = live_input.capture()
    w = r["observation"]["world"]
    ext = r.get("commander_ext") or {}
    units = [{"id": u["unit_id"], "prov": u.get("province_id"), "org": round(u.get("organization") or 0),
              "army": (u.get("formation") or {}).get("army_id"),
              "order": (u.get("order") or {}).get("target_province_ids") or (u.get("order") or {}).get("path_province_ids"),
              "combat": u.get("combat_id") if u.get("in_combat") else None} for u in w.get("own_units", [])]
    combats = [{"id": c["combat_id"], "prov": c["province_id"], "att": len(c.get("attacker_unit_ids") or []),
                "def": len(c.get("defender_unit_ids") or []),
                "we_attack": bool(set(c.get("attacker_unit_ids") or []) & {u["id"] for u in units})}
               for c in w.get("combats", [])]
    import commander_view as cv
    prim = set(cv.PRIMARY_TARGETS)
    return {"units": units, "combats": combats,
            "surrender": {k: v for k, v in (ext.get("surrender") or {}).items() if k in prim},
            "enemy_provinces": {k: v for k, v in (ext.get("enemy_controlled_provinces") or {}).items() if k in prim}}


def light_units(unit_ids: list[int]) -> list:
    """Per-division position and route read directly, with no consistency checks: the full
    capture needs a still game and failed on every running record of the first demo."""
    import live_trial as lt
    s = lt.Session(check_sha=False)
    out = []
    for uid in unit_ids:
        try:
            u = s.unit(uid)
        except (Exception, SystemExit):
            u = None
        if u:
            out.append({"id": uid, "prov": u["province_id"], "path": u["path"],
                        "cmds": u["commandlist_size"], "retreat": u["retreat"]})
    return out


def air() -> list:
    try:
        import air_orders as ao
        return ao.own_wings(max_id=1500)
    except (Exception, SystemExit) as e:
        return [{"error": type(e).__name__}]


def traits() -> dict:
    """Every leader's traits (pure memory reads; the demo-1 traits had to be found afterwards)."""
    try:
        import leader_traits as ltr
        return {str(k): v for k, v in ltr.leader_traits().items()}
    except (Exception, SystemExit) as e:
        return {"error": type(e).__name__}


def shot(tag: str) -> str | None:
    try:
        import game_ui as gu
        return str(gu.shot(OUT / f"shot_{tag}.png", 0.6))
    except (Exception, SystemExit):
        return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if STOP.exists():
        STOP.unlink()
    last_rec = last_shot = None
    misses = 0
    known_ids: set[int] = set()
    print("recording to", OUT, flush=True)
    while not STOP.exists():
        try:
            c = clock()
            misses = 0
        except (Exception, SystemExit):
            # game closed, restarting or loading a save: wait up to an hour for it
            misses += 1
            if misses > 360:
                break
            time.sleep(10)
            continue
        h = c.get("hour_tick")
        if h is None:
            time.sleep(POLL_S)
            continue
        if last_rec is not None and h < last_rec:  # a save was (re)loaded
            last_rec = last_shot = None
        if last_rec is None or h - last_rec >= RECORD_HOURS:
            row = {"at": datetime.now().isoformat(timespec="seconds"), "game": f"{c.get('ui_date')} {c.get('ui_hour')}h",
                   "speed_slot": c.get("speed_slot"), "pause": c.get("pause")}
            try:
                row.update(plans())
            except (Exception, SystemExit) as e:
                row["plans_error"] = type(e).__name__
            for _ in range(3):
                try:
                    row.update(full())
                    break
                except (Exception, SystemExit) as e:
                    row["capture_error"] = f"{type(e).__name__}: {e}"[:120]
                    time.sleep(0.3)
            if "units" in row:
                known_ids.update(u["id"] for u in row["units"])
            else:  # the full capture failed: keep at least each division's route
                ids = sorted(known_ids | {u for a in row.get("armies", []) for u in a.get("unit_ids", [])})
                try:
                    row["units_light"] = light_units(ids)
                except (Exception, SystemExit) as e:
                    row["units_light_error"] = type(e).__name__
            row["air"] = air()
            row["traits"] = traits()
            with (OUT / "record.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            last_rec = h
            print(row["game"], "surrender", row.get("surrender"), flush=True)
        if last_shot is None or h - last_shot >= SHOT_HOURS:
            shot(str(c.get("ui_date")).replace("-", "") + f"_{c.get('ui_hour')}")
            last_shot = h
        time.sleep(POLL_S)
    print("stopped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
