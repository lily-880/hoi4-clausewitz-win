"""Commander plan orders: order of battle, front lines, offensive lines, execution.

The commander (decide_llm) decides these (user 2026-11-24: drawing front and
offensive lines is the commander's job). This module only
  * summarises the current order of battle and plans for the model (view()),
  * checks each plan order against the live game (validate()),
  * carries it out through orbat (apply()), one gated command each.

Plan order shapes (model output, key "plan_orders"):
  {"type": "front_line",     "army_id": 534, "enemy": "POL", "reason": "..."}
  {"type": "offensive_line", "army_id": 534, "path": [6567, 3544], "reason": "..."}
  {"type": "execute",        "army_id": 534, "on": true, "reason": "..."}
  {"type": "create_army",    "unit_ids": [..<=24], "leader_id": 349, "reason": "..."}
  {"type": "create_army_group", "army_ids": [..], "leader_id": 342, "reason": "..."}
  {"type": "appoint",        "leader_id": 349, "group_id": 534, "reason": "..."}
  {"type": "promote",        "leader_id": 342, "reason": "..."}   general -> field marshal (command power)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import commander_view as cv  # noqa: E402

TYPES = ("front_line", "offensive_line", "delete_offensive_line", "execute", "create_army",
         "create_army_group", "appoint", "promote")
MAX_PER_TICK = 12
ARMY_MAX = 24
FRONTS_FILE = HERE / "tables" / "army_fronts.json"
# Leaders the game un-assigns right after an appointment (focus-path / retired characters that are
# still on the roster, e.g. Mackensen and Blomberg in the 1939 historical game). Keyed by character
# key; filled by observation: an appointment that held at post time but is gone a tick later.
UNAVAILABLE_FILE = HERE / "tables" / "unavailable_leaders.json"


def _load_unavailable() -> dict:
    try:
        return json.loads(UNAVAILABLE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"unavailable": {}, "pending_appointments": {}}


def _save_unavailable(data: dict) -> None:
    UNAVAILABLE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pend(leader_id: int, group_id: int) -> None:
    data = _load_unavailable()
    data.setdefault("pending_appointments", {})[str(leader_id)] = {"group_id": group_id}
    _save_unavailable(data)


def _check_appointments(leaders_live: dict) -> set:
    """Mark leaders whose last appointment the game revoked; return the unavailable keys."""
    data = _load_unavailable()
    pend = data.get("pending_appointments", {})
    changed = False
    for lid_s, p in list(pend.items()):
        l = leaders_live.get(int(lid_s))
        if l is None:
            continue
        if l["assigned_group"] != p["group_id"]:
            data["unavailable"][l["key"]] = "任命后被游戏撤销"
        pend.pop(lid_s)
        changed = True
    if changed:
        _save_unavailable(data)
    return set(data.get("unavailable", {}))


def _session():
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import live_trial as lt
    return lt.Session(check_sha=False)


LINE_PROGRESS_FILE = HERE / "tables" / "line_progress.json"


def _line_progress(s, armies: list) -> None:
    """Annotate each offensive line with how it is doing (exam 6, 2026-11-25: arrows drawn on
    08-17 were never redrawn although their start provinces had long been taken, and fronts the
    game split after a pocket sat without any line):
      start_taken / target_taken  the line's first / last province is ours now
      provinces_to_target         land steps from the target to the nearest province we hold
      no_progress_since           game date since provinces_to_target last changed
    and each executing front without a line with "needs_offensive_line"."""
    me = s.player.get("player_index")
    clk = s.clock()
    now = f"{clk.get('ui_date')} {clk.get('ui_hour')}h"
    try:
        hist = json.loads(LINE_PROGRESS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        hist = {}
    nb: dict = {}
    ctrl: dict = {}

    def c(p):
        if p not in ctrl:
            ctrl[p] = s.controller_of(p)
        return ctrl[p]

    def n(p):
        if p not in nb:
            nb[p] = list(s.land_neighbors(p).get("neighbors") or [])
        return nb[p]

    def hops(target):
        if c(target) == me:
            return 0
        seen, frontier, d = {target}, [target], 0
        while frontier and d < 40:
            d += 1
            nxt = []
            for x in frontier:
                for y in n(x):
                    if y in seen:
                        continue
                    if c(y) == me:
                        return d
                    seen.add(y)
                    nxt.append(y)
            frontier = nxt
        return None

    live = set()
    for a in armies:
        for f in a["fronts"]:
            if f["executing"] and not f["offensive_lines"]:
                f["needs_offensive_line"] = True
            for l in f["offensive_lines"]:
                if not l["path"]:
                    continue
                key = str(l["plan_id"])
                live.add(key)
                h = hops(l["path"][-1])
                l["start_taken"] = c(l["path"][0]) == me
                l["target_taken"] = c(l["path"][-1]) == me
                l["provinces_to_target"] = h
                old = hist.get(key)
                if not old or old.get("hops") != h:
                    hist[key] = {"hops": h, "since": now}
                l["no_progress_since"] = hist[key]["since"]
    hist = {k: v for k, v in hist.items() if k in live}
    try:
        LINE_PROGRESS_FILE.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def view(doc: dict, session=None) -> dict:
    """Order of battle and plans for the model (live read; empty dict if unavailable)."""
    try:
        import orbat
        s = session or _session()
        snap = orbat.snapshot(s)
    except Exception as e:  # never block a tick on this
        return {"error": f"{type(e).__name__}"}
    units = {u["unit_id"]: u for u in (doc.get("world") or {}).get("own_units", [])}
    leaders_live = {l["leader_id"]: l for l in snap["leaders"]}
    leader_info = {l.get("leader_id"): l for l in (doc.get("world") or {}).get("leaders", [])}

    unavailable = _check_appointments(leaders_live)

    def rank_of(lid):
        return (leaders_live.get(lid) or {}).get("rank") if lid is not None else None
    in_army = set()
    armies, groups = [], []
    for t in snap["theatres"]:
        for a in t["armies"]:
            in_army.update(a["unit_ids"])
            kinds = {}
            for u in a["unit_ids"]:
                k = cv.unit_kind(units.get(u, {}))
                kinds[k] = kinds.get(k, 0) + 1
            fronts = []
            for p in a["plans"]:
                if not p["path"] and not p["children"]:
                    continue
                fronts.append({"plan_id": p["plan_id"], "front_provinces": len(p["path"]),
                               "front_ends": [p["path"][0], p["path"][-1]] if p["path"] else [],
                               "divisions_on_plan": p["members"],
                               "executing": bool(p["can_execute"]) and all(p.get("sub_executing") or [1]),
                               "offensive_lines": [{"plan_id": c["plan_id"], "path": c["path"]} for c in p["children"]]})
            lead = leader_info.get(a["leader_id"], {})
            armies.append({"army_id": a["id"], "name": a["name"], "army_group_id": a.get("army_group_id"),
                           "leader": lead.get("name") or a["leader_id"], "leader_skill": lead.get("skill"),
                           "leader_rank": rank_of(a["leader_id"]),
                           "divisions": len(a["unit_ids"]), "kinds": kinds,
                           "avg_org": round(sum((units.get(u, {}).get("organization") or 0) for u in a["unit_ids"])
                                            / max(1, len(a["unit_ids"])), 1),
                           "fronts": fronts})
        # how each army's divisions are being used (exam 8: 24 divisions with 1 attacking went
        # unnoticed for days)
        world_ = doc.get("world") or {}
        attackers = {u for c in world_.get("combats", []) for u in c.get("attacker_unit_ids") or []}
        defenders = {u for c in world_.get("combats", []) for u in c.get("defender_unit_ids") or []}
        use = {}
        for u in world_.get("own_units", []):
            aid = (u.get("formation") or {}).get("army_id")
            if aid is None:
                continue
            k = ("attacking" if u["unit_id"] in attackers else "defending" if u["unit_id"] in defenders
                 else "marching" if (u.get("order") or {}).get("path_province_ids") else
                 "resting_low_org" if (u.get("organization") or 0) < 30 else "idle")
            use.setdefault(aid, {}).setdefault(k, 0)
            use[aid][k] += 1
        for a_ in armies:
            a_["divisions_use"] = use.get(a_["army_id"], {})
        try:
            _line_progress(s, armies)
        except Exception:
            pass
        for g in t["army_groups"]:
            lead = leader_info.get(g["leader_id"], {})
            groups.append({"army_group_id": g["id"], "name": g["name"], "army_ids": g.get("army_ids"),
                           "leader": lead.get("name") or g["leader_id"], "leader_rank": rank_of(g["leader_id"])})
    starts: dict = {}
    for a in armies:
        for f in a["fronts"]:
            for l in f["offensive_lines"]:
                if l["path"]:
                    starts.setdefault(l["path"][0], []).append(a["army_id"])
    for a in armies:
        for f in a["fronts"]:
            for l in f["offensive_lines"]:
                others = [x for x in starts.get(l["path"][0] if l["path"] else None, []) if x != a["army_id"]]
                if others:
                    l["same_start_as_armies"] = others
    free_units = [u for u in units if u not in in_army]
    free_leaders = [{"leader_id": lid, "name": (leader_info.get(lid) or {}).get("name"),
                     "skill": (leader_info.get(lid) or {}).get("skill"), "rank": l.get("rank")}
                    for lid, l in leaders_live.items() if not l["assigned_group"] and l["key"] not in unavailable]
    # command rules (user 2026-11-24): army groups are led by field marshals, armies by generals,
    # and every army belongs to an army group
    violations = []
    for a in armies:
        if a["leader_rank"] == "field_marshal":
            violations.append(f"集团军 {a['name']}（{a['army_id']}）由元帅 {a['leader']} 指挥：元帅只能指挥集团军群，换一位将军")
        if a["leader_rank"] is None:
            violations.append(f"集团军 {a['name']}（{a['army_id']}）没有指挥官：任命一位将军")
        if not a.get("army_group_id"):
            violations.append(f"集团军 {a['name']}（{a['army_id']}）不属于任何集团军群：编入由元帅指挥的集团军群")
    for g in groups:
        if g["leader_rank"] != "field_marshal":
            violations.append(f"集团军群 {g['name']}（{g['army_group_id']}）不是由元帅指挥：改任元帅")
    # player rule (2026-11-24): no front on another country's soil
    try:
        me_idx = s.player.get("player_index")
        paths = {a_["id"]: [p_["path"] for p_ in a_["plans"]]
                 for t_ in snap["theatres"] for a_ in t_["armies"]}
        for a in armies:
            foreign = {}
            for path in paths.get(a["army_id"], []):
                for pid in path:
                    c = s.controller_of(pid)
                    if c is not None and c != me_idx:
                        tg = s.tag(c) or str(c)
                        foreign[tg] = foreign.get(tg, 0) + 1
            if foreign:
                where = "、".join(f"{k} {v} 个省" for k, v in foreign.items())
                violations.append(f"集团军 {a['name']}（{a['army_id']}）的前线有一部分在别国境内（{where}）："
                                  f"按 border_fronts 的 own_territory_range_pct 重画前线")
    except Exception:
        pass
    me = ((doc.get("meta") or {}).get("player_country") or {}).get("tag")
    sections = {}
    free_by_pos: dict = {}
    try:
        import orbat
        fs = orbat.front_sections(s)
        # where the free divisions stand along each border section (0..100 % of the section, in 10 %
        # bins): an army built from divisions already inside its front's range starts attacking
        # days earlier than one gathered from all over (exams 5 and 6: about a week of reshuffling)
        try:
            where = {u: (units.get(u) or {}).get("province_id") for u in units if u not in in_army}
            for tag, rows in fs.items():
                for r in rows:
                    provs = r["provinces"]
                    idx = {p: i for i, p in enumerate(provs)}
                    for u, p in where.items():
                        if p in idx:
                            pct = int(100 * idx[p] / max(1, len(provs) - 1))
                            key = f"{min(90, pct // 10 * 10)}-{min(100, pct // 10 * 10 + 10)}"
                            free_by_pos.setdefault(tag, {}).setdefault(str(r["section"]), {}) \
                                .setdefault(key, []).append(u)
        except Exception:
            free_by_pos = {}
        for tag, rows in fs.items():
            for r in rows:
                own = orbat.own_range(r["controllers"], me) if me else None
                foreign = sorted({c for c in r["controllers"] if c and c != me})
                sections.setdefault(tag, []).append({
                    "section": r["section"], "provinces": len(r["provinces"]),
                    "ends": [r["provinces"][0], r["provinces"][-1]] if r["provinces"] else [],
                    "other_countries_on_our_side": foreign,
                    "own_territory_range_pct": [round(own[0] / 1000), round(own[1] / 1000)] if own else None})
    except Exception:
        pass
    fronts = sections
    at_war = {e["controller"]["tag"] for e in (doc.get("_ext") or {}).get("enemy_border", []) if e.get("controller")}
    wars = {(w.get("opponent") or {}).get("tag") for w in (doc.get("world") or {}).get("wars", [])} if \
        (doc.get("world") or {}).get("wars") else None
    return {"armies": armies, "army_groups": groups,
            "divisions_not_in_any_army": free_units, "unassigned_leaders": free_leaders,
            "field_marshals_total": sum(1 for l in leaders_live.values()
                                        if l.get("rank") == "field_marshal" and l["key"] not in unavailable),
            "command_rule_violations": violations,
            "border_fronts": {k: v for k, v in fronts.items() if k in at_war},
            "free_divisions_by_border_position": {k: v for k, v in free_by_pos.items() if k in at_war}}


def validate(order: dict, doc: dict, pview: dict) -> str | None:
    """Return a reason string if the plan order must be refused, else None."""
    t = order.get("type")
    if t not in TYPES:
        return "未知的计划命令类型"
    armies = {a["army_id"]: a for a in pview.get("armies", [])}
    ext = doc.get("_ext") or {}
    enemies = {e["controller"]["tag"] for e in ext.get("enemy_border", []) if e.get("controller")}
    enemy_provs = {e["province_id"]: e["controller"]["tag"] for e in ext.get("enemy_border", []) if e.get("controller")}
    # the number in an army's name is not its army_id (exam 7, 09-02: "第5集团军" was ordered
    # as army_id 5, but its id is 463, and the order was refused without saying why)
    for aid in ([order["army_id"]] if "army_id" in order else []) + list(order.get("army_ids") or []):
        if aid not in armies:
            named = [a for a in pview.get("armies", []) if f"第{aid}集团军" in (a.get("name") or "")]
            hint = f"；名称里的数字不是编号，{named[0]['name']}的 army_id 是 {named[0]['army_id']}" if named else ""
            return f"army_id {aid} 不存在{hint}"
    if t == "delete_offensive_line":
        a = armies.get(order.get("army_id"))
        lines = {l["plan_id"] for f in (a or {}).get("fronts", []) for l in f["offensive_lines"]}
        if order.get("plan_id") not in lines:
            return "要删除的进攻线不属于该集团军"
        return None
    if t in ("front_line", "offensive_line", "execute"):
        a = armies.get(order.get("army_id"))
        if not a:
            return "集团军不存在"
        if not a["divisions"]:
            return "集团军没有师"
    if t == "execute" and order.get("on", True):
        if not any(f["offensive_lines"] for f in a["fronts"]):
            return "该集团军没有进攻线，执行也不会进攻；先画进攻线"
    if t == "front_line":
        if order.get("enemy") not in enemies:
            return "只能对正在交战且接壤的国家画前线"
        secs = (pview.get("border_fronts") or {}).get(order["enemy"]) or []
        if "section" in order and order["section"] not in {x["section"] for x in secs}:
            return "该国边境没有这个前线段编号（见 border_fronts）"
        # player hard rule: the home-defense line keeps its garrison. An army is pulled to its own
        # front, so an army holding garrison troops may only front the country they face.
        sections = cv.border_sections(doc)
        count, faces = {}, {}
        for s_ in sections:
            if s_["role"] == "home_defense":
                for p_ in s_["provinces"]:
                    count[p_["prov"]] = p_["divisions"]
                    faces.setdefault(p_["prov"], set()).add(str(s_["enemy"]).split("(")[0])
        for u in (doc.get("world") or {}).get("own_units", []):
            pv = u.get("province_id")
            if (u.get("formation") or {}).get("army_id") == order.get("army_id") and pv in count                     and order["enemy"] not in faces[pv]:
                count[pv] -= 1
                if count[pv] < cv.DEFENSE_MIN:
                    return (f"该集团军有守在本土防线省 {pv} 的师（面对 {'、'.join(sorted(faces[pv]))}），对别国画前线会把它们拉走，"
                            f"使该省少于 {cv.DEFENSE_MIN} 个师；这样的集团军只能对它们面对的国家画前线")
        rng = order.get("range_pct")
        if rng is not None and not (isinstance(rng, list) and len(rng) == 2 and 0 <= rng[0] < rng[1] <= 100):
            return "range_pct 须为 [起点百分比, 终点百分比]，0≤起点<终点≤100"
        # no section given: place_front picks the section with most of our own provinces
        sec = next((x for x in secs if x["section"] == order["section"]), None) if "section" in order else None
        own = (sec or {}).get("own_territory_range_pct")
        if sec is not None and own is None:
            return "这一段边境不在本国领土上；前线不能画在别国境内"
        if rng is not None and own and not (rng[0] < own[1] and own[0] < rng[1]):
            return f"这一截不在本国领土上；本国领土是该段的 {own[0]}～{own[1]}%（own_territory_range_pct）"
    if t == "offensive_line":
        path = order.get("path")
        if not (isinstance(path, list) and 1 <= len(path) <= 12 and all(type(x) is int for x in path)):
            return "进攻线路径须为 1～12 个省份编号"
        if not a["fronts"] or not any(f["front_provinces"] for f in a["fronts"]):
            return "该集团军还没有前线，先画前线"
        # a target alone (exam 7, 08-30: [9263] was refused and the army lost its line) or a
        # start that is not on this army's front: apply() anchors the start on the army's own front
        if len(path) >= 2 and path[0] not in enemy_provs:
            return "进攻线起点必须是与我方接壤的敌方省份"
        taken = {f_line["path"][0] for other in pview.get("armies", []) if other["army_id"] != a["army_id"]
                 for f in other["fronts"] for f_line in f["offensive_lines"] if f_line["path"]}
        if len(path) >= 2 and path[0] in taken:
            return "这个起点已被别的集团军的进攻线占用；不同集团军应从不同方向进攻"
    if t == "create_army":
        ids = order.get("unit_ids")
        free = set(pview.get("divisions_not_in_any_army", []))
        if not (isinstance(ids, list) and 1 <= len(ids) <= ARMY_MAX and set(ids) <= free):
            return f"组建集团军须用 1～{ARMY_MAX} 个尚未编入集团军的师"
        # the home-defense garrison may form an army (exam 8: refusing it left the border with an
        # at-war neighbour without any front); the check is at front_line: such an army may only
        # hold a front against the country its garrison faces
    free = {l["leader_id"]: l.get("rank") for l in pview.get("unassigned_leaders", [])}
    if t == "create_army" and order.get("leader_id") is not None:
        if order["leader_id"] not in free:
            return "将领不存在或已有职务"
        if free[order["leader_id"]] != "general":
            return "集团军只能由将军指挥；元帅只能指挥集团军群"
    if t == "create_army_group":
        ids = order.get("army_ids")
        if not (isinstance(ids, list) and 1 <= len(ids) <= 5 and set(ids) <= set(armies)):
            return "集团军群须由 1～5 个现有集团军组成"
        if any(armies[i].get("army_group_id") for i in ids):
            return "其中有集团军已属于别的集团军群"
        if order.get("leader_id") not in free:
            return "集团军群必须指定一位空闲的元帅（unassigned_leaders 中 rank 为 field_marshal）"
        if free[order["leader_id"]] != "field_marshal":
            return "集团军群只能由元帅指挥，不能用将军"
    if t == "promote":
        if order.get("leader_id") not in free:
            return "只能晋升空闲的将领（先免去职务或另选）"
        if free[order["leader_id"]] != "general":
            return "只有将军可以晋升为元帅"
    if t == "appoint":
        if order.get("leader_id") not in free:
            return "将领不存在或已有职务"
        gid = order.get("group_id")
        groups = {g["army_group_id"] for g in pview.get("army_groups", [])}
        if gid in groups:
            if free[order["leader_id"]] != "field_marshal":
                return "集团军群只能由元帅指挥，不能用将军"
        elif gid in armies:
            if free[order["leader_id"]] != "general":
                return "集团军只能由将军指挥；元帅只能指挥集团军群"
        else:
            return "没有这个集团军或集团军群"
    return None


def _remember_front(army_id: int, spec: dict) -> None:
    try:
        data = json.loads(FRONTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {"armies": {}}
    data.setdefault("armies", {})[str(army_id)] = spec
    FRONTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def place_front(s, army_id: int, enemy: str, section, range_pct, unit_ids, live=True, remember=False) -> dict:
    """Front line on one section of the border with `enemy`. Default section: the one with the most
    of our own provinces; default range: our own territory only (no allied / neutral stretch)."""
    import orbat
    me = s.tag(s.player.get("player_index")) if s.player.get("player_index") is not None else None
    rows = orbat.front_sections(s).get(enemy) or []
    if not rows:
        return {"ok": False, "stop": "该国没有边境前线"}
    if section is None:
        row = max(rows, key=lambda r: sum(1 for c in r["controllers"] if c == me))
    else:
        row = next((r for r in rows if r["section"] == section), None)
        if row is None:
            return {"ok": False, "stop": "没有这个前线段"}
    own = orbat.own_range(row["controllers"], me)
    if own is None:
        return {"ok": False, "stop": "这一段前线不在本国领土上，不画"}
    rng = own
    if range_pct:
        # never on another country's soil (exam 8: a range on the far end of a section put two
        # armies' fronts on a neutral neighbour's provinces): clip to our own stretch
        want = (int(range_pct[0] * 1000), int(range_pct[1] * 1000))
        rng = (max(want[0], own[0]), min(want[1], own[1]))
        if rng[0] >= rng[1]:
            return {"ok": False, "stop": f"这一截不在本国领土上；本国领土是该段的 "
                                         f"{round(own[0] / 1000)}～{round(own[1] / 1000)}%"}
    if live:  # one root plan per army: stacking several roots preceded a game crash (2026-11-24)
        for th in orbat.snapshot(s)["theatres"]:
            for g in th["armies"]:
                if g["id"] == army_id:
                    for p in g["plans"]:
                        orbat.delete_plan(army_id, p["plan_id"], live)
    res = orbat.front_line(army_id, row["front_id"], unit_ids, live, start=rng[0], end=rng[1],
                           section=row["section"])
    if res.get("ok") and remember:
        _remember_front(army_id, {"enemy": enemy, "section": row["section"],
                                  "range_pct": [rng[0] / 1000, rng[1] / 1000]})
    res.update(section=row["section"], range=rng)
    return res


CHAIN_MAX = 60  # provinces in one expanded offensive line (game AI lines seen: 1..22)
# "arrow": the commander's points, anchored on the army's own front (drawn by the game as a thrust
# arrow). "chain": every step a land neighbour (drawn as a spiked line = the front to reach).
# Exam 5 (2026-11-25) with "chain": Poland 151 -> 147 in two weeks; the exam-3 A/B had 17
# divisions attacking on a 3-point arrow vs 2 on a chain.
LINE_MODE = "arrow"


def chain_path(s, front_path: list[int], waypoints: list[int], taken=frozenset()) -> list[int] | None:
    """Expand the commander's waypoints into a chain of ADJACENT provinces, as the game's own
    lines are (exam 3, 2026-11-25: a 2-point line [border, capital] is drawn and 'executing' but
    no division ever attacks; the game AI's lines are 5..22 provinces, every step a land
    neighbour). Steps go through enemy-held provinces (any land province only if no such route).
    The chain starts at an enemy province touching this army's own front."""
    nb_cache: dict[int, list[int]] = {}
    ctrl_cache: dict[int, int | None] = {}

    def nbs(p):
        if p not in nb_cache:
            try:
                nb_cache[p] = list(s.land_neighbors(p).get("neighbors") or [])
            except Exception:
                nb_cache[p] = []
        return nb_cache[p]

    def ctrl(p):
        if p not in ctrl_cache:
            try:
                ctrl_cache[p] = s.controller_of(p)
            except Exception:
                ctrl_cache[p] = None
        return ctrl_cache[p]

    front = set(front_path)
    own = {ctrl(p) for p in front_path} - {None}
    enemy = {ctrl(w) for w in waypoints} - own - {None}
    if not enemy:
        return None

    def bfs(starts, goal, allow):
        prev = {x: None for x in starts}
        queue = list(starts)
        i = 0
        while i < len(queue) and len(prev) < 4000:
            x = queue[i]
            i += 1
            if x == goal:
                out = []
                while x is not None:
                    out.append(x)
                    x = prev[x]
                return out[::-1]
            for y in nbs(x):
                if y not in prev and allow(y):
                    prev[y] = x
                    queue.append(y)
        return None

    def leg(starts, goal):
        return (bfs(starts, goal, lambda p: ctrl(p) in enemy)
                or bfs(starts, goal, lambda p: ctrl(p) in enemy or ctrl(p) in own))

    # starts already used by other armies' lines are not entry points: re-anchoring onto one
    # (exam 7, 08-17..08-19) made the commander see an overlap, delete and redraw the same line
    # every tick, so the army never advanced
    entry = sorted({y for f in front_path for y in nbs(f) if ctrl(y) in enemy and y not in taken})
    if not entry:
        return None
    first = waypoints[0]
    chain = [first] if first in entry else leg(entry, first)
    if not chain:
        return None
    if LINE_MODE == "arrow":
        # an arrow (spearhead): only make sure it starts at the army's own front; keep the
        # commander's points (a full chain is drawn by the game as a line to hold, not a thrust)
        out = []
        for w in [chain[0]] + [w for w in waypoints if w != chain[0]]:
            if not out or out[-1] != w:  # [6558, 6558] was drawn in exam 7
                out.append(w)
        if len(out) == 1:
            # the target itself faces our front: aim from another facing province next to it,
            # otherwise point on into the enemy province behind it
            side = [y for y in nbs(out[0]) if y in entry and y != out[0]]
            deeper = [y for y in nbs(out[0]) if ctrl(y) in enemy and y not in entry]
            out = [side[0], out[0]] if side else (out + deeper[:1])
        return out[:12] if len(out) >= 2 else None
    for w in waypoints[1:]:
        if w == chain[-1]:
            continue
        part = leg([chain[-1]], w)
        if not part:
            return None
        chain += part[1:]
    # the line must open on an enemy province next to the front
    while chain and not (ctrl(chain[0]) in enemy and front & set(nbs(chain[0]))):
        chain.pop(0)
    return chain[:CHAIN_MAX] if len(chain) >= 1 else None


