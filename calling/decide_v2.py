"""decide() v2: offensive war of conquest, built on decide_v1.

Keeps v1 (R1 reinforce, R2 withdraw, R3 counter-attack) and adds, using the
commander front view (doc["_ext"], from live_input's commander_ext):

R4 concentrate on the front
  Idle divisions that are not on a hostile border and not on a watched
  (western, not-at-war) border strategically redeploy to the own border
  province with the fewest divisions per hostile neighbour.

R5 general offensive
  Idle divisions standing on a hostile border attack. All idle divisions of
  one province strike the same hostile neighbour: the one with the fewest
  enemy divisions we can see there (unknown counts as 0), then the lowest id.

Divisions with organization below ATTACK_MIN_ORG rest instead of attacking.
Orders per tick are capped so a tick stays short; the rest follow next tick.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import decide_v0  # noqa: E402
import decide_v1  # noqa: E402

VERSION = "decide_v2"
ATTACK_MIN_ORG = 25.0
MAX_REDEPLOY = 40
MAX_ATTACK = 80


def _idle(u: dict) -> bool:
    return (not u.get("in_combat")
            and not (u.get("order") or {}).get("path_province_ids"))


def offensive_orders(doc: dict, used: set[int]) -> tuple[list[dict], list[str]]:
    ext = doc.get("_ext") or {}
    world = doc.get("world", {}) or {}
    border = {b["province_id"]: b for b in ext.get("own_border", [])}
    watch = set(ext.get("own_watch_border", []))
    if not border:
        return [], []
    units = [u for u in world.get("own_units", []) if u["unit_id"] not in used]
    names = {u["unit_id"]: decide_v0.label(u) for u in units}
    enemy_seen: dict[int, int] = {}
    for v in world.get("visible_units", []):
        if v.get("relation_to_player") == "enemy":
            enemy_seen[v.get("province_id")] = enemy_seen.get(v.get("province_id"), 0) + 1
    on_ground: dict[int, list[dict]] = {}
    for u in world.get("own_units", []):
        on_ground.setdefault(u.get("province_id"), []).append(u)

    orders: list[dict] = []
    notes: list[str] = []

    # R5: attack from the border
    n_attack = 0
    for prov, b in sorted(border.items()):
        ready = [u for u in on_ground.get(prov, []) if u["unit_id"] not in used and _idle(u)
                 and (u.get("organization") or 0) >= ATTACK_MIN_ORG]
        if not ready:
            continue
        target = sorted(b["enemy_neighbors"], key=lambda n: (enemy_seen.get(n, 0), n))[0]
        for u in ready:
            if n_attack >= MAX_ATTACK:
                break
            orders.append({"type": "attack", "unit": u["unit_id"], "target": target,
                           "reason": f"{names.get(u['unit_id'], u['unit_id'])} 从边境省 {prov} 进攻 {target}"})
            used.add(u["unit_id"])
            n_attack += 1
    if n_attack:
        notes.append(f"全线进攻：{n_attack} 个师从边境出击")

    # R4: bring the rest to the front
    load = {p: len(on_ground.get(p, [])) / max(1, len(b["enemy_neighbors"])) for p, b in border.items()}
    movers = [u for u in units if u["unit_id"] not in used and _idle(u)
              and u.get("province_id") not in border and u.get("province_id") not in watch]
    movers.sort(key=lambda u: u["unit_id"])
    n_move = 0
    for u in movers[:MAX_REDEPLOY]:
        dest = min(load, key=lambda p: (load[p], p))
        load[dest] += 1 / max(1, len(border[dest]["enemy_neighbors"]))
        orders.append({"type": "strategic_redeploy", "unit": u["unit_id"], "target": dest,
                       "reason": f"{names.get(u['unit_id'], u['unit_id'])} 战略转移到边境省 {dest}"})
        used.add(u["unit_id"])
        n_move += 1
    if n_move:
        notes.append(f"向前线集结：{n_move} 个师战略转移")
    return orders, notes


def decide(input_doc: dict) -> dict:
    out = decide_v1.decide(input_doc)
    meta = input_doc.get("meta", {}) or {}
    if meta.get("allow_write") is not True or not isinstance(meta.get("geography_scope"), dict):
        return out
    used = {o["subject"]["unit_ids"][0] for o in out["orders"]}
    extra, notes = offensive_orders(input_doc, used)
    seq = max([o["order_seq"] for o in out["orders"]], default=0)
    by_kind: dict[str, list[int]] = {}
    for o in extra:
        seq += 1
        order = {"order_seq": seq, "type": o["type"], "subject": {"unit_ids": [o["unit"]]},
                 "target_province_ids": [o["target"]], "reason": o["reason"]}
        out["orders"].append(order)
        by_kind.setdefault(o["type"], []).append(seq)
    for kind, seqs in by_kind.items():
        units = [o["subject"]["unit_ids"][0] for o in out["orders"] if o["order_seq"] in seqs]
        out["intents"].append({"intent_id": f"v2-{kind}", "kind": "exploit" if kind == "attack" else "concentrate",
                               "subject": {"unit_ids": units}, "expands_to_order_seqs": seqs,
                               "notes": "全线进攻" if kind == "attack" else "向前线集结"})
    if notes and out.get("brief"):
        out["brief"]["summary"] = "；".join(notes) + "。" + out["brief"]["summary"].replace(
            "允许写入，本拍无需下令", f"本拍共 {len(out['orders'])} 条命令")
        ext = input_doc.get("_ext") or {}
        if ext.get("enemy_controlled_provinces"):
            out["brief"].setdefault("risks", []).append(
                "敌方仍控制省份：" + "、".join(f"{k} {v}" for k, v in ext["enemy_controlled_provinces"].items()))
    return out
