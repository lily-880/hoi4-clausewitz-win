"""decide() v3: staff rules rewritten after the 62-day Poland baseline.

Keeps v1 (R1 reinforce, R2 withdraw, R3 counter-attack). Replaces v2's R4/R5:

R6 home defense (user 2026-11-24: "德国本土不能被占领")
  Every own border province of the home land region that faces an enemy that
  is not a primary offensive target (e.g. France) keeps at least DEFENSE_MIN
  divisions. Short provinces are filled first, by strategic redeploy, from
  idle divisions standing far from any front (neutral borders first: the two
  divisions parked on the Dutch border in the baseline did nothing). Divisions
  on the defense line are never pulled away by the staff.

R5' width-aware attacks (baseline: up to 54 divisions in one province)
  For each primary-target enemy province on our border, attackers from all
  adjacent own provinces are pooled (more directions = more width and the
  flanking bonus) up to the province's combat width. Targets are ranked by
  difficulty: terrain, river crossing, fort, visible enemy divisions, and
  victory points pull. Armor prefers open ground without rivers. Divisions
  that do not fit any target wait as rested reserve instead of queueing.

R4' redeploy toward the front with a per-province cap (MAX_PER_BORDER), so
  reserves spread along the front instead of stacking in one rear province.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import commander_view as cv  # noqa: E402
import decide_v0  # noqa: E402
import decide_v1  # noqa: E402

VERSION = "decide_v3"
ATTACK_MIN_ORG = 30.0
MAX_REDEPLOY = 40
MAX_ATTACK = 80
MAX_PER_BORDER = 6
WIDTH_FILL = 1.0  # fraction of the combat width the staff fills per target


def _idle(u: dict) -> bool:
    return not u.get("in_combat") and not (u.get("order") or {}).get("path_province_ids")


def _region(ext, pid):
    return cv._region(ext, pid)


def staff_orders(doc: dict, used: set[int]) -> tuple[list[dict], list[str]]:
    ext = doc.get("_ext") or {}
    world = doc.get("world", {}) or {}
    units = world.get("own_units", [])
    names = {u["unit_id"]: decide_v0.label(u) for u in units}
    hops = (ext.get("topology") or {}).get("hops_to_border") or {}
    watch = set(ext.get("own_watch_border", []))
    on_ground: dict[int, list[dict]] = {}
    for u in units:
        if not (u.get("order") or {}).get("path_province_ids"):
            on_ground.setdefault(u.get("province_id"), []).append(u)
    sections = cv.border_sections(doc)
    defense = {p["prov"]: p["divisions"] + p["incoming"]
               for s in sections if s["role"] == "home_defense" for p in s["provinces"]}
    orders: list[dict] = []
    notes: list[str] = []

    def h(pid):
        x = hops.get(pid, hops.get(str(pid)))
        return 99 if x is None else x

    # ---- R6 home defense ----
    short = sorted((p for p, n in defense.items() if n < cv.DEFENSE_MIN), key=lambda p: defense[p])
    home = cv.home_region(ext)
    attack_border = {b["province_id"] for b in ext.get("own_border", [])} - set(defense)
    pool = [u for u in units if u["unit_id"] not in used and _idle(u)
            and u.get("province_id") not in defense and u.get("province_id") not in attack_border
            and _region(ext, u.get("province_id")) == home]
    # neutral-border sitters first, then the farthest from any front, infantry before mobile units
    pool.sort(key=lambda u: (u.get("province_id") not in watch, -h(u.get("province_id")),
                             cv.unit_kind(u) in ("armor", "motorized"), u["unit_id"]))
    n_def = 0
    for prov in short:
        while defense[prov] < cv.DEFENSE_MIN and pool:
            u = pool.pop(0)
            orders.append({"type": "strategic_redeploy", "unit": u["unit_id"], "target": prov,
                           "reason": f"{names[u['unit_id']]} 填补本土防线省 {prov}"})
            used.add(u["unit_id"])
            defense[prov] += 1
            n_def += 1
    if n_def:
        notes.append(f"本土防线补防：{n_def} 个师")
    still = [p for p, n in defense.items() if n < cv.DEFENSE_MIN]
    if still:
        notes.append(f"本土防线仍有 {len(still)} 个省不足 {cv.DEFENSE_MIN} 个师")

    # ---- R5' width-aware attacks on primary targets ----
    tinfo = {e["province_id"]: e for e in ext.get("enemy_border", [])
             if (e.get("controller") or {}).get("tag") in cv.PRIMARY_TARGETS}
    if not tinfo:
        return orders, notes
    attackers_of: dict[int, list[int]] = {}
    river: dict[tuple, bool] = {}
    for b in ext.get("own_border", []):
        if b["province_id"] in defense:
            continue
        for n in b.get("enemy_neighbors", []):
            if n in tinfo:
                attackers_of.setdefault(n, []).append(b["province_id"])
                river[(b["province_id"], n)] = n in (b.get("river_crossing_to") or [])
    enemy_seen: dict[int, int] = {}
    for v in world.get("visible_units", []):
        if v.get("relation_to_player") == "enemy":
            enemy_seen[v.get("province_id")] = enemy_seen.get(v.get("province_id"), 0) + 1
    # width already committed by our ongoing attacks
    committed: dict[int, float] = {}
    by_id = {u["unit_id"]: u for u in units}
    for c in world.get("combats", []):
        ours = [by_id[x] for x in c.get("attacker_unit_ids", []) if x in by_id]
        if ours:
            committed[c["province_id"]] = committed.get(c["province_id"], 0) + sum(cv.width(u) for u in ours)

    def difficulty(t, armor=False):
        e = tinfo[t]
        terr = e.get("terrain") or "plains"
        d = cv.TERRAIN_PENALTY.get(terr, 1) * (2 if armor else 1)
        srcs = attackers_of.get(t, [])
        if srcs and all(river.get((s, t)) for s in srcs):
            d += 3 if armor else 2
        d += 2 * (e.get("fort_level") or 0)
        d += enemy_seen.get(t, 0)
        d -= min(3, (e.get("victory_points") or 0) / 10)
        d -= 0.5 * (len(srcs) - 1)  # more directions: flanking bonus and width
        return d

    cap: dict[int, float] = {}
    for t in tinfo:
        base, extra = cv.TERRAIN_WIDTH.get(tinfo[t].get("terrain") or "plains", (70, 35))
        cap[t] = WIDTH_FILL * (base + extra * max(0, len(attackers_of.get(t, [])) - 1)) - committed.get(t, 0)
    n_attack = 0
    ready_by_src = {}
    for src in {s for ss in attackers_of.values() for s in ss}:
        ready_by_src[src] = sorted(
            (u for u in on_ground.get(src, []) if u["unit_id"] not in used and _idle(u)
             and (u.get("organization") or 0) >= ATTACK_MIN_ORG),
            key=lambda u: (cv.unit_kind(u) != "armor", -(u.get("organization") or 0)))
    for src in sorted(ready_by_src):
        targets = [t for t, ss in attackers_of.items() if src in ss]
        for u in ready_by_src[src]:
            if n_attack >= MAX_ATTACK:
                break
            armor = cv.unit_kind(u) in ("armor", "motorized")
            fit = [t for t in targets if cap[t] >= cv.width(u)]
            if not fit:
                continue  # rested reserve: no width left on reachable targets
            t = min(fit, key=lambda t: (difficulty(t, armor), t))
            cap[t] -= cv.width(u)
            terr = tinfo[t].get("terrain") or "?"
            orders.append({"type": "attack", "unit": u["unit_id"], "target": t,
                           "reason": f"{names[u['unit_id']]} 从 {src} 进攻 {t}（{terr}）"})
            used.add(u["unit_id"])
            n_attack += 1
    if n_attack:
        notes.append(f"按战斗宽度分配进攻：{n_attack} 个师，{len({o['target'] for o in orders if o['type'] == 'attack'})} 个目标")

    # ---- R4' bring reserves forward, capped per border province ----
    allied = {b["province_id"] for b in ext.get("own_border", []) if b.get("friendly_controller")}
    offensive = {s: 0 for ss in attackers_of.values() for s in ss if s not in allied}  # redeploy ends on own soil only
    for s in offensive:
        offensive[s] = len(on_ground.get(s, []))
    for u in units:
        route = (u.get("order") or {}).get("path_province_ids") or []
        if route and route[-1] in offensive:
            offensive[route[-1]] += 1
    movers = [u for u in units if u["unit_id"] not in used and _idle(u)
              and u.get("province_id") not in defense and u.get("province_id") not in offensive
              and u.get("province_id") not in attack_border and u.get("province_id") not in allied]
    movers.sort(key=lambda u: (cv.unit_kind(u) not in ("armor", "motorized"), u["unit_id"]))
    n_move = 0
    for u in movers:
        if n_move >= MAX_REDEPLOY:
            break
        same = [p for p in offensive if _region(ext, p) == _region(ext, u.get("province_id"))
                and offensive[p] < MAX_PER_BORDER]
        if not same:
            continue
        dest = min(same, key=lambda p: (offensive[p], p))
        offensive[dest] += 1
        orders.append({"type": "strategic_redeploy", "unit": u["unit_id"], "target": dest,
                       "reason": f"{names[u['unit_id']]} 前出到进攻边境省 {dest}"})
        used.add(u["unit_id"])
        n_move += 1
    if n_move:
        notes.append(f"预备队前出：{n_move} 个师（每省不超过 {MAX_PER_BORDER} 个）")
    return orders, notes


def decide(input_doc: dict) -> dict:
    out = decide_v1.decide(input_doc)
    meta = input_doc.get("meta", {}) or {}
    if meta.get("allow_write") is not True or not isinstance(meta.get("geography_scope"), dict):
        return out
    # v1 may move defense-line divisions (reinforce/retreat); keep those, they react to combat.
    used = {o["subject"]["unit_ids"][0] for o in out["orders"]}
    extra, notes = staff_orders(input_doc, used)
    seq = max([o["order_seq"] for o in out["orders"]], default=0)
    by_kind: dict[str, list[int]] = {}
    for o in extra:
        seq += 1
        out["orders"].append({"order_seq": seq, "type": o["type"], "subject": {"unit_ids": [o["unit"]]},
                              "target_province_ids": [o["target"]], "reason": o["reason"]})
        by_kind.setdefault(o["type"], []).append(seq)
    for kind, seqs in by_kind.items():
        uids = [o["subject"]["unit_ids"][0] for o in out["orders"] if o["order_seq"] in seqs]
        out["intents"].append({"intent_id": f"v3-{kind}", "kind": "exploit" if kind == "attack" else "concentrate",
                               "subject": {"unit_ids": uids}, "expands_to_order_seqs": seqs,
                               "notes": "按宽度进攻" if kind == "attack" else "补防与前出"})
    if notes and out.get("brief"):
        out["brief"]["summary"] = "；".join(notes) + "。" + out["brief"]["summary"].replace(
            "允许写入，本拍无需下令", f"本拍共 {len(out['orders'])} 条命令")
    return out