def apply(order: dict, pview: dict, live: bool = True) -> dict:
    import orbat
    t = order["type"]
    armies = {a["army_id"]: a for a in pview.get("armies", [])}
    s = _session()
    snap = orbat.snapshot(s)
    units_of = {a["id"]: a["unit_ids"] for th in snap["theatres"] for a in th["armies"]}
    if t == "front_line":
        return place_front(s, order["army_id"], order["enemy"], order.get("section"), order.get("range_pct"),
                           units_of.get(order["army_id"], []), live, remember=True)
    if t == "offensive_line":
        a = armies[order["army_id"]]
        front = max(a["fronts"], key=lambda f: f["front_provinces"])
        if order.get("front_plan_id") is not None:  # a given segment of a split front
            front = next((f for f in a["fronts"] if f["plan_id"] == order["front_plan_id"]), front)

        def line_ids():
            return {c["plan_id"] for th in orbat.snapshot(s)["theatres"] for g in th["armies"]
                    if g["id"] == order["army_id"] for p in g["plans"] for c in p["children"]}
        before = line_ids()
        root = next((p for th in snap["theatres"] for g in th["armies"] if g["id"] == order["army_id"]
                     for p in g["plans"] if p["plan_id"] == front["plan_id"]), None)
        taken = {c["path"][0] for th in snap["theatres"] for g in th["armies"] if g["id"] != order["army_id"]
                 for p in g["plans"] for c in p["children"] if c.get("path")}
        chain = chain_path(s, (root or {}).get("path") or [], order["path"], taken)
        if not chain and str(order.get("reason") or "").startswith("系统"):
            # a segment cut off from the army's target (it faces a pocket): aim it at the enemy
            # province it faces, so its divisions fight instead of standing idle
            seg = (root or {}).get("path") or []
            facing = []
            for f_ in seg:
                try:
                    nb_ = s.land_neighbors(f_).get("neighbors") or []
                except Exception:
                    nb_ = []
                for y in nb_:
                    c_ = s.controller_of(y)
                    if y not in taken and y not in facing and c_ is not None and s.at_war_with(c_):
                        facing.append(y)
            for y in facing[:3]:
                chain = chain_path(s, seg, [y], taken)
                if chain:
                    break
        if not chain:
            return {"ok": False, "stop": "该集团军前线对面没有可用的起点（可能都已被别的集团军的进攻线占用），"
                                         "或无法沿相邻的敌方省份连到目标；调整前线范围或换目标"}
        res = orbat.offensive_line(order["army_id"], front["plan_id"], chain,
                                   units_of.get(order["army_id"], []), live)
        res["chain"] = chain
        if res.get("ok") and live and not (line_ids() - before):  # posted, but the engine dropped it
            res.update(ok=False, stop="游戏没有接受这条进攻线（起点可能已被攻占，或路径不全在敌境内）")
        return res
    if t == "delete_offensive_line":
        return orbat.delete_plan(order["army_id"], order["plan_id"], live)
    if t == "execute":
        # whole-army execute (plan id 0), like the UI button; per-plan execute never moved a division
        r = orbat.execute(order["army_id"], 0, bool(order.get("on", True)), live=live)
        res = {"ok": bool(r.get("ok")), "results": [r.get("ok")]}
        if res["ok"] and live:
            subs = [x for th in orbat.snapshot(s)["theatres"] for g in th["armies"] if g["id"] == order["army_id"]
                    for p in g["plans"] for x in p.get("sub_executing", [])]
            if bool(order.get("on", True)) and subs and not all(subs):
                res.update(ok=False, stop="执行命令已下达，但挂着部队的计划实例没有进入执行状态")
        return res
    if t == "create_army":
        before = set(units_of)
        res = orbat.create_army(snap["theatres"][0]["id"], order["unit_ids"], live)
        new = [a["id"] for th in orbat.snapshot(s)["theatres"] for a in th["armies"] if a["id"] not in before]
        if res.get("ok") and new and order.get("leader_id"):
            res["appoint"] = orbat.appoint(order["leader_id"], new[0], live).get("ok")
            if res["appoint"] and live:
                _pend(order["leader_id"], new[0])
        res["army_id"] = new[0] if new else None
        return res
    if t == "create_army_group":
        before = {g["id"] for th in snap["theatres"] for g in th["army_groups"]}
        res = orbat.create_army_group(snap["theatres"][0]["id"], order["army_ids"], live)
        new = [g["id"] for th in orbat.snapshot(s)["theatres"] for g in th["army_groups"] if g["id"] not in before]
        if res.get("ok") and new and order.get("leader_id"):
            res["appoint"] = orbat.appoint(order["leader_id"], new[0], live).get("ok")
            if res["appoint"] and live:
                _pend(order["leader_id"], new[0])
        res["army_group_id"] = new[0] if new else None
        return res
    def leader_now(lid):
        return next((l for l in orbat.snapshot(s)["leaders"] if l["leader_id"] == lid), {})
    if t == "appoint":
        res = orbat.appoint(order["leader_id"], order["group_id"], live)
        if res.get("ok") and live and leader_now(order["leader_id"]).get("assigned_group") != order["group_id"]:
            res.update(ok=False, stop="游戏没有接受这次任命")
        elif res.get("ok") and live:  # checked again next tick: the game may revoke it
            data = _load_unavailable()
            data.setdefault("pending_appointments", {})[str(order["leader_id"])] = {"group_id": order["group_id"]}
            _save_unavailable(data)
        return res
    if t == "promote":
        res = orbat.promote(order["leader_id"], live)
        if res.get("ok") and live and leader_now(order["leader_id"]).get("rank") != "field_marshal":
            res.update(ok=False, stop="晋升没有生效（可能指挥点数不足）")
        return res
    return {"ok": False, "stop": "UNKNOWN"}
