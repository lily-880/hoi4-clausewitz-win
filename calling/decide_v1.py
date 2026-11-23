"""decide() v1: v0's alerts/brief plus one tactical rule.

Rule R1 — reinforce outnumbered defences
  For every land combat where our divisions defend and the attackers have
  more units than we do, move idle neighbouring divisions into that province,
  at most (attackers - defenders) of them, nearest first by organization.

  "Idle neighbouring" means: our division, not in combat, not standing in a
  province that is itself defended in a combat, and its own province lists
  the combat province among its land neighbours (world.provinces[].neighbors,
  i.e. read from the engine, never guessed).

Rule R2 — pull out collapsing defenders
  A defending division whose organization is below the stance threshold
  (preserve_force / economize_manpower / hold_line 20, annihilate / custom 10)
  retreats to a neighbouring province that we control (engine-registered
  controller), that is not itself a combat province, preferring the one with
  most of our divisions. A province is never emptied by R2 unless every
  defender there is below the threshold. Emitted as the contract's `retreat`
  command; the executor carries it out as a move out of the battle.

Orders are only produced when meta.allow_write is true and geography_scope is
set (the contract rejects writes otherwise). Only commands verified end to end
on 1.19.5 are used: move.

Pure offline: no process access. The executor re-checks idleness and dry-runs
every order before posting, so a stale "idle" guess is refused, not posted.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import decide_v0  # noqa: E402

VERSION = "decide_v1"
ORG_FLOOR = {"preserve_force": 20.0, "economize_manpower": 20.0, "hold_line": 20.0,
             "annihilate": 10.0, "custom": 10.0}


def _withdrawals(world: dict, player_index: int | None, stance: str) -> list[dict]:
    floor = ORG_FLOOR.get(stance, 20.0)
    units = {u["unit_id"]: u for u in world.get("own_units", []) if "unit_id" in u}
    provs = {p["province_id"]: p for p in world.get("provinces", []) if "province_id" in p}
    combat_provs = {c["province_id"] for c in world.get("combats", [])}
    on_ground = {}
    for u in units.values():
        on_ground.setdefault(u.get("province_id"), []).append(u["unit_id"])
    out = []
    for c in world.get("combats", []):
        ours = [units[x] for x in c.get("defender_unit_ids", []) if x in units]
        low = [u for u in ours if isinstance(u.get("organization"), (int, float))
               and u["organization"] < floor]
        if not low:
            continue
        if True:  # low ones leave; any defender above the floor keeps holding
            safe = []
            for n in provs.get(c["province_id"], {}).get("neighbors", []):
                info = provs.get(n)
                if (n not in combat_provs and info is not None
                        and (info.get("controller") or {}).get("index") == player_index):
                    safe.append((-len(on_ground.get(n, [])), n))
            if not safe:
                continue
            dest = sorted(safe)[0][1]
            for u in sorted(low, key=lambda u: u["organization"]):
                out.append({"unit": u["unit_id"], "from": c["province_id"], "to": dest,
                            "org": u["organization"], "floor": floor})
    return out


def _reinforcements(world: dict) -> list[dict]:
    units = {u["unit_id"]: u for u in world.get("own_units", []) if "unit_id" in u}
    neighbors = {p["province_id"]: set(p.get("neighbors", []))
                 for p in world.get("provinces", []) if "province_id" in p}
    defended = {}
    for c in world.get("combats", []):
        ours = [u for u in c.get("defender_unit_ids", []) if u in units]
        if ours:
            defended[c["province_id"]] = (c, ours)
    used: set[int] = set()
    plans = []
    for prov, (combat, ours) in sorted(defended.items(),
                                       key=lambda kv: -(len(kv[1][0].get("attacker_unit_ids", []))
                                                        - len(kv[1][1]))):
        need = len(combat.get("attacker_unit_ids", [])) - len(ours)
        if need <= 0:
            continue
        candidates = [
            u for uid, u in units.items()
            if uid not in used and not u.get("in_combat")
            and not (u.get("order") or {}).get("path_province_ids")  # already marching
            and u.get("province_id") not in defended
            and prov in neighbors.get(u.get("province_id"), set())
        ]
        candidates.sort(key=lambda u: (-(u.get("organization") or 0), u["unit_id"]))
        chosen = candidates[:need]
        if chosen:
            used.update(u["unit_id"] for u in chosen)
            plans.append({"province": prov, "combat": combat, "defenders": ours,
                          "units": [u["unit_id"] for u in chosen], "need": need})
    return plans


def decide(input_doc: dict) -> dict:
    out = decide_v0.decide(input_doc)
    meta = input_doc.get("meta", {}) or {}
    if meta.get("allow_write") is not True or not isinstance(meta.get("geography_scope"), dict):
        return out
    world = input_doc.get("world", {}) or {}
    stance = (input_doc.get("policy") or {}).get("stance", decide_v0.DEFAULT_STANCE)
    player = (meta.get("player_country") or {}).get("index")
    seq = 0
    for w in _withdrawals(world, player, stance):
        seq += 1
        out["orders"].append({
            "order_seq": seq, "type": "retreat", "subject": {"unit_ids": [w["unit"]]},
            "to_province_ids": [w["to"]],
            "reason": f"守军组织度 {w['org']:.1f} 低于 {w['floor']:.0f}，撤出省份 {w['from']} 保存兵力",
        })
    for plan in _reinforcements(world):
        seqs = []
        for uid in plan["units"]:
            seq += 1
            seqs.append(seq)
            out["orders"].append({
                "order_seq": seq, "type": "move", "subject": {"unit_ids": [uid]},
                "target_province_ids": [plan["province"]],
                "reason": (f"增援省份 {plan['province']} 的防守：敌方 "
                           f"{len(plan['combat'].get('attacker_unit_ids', []))} 个单位对我方 "
                           f"{len(plan['defenders'])} 个师"),
            })
        out["intents"].append({
            "intent_id": f"hold-{plan['province']}", "kind": "hold_line",
            "province_ids": [plan["province"]], "subject": {"unit_ids": plan["units"]},
            "expands_to_order_seqs": seqs,
            "notes": f"敌我数量差 {plan['need']}，调入 {len(plan['units'])} 个相邻空闲师",
        })
    if out["orders"] and out.get("brief"):
        out["brief"]["summary"] = out["brief"]["summary"].replace(
            "允许写入，本拍无需下令",
            f"已下达 {sum(o['type'] == 'move' for o in out['orders'])} 条增援、"
            f"{sum(o['type'] == 'retreat' for o in out['orders'])} 条撤退命令")
    return out
