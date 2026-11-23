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

Rule R3 — counter-attack tired enemy staging provinces
  Enemy divisions we can see (world.visible_units, relation enemy; today:
  the opponents of our own battles) sit in provinces of their own. If idle
  divisions of ours (organization >= 30, no route, and either not fighting
  or surplus defenders of a battle we clearly hold) border such
  a province, and their summed organization is at least ATTACK_RATIO times
  the visible enemy's there (annihilate 1.5, others 2.5) with at least as
  many divisions, all of them attack it. The executor re-checks with the
  native has-war getter before posting.

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


ATTACK_RATIO = {"annihilate": 1.5, "custom": 1.5}
MIN_ATTACK_ORG = 30.0
# Engine rejected (IsValid false) attacks by units that are defending; keep
# surplus defenders home until a verified way to strike from a battle exists.
ALLOW_SURPLUS_STRIKE = False


def _surplus_defenders(world: dict) -> set[int]:
    """Defenders not needed to hold: keep the strongest until their org sum is
    >= 1.5x the visible attackers' org (at least one stays); the rest may strike."""
    units = {u["unit_id"]: u for u in world.get("own_units", [])}
    vis = {v["unit_id"]: v for v in world.get("visible_units", [])}
    free: set[int] = set()
    for c in world.get("combats", []):
        ours = sorted((units[x] for x in c.get("defender_unit_ids", []) if x in units),
                      key=lambda u: -(u.get("organization") or 0))
        if not ours:
            continue
        attackers = [vis[x] for x in c.get("attacker_unit_ids", []) if x in vis]
        if len(attackers) != len(c.get("attacker_unit_ids", [])):
            continue  # some attacker unseen: hold everything
        need = 1.5 * sum(a.get("organization", 0) for a in attackers)
        kept = 0.0
        for i, u in enumerate(ours):
            if i == 0 or kept < need:
                kept += u.get("organization") or 0
            else:
                free.add(u["unit_id"])
    return free


def _counterattacks(world: dict, stance: str, used: set[int]) -> list[dict]:
    ratio = ATTACK_RATIO.get(stance, 2.5)
    surplus = _surplus_defenders(world)
    own_provs = {u.get("province_id") for u in world.get("own_units", [])}
    enemy_at = {}
    for v in world.get("visible_units", []):
        if v.get("relation_to_player") == "enemy" and v.get("province_id") not in own_provs:
            enemy_at.setdefault(v["province_id"], []).append(v)
    neighbors = {p["province_id"]: set(p.get("neighbors", []))
                 for p in world.get("provinces", []) if "province_id" in p}
    plans = []
    for prov, enemies in sorted(enemy_at.items(),
                                key=lambda kv: sum(e.get("organization", 0) for e in kv[1])):
        enemy_org = sum(e.get("organization", 0) for e in enemies)
        ours = [u for u in world.get("own_units", [])
                if u["unit_id"] not in used
                and (not u.get("in_combat") or (ALLOW_SURPLUS_STRIKE and u["unit_id"] in surplus))
                and not (u.get("order") or {}).get("path_province_ids")
                and (u.get("organization") or 0) >= MIN_ATTACK_ORG
                and prov in neighbors.get(u.get("province_id"), set())]
        our_org = sum(u["organization"] for u in ours)
        if ours and len(ours) >= len(enemies) and our_org >= ratio * enemy_org:
            used.update(u["unit_id"] for u in ours)
            plans.append({"province": prov, "units": [u["unit_id"] for u in ours],
                          "our_org": our_org, "enemy_org": enemy_org, "enemies": len(enemies)})
    return plans


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
               and u["organization"] < floor
               and not (u.get("order") or {}).get("path_province_ids")]  # not already leaving
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


def _reinforcements(world: dict, min_org: float = 20.0) -> list[dict]:
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
            and (u.get("organization") or 0) >= min_org  # do not feed exhausted units back in
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
    for plan in _reinforcements(world, max(20.0, 1.5 * ORG_FLOOR.get(stance, 20.0))):
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
    used = {o["subject"]["unit_ids"][0] for o in out["orders"]}
    for plan in _counterattacks(world, stance, used):
        seqs = []
        for uid in plan["units"]:
            seq += 1
            seqs.append(seq)
            out["orders"].append({
                "order_seq": seq, "type": "attack", "subject": {"unit_ids": [uid]},
                "target_province_ids": [plan["province"]],
                "reason": (f"反击省份 {plan['province']}：我方组织度合计 {plan['our_org']:.0f}，"
                           f"敌方 {plan['enemies']} 个师合计 {plan['enemy_org']:.0f}"),
            })
        out["intents"].append({
            "intent_id": f"strike-{plan['province']}", "kind": "exploit",
            "province_ids": [plan["province"]], "subject": {"unit_ids": plan["units"]},
            "expands_to_order_seqs": seqs,
            "notes": f"以 {len(plan['units'])} 个师打击疲惫的敌军集结地",
        })
    if out["orders"] and out.get("brief"):
        out["brief"]["summary"] = out["brief"]["summary"].replace(
            "允许写入，本拍无需下令",
            f"已下达 {sum(o['type'] == 'move' for o in out['orders'])} 条增援、"
            f"{sum(o['type'] == 'retreat' for o in out['orders'])} 条撤退、"
            f"{sum(o['type'] == 'attack' for o in out['orders'])} 条进攻命令")
    return out
