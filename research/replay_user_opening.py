"""Diagnostic, not product (2026-11-27): rebuild the user's 27-day opening deployment on the
war-start save through the commander's own commands, then let the game run with no further
intervention. Question: is "the right opening + leave it alone" enough for ~30 days?

  python -I research/replay_user_opening.py deploy     # on CC_GER_1939_08_14_base, paused
  python -I research/replay_user_opening.py run DAYS   # advance, log progress every 24 h

Source: research/claude_live/demo/20261127_005423/deployment_before_start.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "calling"), str(ROOT / "scripts")]
os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"

import orbat  # noqa: E402
import plan_orders as po  # noqa: E402
import air_orders as ao  # noqa: E402
import leader_traits as ltr  # noqa: E402
import live_trial as lt  # noqa: E402

DEMO = ROOT / "research" / "claude_live" / "demo" / "20261127_005423" / "deployment_before_start.json"
LOG = ROOT / "research" / "claude_live" / "runs" / "replay_user_opening.jsonl"
TRAITS = {339: ["offensive_doctrine", "aggressive_assaulter", "inspirational_leader"], 338: ["fortress_buster"]}


def armies_now():
    return {a["id"]: a for th in orbat.snapshot()["theatres"] for a in th["armies"]}


def groups_now():
    return {g["id"]: g for th in orbat.snapshot()["theatres"] for g in th["army_groups"]}


def deploy():
    d = json.loads(DEMO.read_text(encoding="utf-8"))
    th = orbat.snapshot()["theatres"][0]["id"]
    user_armies = [a for a in d["armies"] if "army_id" in a]
    user_groups = [a for a in d["armies"] if "army_id" not in a]
    # field marshals first (the user's two army-group commanders were generals at the start)
    for g in user_groups:
        print("promote", g["leader_id"], orbat.promote(g["leader_id"]).get("ok"))
    new_id = {}
    for a in user_armies:
        before = set(armies_now())
        r = orbat.create_army(th, a["unit_ids"])
        time.sleep(0.5)
        nid = (set(armies_now()) - before or {None}).pop()
        new_id[a["army_id"]] = nid
        print("army", a["name"], len(a["unit_ids"]), "->", nid, r.get("ok"),
              "leader", orbat.appoint(a["leader_id"], nid).get("ok") if nid else None)
    gid = {}
    for g in user_groups:
        before = set(groups_now())
        r = orbat.create_army_group(th, [new_id[x] for x in g["army_ids"]])
        time.sleep(0.5)
        ng = (set(groups_now()) - before or {None}).pop()
        gid[g["army_group_id"]] = ng
        print("group", g["name"], "->", ng, r.get("ok"), "leader", orbat.appoint(g["leader_id"], ng).get("ok") if ng else None)
    s = lt.Session(check_sha=False)
    units = {a["id"]: a["unit_ids"] for a in armies_now().values()}

    def group_units(g):
        return [u for x in groups_now()[g]["army_ids"] for u in units.get(x, [])]
    # main army group: front along our whole stretch of the Polish border, one line to the target
    main_user = next(g for g in user_groups if g.get("plans") and g["plans"][0]["lines"] and g["plans"][0]["lines"][0] == [560])
    mg = gid[main_user["army_group_id"]]
    print("main front", po.place_front(s, mg, "POL", None, None, group_units(mg), True).get("ok"))
    root = next(p for p in groups_now()[mg]["plans"] if p["path"])
    print("main line", orbat.offensive_line(mg, root["plan_id"], [560], group_units(mg), True).get("ok"))
    # the army with its own plan (East Prussia): front where its divisions stand, same target
    for a in user_armies:
        if a["plans"]:
            nid = new_id[a["army_id"]]
            print("army front", a["name"], po.place_front(s, nid, "POL", "near_units", None, units[nid], True).get("ok"))
            r_ = next(p for p in armies_now()[nid]["plans"] if p["path"])
            print("army line", orbat.offensive_line(nid, r_["plan_id"], a["plans"][0]["lines"][0], units[nid], True).get("ok"))
    # the western army group: front facing France, not executed
    for g in user_groups:
        if g["army_group_id"] != main_user["army_group_id"]:
            ng = gid[g["army_group_id"]]
            print("west front", po.place_front(s, ng, "FRA", None, None, group_units(ng), True).get("ok"))
    # air: every wing the user used, on the same army, mission by type
    used = [w for w in d["air"] if w.get("army_id")]
    target_army = new_id[used[0]["army_id"]]
    ids = [w["wing_id"] for w in used]
    print("air attach", ao.attach(target_army, ids).get("ok"))
    for mission in ("air_superiority", "cas"):
        wid = [w["wing_id"] for w in used if mission in w["missions"]]
        kinds = {}
        for w in ao.own_wings():
            if w["wing_id"] in wid:
                kinds.setdefault(w["type"], []).append(w["wing_id"])
        for k, v in kinds.items():
            print("air", mission, k, ao.set_mission(v, mission).get("ok"))
    # traits the user gave
    for lid, names in TRAITS.items():
        for n in names:
            print("trait", lid, n, ltr.learn(lid, n).get("ok"))
    # execute: the main group (with its armies) and the army with its own plan
    print("exec main", orbat.execute(mg, 0, True, flag_35=1).get("ok"))
    for a in user_armies:
        if a["plans"]:
            print("exec army", orbat.execute(new_id[a["army_id"]], 0, True).get("ok"))


def run(days: int):
    import ai_benchmark as ab
    import live_input
    LOG.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(days):
        ab.run_hours_bg(24)
        try:
            r = live_input.capture()
            ext = r.get("commander_ext") or {}
            w = r["observation"]["world"]
            att = {u for c in w["combats"] for u in c["attacker_unit_ids"]}
            row = {"game": r["observation"]["meta"]["game_time"],
                   "POL": (ext.get("enemy_controlled_provinces") or {}).get("POL"),
                   "surrender": ((ext.get("surrender") or {}).get("POL") or {}).get("progress_pct"),
                   "attacking": sum(1 for u in w["own_units"] if u["unit_id"] in att), "combats": len(w["combats"])}
        except Exception as e:
            row = {"error": f"{type(e).__name__}: {e}"[:120], "clock": lt.Session(check_sha=False).clock()}
        print(json.dumps(row, ensure_ascii=False), flush=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if row.get("POL") == 0 or (row.get("surrender") or 0) >= 100:
            break


if __name__ == "__main__":
    if sys.argv[1] == "deploy":
        deploy()
    else:
        run(int(sys.argv[2]))
