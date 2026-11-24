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
         "create_army_group", "appoint")
MAX_PER_TICK = 12
ARMY_MAX = 24
FRONTS_FILE = HERE / "tables" / "army_fronts.json"


def _session():
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import live_trial as lt
    return lt.Session(check_sha=False)


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
                               "divisions_on_plan": p["members"], "executing": bool(p["can_execute"]),
                               "offensive_lines": [{"plan_id": c["plan_id"], "path": c["path"]} for c in p["children"]]})
            lead = leader_info.get(a["leader_id"], {})
            armies.append({"army_id": a["id"], "name": a["name"], "army_group_id": a.get("army_group_id"),
                           "leader": lead.get("name") or a["leader_id"], "leader_skill": lead.get("skill"),
                           "divisions": len(a["unit_ids"]), "kinds": kinds,
                           "avg_org": round(sum((units.get(u, {}).get("organization") or 0) for u in a["unit_ids"])
                                            / max(1, len(a["unit_ids"])), 1),
                           "fronts": fronts})
        for g in t["army_groups"]:
            lead = leader_info.get(g["leader_id"], {})
            groups.append({"army_group_id": g["id"], "name": g["name"], "army_ids": g.get("army_ids"),
                           "leader": lead.get("name") or g["leader_id"]})
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
                     "skill": (leader_info.get(lid) or {}).get("skill")}
                    for lid, l in leaders_live.items() if not l["assigned_group"]]
    me = ((doc.get("meta") or {}).get("player_country") or {}).get("tag")
    sections = {}
    try:
        import orbat
        for tag, rows in orbat.front_sections(s).items():
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
            "border_fronts": {k: v for k, v in fronts.items() if k in at_war}}


def validate(order: dict, doc: dict, pview: dict) -> str | None:
    """Return a reason string if the plan order must be refused, else None."""
    t = order.get("type")
    if t not in TYPES:
        return "未知的计划命令类型"
    armies = {a["army_id"]: a for a in pview.get("armies", [])}
    ext = doc.get("_ext") or {}
    enemies = {e["controller"]["tag"] for e in ext.get("enemy_border", []) if e.get("controller")}
    enemy_provs = {e["province_id"]: e["controller"]["tag"] for e in ext.get("enemy_border", []) if e.get("controller")}
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
        rng = order.get("range_pct")
        if rng is not None and not (isinstance(rng, list) and len(rng) == 2 and 0 <= rng[0] < rng[1] <= 100):
            return "range_pct 须为 [起点百分比, 终点百分比]，0≤起点<终点≤100"
    if t == "offensive_line":
        path = order.get("path")
        if not (isinstance(path, list) and 2 <= len(path) <= 12 and all(type(x) is int for x in path)):
            return "进攻线路径须为 2～12 个省份编号"
        if not a["fronts"] or not any(f["front_provinces"] for f in a["fronts"]):
            return "该集团军还没有前线，先画前线"
        if path[0] not in enemy_provs:
            return "进攻线起点必须是与我方接壤的敌方省份"
        taken = {f_line["path"][0] for other in pview.get("armies", []) if other["army_id"] != a["army_id"]
                 for f in other["fronts"] for f_line in f["offensive_lines"] if f_line["path"]}
        if path[0] in taken:
            return "这个起点已被别的集团军的进攻线占用；不同集团军应从不同方向进攻"
    if t == "create_army":
        ids = order.get("unit_ids")
        free = set(pview.get("divisions_not_in_any_army", []))
        if not (isinstance(ids, list) and 1 <= len(ids) <= ARMY_MAX and set(ids) <= free):
            return f"组建集团军须用 1～{ARMY_MAX} 个尚未编入集团军的师"
        # player hard rule: the home defense line keeps its garrison (an army would pull them to its front)
        sections = cv.border_sections(doc)
        count = {p["prov"]: p["divisions"] for s_ in sections if s_["role"] == "home_defense" for p in s_["provinces"]}
        where = {u["unit_id"]: u.get("province_id") for u in (doc.get("world") or {}).get("own_units", [])}
        for uid in ids:
            pv = where.get(uid)
            if pv in count:
                count[pv] -= 1
                if count[pv] < cv.DEFENSE_MIN:
                    return f"会让本土防线省 {pv} 少于 {cv.DEFENSE_MIN} 个师；西线守军不能编进对别国作战的集团军"
    if t == "create_army_group":
        ids = order.get("army_ids")
        if not (isinstance(ids, list) and 1 <= len(ids) <= 5 and set(ids) <= set(armies)):
            return "集团军群须由 1～5 个现有集团军组成"
    if t == "appoint":
        free = {l["leader_id"] for l in pview.get("unassigned_leaders", [])}
        if order.get("leader_id") not in free:
            return "将领不存在或已有职务"
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
    if range_pct:
        rng = (int(range_pct[0] * 1000), int(range_pct[1] * 1000))
    else:
        rng = orbat.own_range(row["controllers"], me)
        if rng is None:
            return {"ok": False, "stop": "这一段前线不在本国领土上，不画"}
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

        def line_ids():
            return {c["plan_id"] for th in orbat.snapshot(s)["theatres"] for g in th["armies"]
                    if g["id"] == order["army_id"] for p in g["plans"] for c in p["children"]}
        before = line_ids()
        res = orbat.offensive_line(order["army_id"], front["plan_id"], order["path"],
                                   units_of.get(order["army_id"], []), live)
        if res.get("ok") and live and not (line_ids() - before):  # posted, but the engine dropped it
            res.update(ok=False, stop="游戏没有接受这条进攻线（起点可能已被攻占，或路径不全在敌境内）")
        return res
    if t == "delete_offensive_line":
        return orbat.delete_plan(order["army_id"], order["plan_id"], live)
    if t == "execute":
        a = armies[order["army_id"]]
        res = {"ok": True, "results": []}
        for f in a["fronts"]:
            r = orbat.execute(order["army_id"], f["plan_id"], bool(order.get("on", True)), live=live)
            res["results"].append(r.get("ok"))
            res["ok"] = res["ok"] and bool(r.get("ok"))
        return res
    if t == "create_army":
        before = set(units_of)
        res = orbat.create_army(snap["theatres"][0]["id"], order["unit_ids"], live)
        new = [a["id"] for th in orbat.snapshot(s)["theatres"] for a in th["armies"] if a["id"] not in before]
        if res.get("ok") and new and order.get("leader_id"):
            res["appoint"] = orbat.appoint(order["leader_id"], new[0], live).get("ok")
        res["army_id"] = new[0] if new else None
        return res
    if t == "create_army_group":
        before = {g["id"] for th in snap["theatres"] for g in th["army_groups"]}
        res = orbat.create_army_group(snap["theatres"][0]["id"], order["army_ids"], live)
        new = [g["id"] for th in orbat.snapshot(s)["theatres"] for g in th["army_groups"] if g["id"] not in before]
        if res.get("ok") and new and order.get("leader_id"):
            res["appoint"] = orbat.appoint(order["leader_id"], new[0], live).get("ok")
        res["army_group_id"] = new[0] if new else None
        return res
    if t == "appoint":
        return orbat.appoint(order["leader_id"], order["group_id"], live)
    return {"ok": False, "stop": "UNKNOWN"}
