"""decide() with a large-language-model brain (DeepSeek, OpenAI-compatible API).

Hybrid design:
  1. decide_v1 rules compute a staff proposal (orders + intents) and the
     deterministic alerts/brief risks.
  2. A compact situation digest + the staff proposal + the hard constraints go
     to the model, which returns the tick's orders, intents and a short brief.
  3. Every model order is checked against the output contract (and later by
     the executor's own pre-checks). Invalid orders are dropped one by one;
     if the reply cannot be used at all, the tick falls back to decide_v1.

Only commands verified end to end on 1.19.5 are allowed: move, attack,
retreat, strategic_redeploy, cancel (current_movement).

The API key is read from the DEEPSEEK_API_KEY environment variable (process
environment first, then the Windows user environment in the registry). It is
never logged. Each call is archived (digest, reply, verdict) under
research/claude_live/llm/.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import commander_view as cv  # noqa: E402
import decide_v0  # noqa: E402
import decide_v1  # noqa: E402
import importlib  # noqa: E402
import generalissimo_output as contract  # noqa: E402

VERSION = "decide_llm"
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
TIMEOUT_S = 300
# deepseek-flash thinks by default (effort high) and once spent all 8000 output
# tokens on reasoning with an empty answer. Keep thinking, at a lower effort.
REASONING_EFFORT = os.environ.get("DEEPSEEK_REASONING_EFFORT", "low")  # none|low|high|max
MAX_TOKENS = int(os.environ.get("DEEPSEEK_MAX_TOKENS", "32000"))
STAFF = os.environ.get("COMMANDER_STAFF", "decide_v3")  # rules that write the staff proposal
# "1" = give the model the situation only, no staff proposal (anchoring experiment)
NO_STAFF = os.environ.get("COMMANDER_NO_STAFF", "1") == "1"
INSTRUCTIONS_FILE = HERE / "tables" / "commander_instructions.json"
ALLOWED = ("move", "attack", "retreat", "strategic_redeploy", "cancel")
ARCHIVE = HERE.parent / "research" / "claude_live" / "llm"


def api_key() -> str | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key.strip()
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return str(winreg.QueryValueEx(k, "DEEPSEEK_API_KEY")[0]).strip() or None
    except OSError:
        return None


# Generic operational-level prompt (user 2026-11-25: no campaign-specific text;
# the campaign lives in tables/scenario.json -> player_instructions).
PROMPT_FILE = HERE / "commander_prompt.md"
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")


UNIT_COLUMNS = ["id", "name", "prov", "kind", "org", "army_id", "marching", "combat", "region"]
KEY_TARGETS_PER_ENEMY = 10


def digest(doc: dict) -> dict:
    """Operational digest: one compact row per division (columns), enemies at war,
    the few most valuable targets per enemy, combats in short form."""
    meta, world = doc.get("meta", {}), doc.get("world", {})
    top = (doc.get("_ext") or {}).get("topology") or {}
    reg = top.get("region_of_province") or {}
    units = []
    for u in world.get("own_units", []):
        pid = u.get("province_id")
        units.append([u["unit_id"], decide_v0.label(u), pid, cv.unit_kind(u),
                      round(u.get("organization") or 0),
                      (u.get("formation") or {}).get("army_id"),
                      1 if (u.get("order") or {}).get("path_province_ids") else 0,
                      u.get("combat_id") if u.get("in_combat") else None,
                      reg.get(pid, reg.get(str(pid)))])
    me = (meta.get("player_country") or {}).get("index")
    enemies = sorted({(w[side].get("tag") or str(w[side].get("index")))
                      for w in world.get("wars", []) for side in ("a", "b")
                      if w.get("state") == "at_war" and w[side].get("index") != me
                      and me in (w["a"].get("index"), w["b"].get("index"))})
    return {
        "time": meta.get("game_time"), "player": meta.get("player_country"),
        "player_instructions": (doc.get("policy") or {}).get("instructions"),
        "enemies_at_war": enemies,
        "units_columns": UNIT_COLUMNS, "units": units,
        "provinces": [{"id": p["province_id"], "neighbors": p.get("neighbors", []),
                       "ours": (p.get("controller") or {}).get("index") == me,
                       "terrain": p.get("terrain"), "vp": (p.get("victory_points") or {}).get("value")}
                      for p in world.get("provinces", [])],
        "combats": _combats(doc),
        "front": _front(doc),
        "last_orders": (doc.get("feedback") or {}).get("last_orders", []),
    }


def _combats(doc: dict) -> list[dict]:
    world = doc.get("world") or {}
    view = {c["id"]: c for c in cv.combat_view(doc, remember=bool((doc.get("meta") or {}).get("allow_write")))}
    out = []
    for c in world.get("combats", []):
        row = {"id": c["combat_id"], "prov": c["province_id"],
               "attackers": len(c.get("attacker_unit_ids") or []), "defenders": len(c.get("defender_unit_ids") or [])}
        v = view.get(c["combat_id"]) or {}
        for k in ("we_attack", "ours", "enemy", "trend", "org_change_since_last_tick", "org_damage_total",
                  "days_fighting", "enemy_encircled"):
            if v.get(k) is not None:
                row[k] = v[k]
        out.append(row)
    return out


def _front(doc: dict) -> dict:
    ext = doc.get("_ext") or {}
    if not ext:
        return {}
    info = {e["province_id"]: e for e in ext.get("enemy_border", [])}

    def facing(b, n):
        e = info.get(n) or {}
        row = {"prov": n, "owner": (e.get("controller") or {}).get("tag")}
        for k in ("terrain", "fort_level"):
            if e.get(k) is not None:
                row[k] = e[k]
        if e.get("victory_points"):
            row["vp"] = e["victory_points"]
        if n in (b.get("river_crossing_to") or []):
            row["river"] = True
        return row
    return {
        "own_border": [{"prov": b["province_id"], "neighbors": b.get("neighbors", []),
                        "facing": [facing(b, n) for n in b.get("enemy_neighbors", [])]}
                       for b in ext.get("own_border", [])],
        "sections": cv.border_sections(doc),
        "near_closed": (ext.get("topology") or {}).get("near_closed", []),
        "enemy_pockets": (ext.get("topology") or {}).get("enemy_pockets", []),
        "enemy_provinces": ext.get("enemy_controlled_provinces", {}),
        "own_provinces": ext.get("own_controlled_provinces"),
        "regions": [{"region": r["region"], "provinces": r["provinces"], "border_provinces": r["border_provinces"]}
                    for r in (ext.get("topology") or {}).get("regions", [])],
        "key_targets": _target_costs(doc, _top_targets((ext.get("topology") or {}).get("key_targets", []))),
        "surrender": _surrender(doc),
        "forces": _forces(doc),
    }


PLAN_FILE = HERE / "tables" / "campaign_plan.json"
PLAN_HISTORY = 5
PLAN_MAX_AGE_DAYS = 20


def _game_dt(doc: dict) -> datetime | None:
    t = (doc.get("meta") or {}).get("game_time") or {}
    try:
        return datetime(int(t["year"]), int(t["month"]), int(t["day"]), int(t.get("hour") or 0) % 24)
    except (KeyError, TypeError, ValueError):
        return None


def _load_plan(doc: dict) -> dict | None:
    """The commander's own campaign plan from an earlier beat (it has no memory between
    calls: exam 7 kept overturning its own main effort). Ignored if written 'in the future'
    (an earlier save was reloaded)."""
    try:
        stored = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    now = _game_dt(doc)
    try:
        written = datetime.fromisoformat(stored["written_at"])
    except (KeyError, TypeError, ValueError):
        return None
    if now is None or written > now or (now - written).days > PLAN_MAX_AGE_DAYS:
        return None  # an earlier save reloaded, or a plan left over from another run
    return stored


def _save_plan(doc: dict, reply: dict) -> None:
    cp = reply.get("campaign_plan")
    if not isinstance(cp, dict) or not cp:
        return  # no new plan: the old one stays in force
    now = _game_dt(doc)
    if now is None:
        return
    old = _load_plan(doc) or {}
    # each group keeps the date its main target was first set, so "how long have we been at it"
    # survives the plan being re-sent every beat
    since = {(str(g.get("army_group")), g.get("main_target")): g.get("since")
             for g in (old.get("plan") or {}).get("groups") or [] if isinstance(g, dict)}
    for g in cp.get("groups") or []:
        if isinstance(g, dict):
            g["since"] = since.get((str(g.get("army_group")), g.get("main_target"))) or now.strftime("%m-%d")
    history = list(old.get("changes") or [])
    change = reply.get("plan_change")
    if isinstance(change, dict) and change:
        history.append({"at": now.isoformat(), **{k: str(v)[:200] for k, v in change.items()}})
    PLAN_FILE.write_text(json.dumps({"written_at": now.isoformat(), "plan": cp,
                                     "changes": history[-PLAN_HISTORY:]},
                                    ensure_ascii=False, indent=2), encoding="utf-8")


def _plan_targets(cp) -> list[int]:
    out: list[int] = []
    for g in (cp or {}).get("groups") or []:
        if not isinstance(g, dict):
            continue
        for k in ("main_target", "next_targets"):
            v = g.get(k)
            for x in (v if isinstance(v, list) else [v]):
                if type(x) is int and x not in out:
                    out.append(x)
    return out[:20]


def _plan_view(doc: dict, combats: list[dict], pview: dict | None = None) -> dict | None:
    """Last beat's plan as written, plus facts the program computes for each target in it:
    taken or not, our combats there and how they go, the visible defenders' organisation,
    days left to the date the commander expected."""
    stored = _load_plan(doc)
    if not stored:
        return None
    now = _game_dt(doc)
    written = datetime.fromisoformat(stored["written_at"])
    world = doc.get("world") or {}
    me = ((doc.get("meta") or {}).get("player_country") or {}).get("index")
    ours = {p["province_id"] for p in world.get("provinces", []) if (p.get("controller") or {}).get("index") == me}
    ext = doc.get("_ext") or {}
    enemy = {t["province_id"] for t in (ext.get("topology") or {}).get("key_targets", [])}
    enemy |= {e["province_id"] for e in ext.get("enemy_border", [])}
    status = []
    for pid in _plan_targets(stored.get("plan")):
        row: dict = {"target": pid}
        row["taken"] = True if pid in ours else (False if pid in enemy else None)
        here = [c for c in combats if c.get("prov") == pid]
        if here:
            row["our_combats_here"] = len(here)
            row["our_divisions_fighting_here"] = sum((c.get("ours") or {}).get("n") or 0 for c in here)
            days = [c["days_fighting"] for c in here if c.get("days_fighting") is not None]
            if days:
                row["days_fighting_here"] = max(days)
            if any(c.get("enemy_encircled") for c in here):
                row["enemy_encircled"] = True
            trends = [c.get("trend") for c in here if c.get("trend")]
            if trends:
                row["combat_trend"] = max(set(trends), key=trends.count)
        orgs = [u.get("organization") or 0 for u in world.get("visible_units", [])
                if u.get("province_id") == pid and u.get("relation_to_player") == "enemy"]
        if orgs:
            row["enemy_divisions_seen"] = len(orgs)
            row["enemy_org_avg"] = round(sum(orgs) / len(orgs))
        # the lines aimed at this target: provinces still to go and since when no progress
        lines = [l for a in (pview or {}).get("armies", []) for f in a.get("fronts", [])
                 for l in f.get("offensive_lines", []) if (l.get("path") or [None])[-1] == pid]
        if lines:
            row["lines_aimed_here"] = len(lines)
            togo = [l["provinces_to_target"] for l in lines if l.get("provinces_to_target") is not None]
            if togo:
                row["provinces_to_go"] = min(togo)
            stuck = [l["no_progress_since"] for l in lines if l.get("no_progress_since")]
            if stuck:
                row["no_progress_since"] = min(stuck)
        for g in (stored.get("plan") or {}).get("groups") or []:
            if isinstance(g, dict) and g.get("main_target") == pid and isinstance(g.get("since"), str):
                try:
                    m, d = (int(x) for x in g["since"].split("-")[-2:])
                    row["days_on_target"] = (now - datetime(now.year, m, d)).days
                except (ValueError, TypeError):
                    pass
            if isinstance(g, dict) and g.get("main_target") == pid and isinstance(g.get("expected_by"), str):
                try:
                    m, d = (int(x) for x in g["expected_by"].split("-")[-2:])
                    row["days_to_expected"] = (datetime(now.year, m, d) - now).days
                except (ValueError, TypeError):
                    pass
        status.append(row)
    return {"written_at": stored["written_at"][:13].replace("T", " ") + "h",
            "days_since": round((now - written).total_seconds() / 86400, 1),
            "plan": stored.get("plan"), "recent_changes": stored.get("changes") or [],
            "status": status}


def _surrender(doc: dict) -> dict:
    """Surrender progress of the enemies that matter here: the scenario's primary targets,
    enemies we share a land border with, and any enemy already losing ground."""
    ext = doc.get("_ext") or {}
    rows = ext.get("surrender") or {}
    bordering = {(e.get("controller") or {}).get("tag") for e in ext.get("enemy_border", [])}
    primary = set(getattr(cv, "PRIMARY_TARGETS", None) or [])
    return {t: r for t, r in rows.items()
            if t in primary or t in bordering or (r.get("progress_pct") or 0) > 0}


def _target_costs(doc: dict, targets: list[dict]) -> list[dict]:
    """Facts for weighing each key target: what taking it is worth (surrender_gain_pct)
    against what it costs (terrain, fort, our divisions next to it, enemy divisions seen in it).
    Enemy divisions are only visible in combats with us; 0 seen does not mean undefended."""
    world = doc.get("world") or {}
    provs = {p["province_id"]: p for p in world.get("provinces", [])}
    border = {e["province_id"]: e for e in (doc.get("_ext") or {}).get("enemy_border", [])}
    at: dict = {}
    for u in world.get("own_units", []):
        at[u.get("province_id")] = at.get(u.get("province_id"), 0) + 1
    seen: dict = {}
    for u in world.get("visible_units", []):
        if u.get("relation_to_player") == "enemy":
            seen[u.get("province_id")] = seen.get(u.get("province_id"), 0) + 1
    fighting = {c.get("province_id") for c in world.get("combats", [])}
    rev: dict = {}  # enemy province -> our provinces that border it (enemy rows carry no neighbours)
    for q in world.get("provinces", []):
        for n in q.get("neighbors") or []:
            rev.setdefault(n, set()).add(q["province_id"])
    out = []
    for t in targets:
        row = dict(t)
        pid = t.get("province_id")
        p, b = provs.get(pid) or {}, border.get(pid) or {}
        for k in ("terrain", "fort_level"):
            v = b.get(k, p.get(k))
            if v is not None:
                row[k] = v
        nbs = set(p.get("neighbors") or []) | rev.get(pid, set())
        if nbs:
            row["our_divisions_adjacent"] = sum(at.get(n, 0) for n in nbs)
        # only a positive sighting is a fact; "0 seen" was read as "no defenders" (exam 7, 09-11:
        # the capital was called undefended and four armies were sent at it)
        if seen.get(pid):
            row["enemy_divisions_seen"] = seen[pid]
        else:
            row["defenders"] = "unknown"
        if pid in fighting:
            row["combat_here"] = True
        out.append(row)
    return out


def _top_targets(targets: list[dict]) -> list[dict]:
    by: dict = {}
    for t in sorted(targets, key=lambda t: (-t.get("victory_points", 0), t.get("hops_from_our_land", 99))):
        rows = by.setdefault(t.get("owner"), [])
        if len(rows) < KEY_TARGETS_PER_ENEMY:
            rows.append(t)
    # the scenario's primary targets first (exam 6: France's bigger victory points led the list
    # while the campaign was against Poland)
    primary = list(getattr(cv, "PRIMARY_TARGETS", None) or [])
    order = sorted(by, key=lambda o: (primary.index(o) if o in primary else len(primary), str(o)))
    return [t for o in order for t in by[o]]


def _forces(doc: dict) -> list[dict]:
    """Per land region: how many divisions fight, march, or stand idle (and how
    fresh / how far from the front the idle ones are)."""
    ext = doc.get("_ext") or {}
    top = ext.get("topology") or {}
    reg = top.get("region_of_province") or {}
    hops = top.get("hops_to_border") or {}
    watch = set(ext.get("own_watch_border", []))
    rows: dict = {}
    for u in (doc.get("world") or {}).get("own_units", []):
        pid = u.get("province_id")
        r = reg.get(pid, reg.get(str(pid)))
        row = rows.setdefault(r, {"region": r, "fighting": 0, "marching": 0, "idle": 0,
                                  "idle_fresh_org60": 0, "idle_on_watch_border": 0,
                                  "idle_hops_to_front": {}})
        if u.get("in_combat"):
            row["fighting"] += 1
        elif (u.get("order") or {}).get("path_province_ids"):
            row["marching"] += 1
        else:
            row["idle"] += 1
            row["idle_fresh_org60"] += (u.get("organization") or 0) >= 60
            row["idle_on_watch_border"] += pid in watch
            h = hops.get(pid, hops.get(str(pid)))
            key = "unknown" if h is None else ("0" if h == 0 else "1-3" if h <= 3 else "4-10" if h <= 10 else ">10")
            row["idle_hops_to_front"][key] = row["idle_hops_to_front"].get(key, 0) + 1
    return [rows[k] for k in sorted(rows, key=lambda x: (x is None, x))]


def _instructions() -> str | None:
    if cv.SCENARIO.get("instructions"):
        return cv.SCENARIO["instructions"]
    try:
        return json.loads(INSTRUCTIONS_FILE.read_text(encoding="utf-8")).get("instructions")
    except (OSError, ValueError):
        return None


def _call(messages: list[dict], key: str, retries: int = 3, effort: str | None = None) -> dict:
    """POST with one retry on transport errors (no game effect, so retrying is safe)."""
    import http.client
    last = None
    for attempt in range(retries + 1):
        try:
            return _call_once(messages, key, effort or REASONING_EFFORT)
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError, OSError) as e:
            last = e
            if attempt < retries:
                time.sleep(10 * 2 ** attempt)  # 10, 20, 40 s: rides out short network drops
    raise last


def _call_once(messages: list[dict], key: str, effort: str) -> dict:
    """Streamed request, assembled into the usual non-stream response shape. A non-streamed
    request sits silent for minutes while the model thinks, and the link cut it (exams 7 and 9:
    SSL UNEXPECTED_EOF on the thinking calls, the quick no-thinking retry got through)."""
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.3,
                       "response_format": {"type": "json_object"}, "max_tokens": MAX_TOKENS,
                       "reasoning_effort": effort, "stream": True,
                       "stream_options": {"include_usage": True}}).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
        "Accept": "text/event-stream"})
    content, finish, usage = [], None, None
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content")
                if piece:
                    content.append(piece)
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    return {"choices": [{"message": {"content": "".join(content)}, "finish_reason": finish}],
            "usage": usage}


def _to_contract(order: dict, seq: int) -> dict | None:
    t = order.get("type")
    uid = order.get("unit_id")
    if t not in ALLOWED or type(uid) is not int:
        return None
    out = {"order_seq": seq, "type": t, "subject": {"unit_ids": [uid]}}
    if order.get("reason"):
        out["reason"] = str(order["reason"])[:200]
    if t == "cancel":
        out["cancel_scope"] = "current_movement"
        return out
    tgt = order.get("target")
    if type(tgt) is not int:
        return None
    out["to_province_ids" if t == "retreat" else "target_province_ids"] = [tgt]
    return out


def decide(input_doc: dict) -> dict:
    if not (input_doc.get("policy") or {}).get("instructions"):
        text = _instructions()
        if text:
            input_doc.setdefault("policy", {})["instructions"] = text
    rules = importlib.import_module(STAFF).decide(input_doc)
    meta = input_doc.get("meta", {}) or {}
    if meta.get("allow_write") is not True:
        return rules  # observation-only ticks never spend tokens
    key = api_key()
    if not key:
        rules.setdefault("brief", {}).setdefault("risks", []).append("未配置 DEEPSEEK_API_KEY，本拍按规则决策")
        return rules
    dig = digest(input_doc)
    import plan_orders as po
    pview = po.view(input_doc)
    dig["order_of_battle"] = pview
    dig["last_plan_orders"] = (input_doc.get("feedback") or {}).get("last_plan_orders", [])
    try:
        dig["last_assaults"] = json.loads(ASSAULT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        dig["last_assaults"] = []
    try:
        dig["your_campaign_plan"] = _plan_view(input_doc, dig.get("combats") or [], pview)
    except Exception as e:  # never block a beat on this
        dig["your_campaign_plan"] = {"error": type(e).__name__}
    proposal = [{"type": o["type"], "unit_id": o["subject"]["unit_ids"][0],
                 "target": (o.get("target_province_ids") or o.get("to_province_ids") or [None])[0],
                 "reason": o.get("reason")} for o in rules["orders"]]
    payload = {"situation": dig} if NO_STAFF else {"situation": dig, "staff_proposal": proposal}
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
    record = {"at": datetime.now().isoformat(timespec="seconds"), "model": MODEL,
              "digest": dig, "staff_proposal": proposal}
    t0 = time.time()
    plan, attempts = None, []
    # deepseek-flash once spent all 32000 output tokens thinking and returned no answer;
    # then retry once with less thinking.
    for effort in (REASONING_EFFORT, "none"):
        try:
            resp = _call(messages, key, effort=effort)
            choice = resp["choices"][0]
            text = choice["message"]["content"]
            attempts.append({"effort": effort, "usage": resp.get("usage"),
                             "finish_reason": choice.get("finish_reason")})
            record["reply"] = text
            plan = json.loads(text)
            break
        except Exception as e:
            attempts.append({"effort": effort, "error": f"{type(e).__name__}: {e}"[:300]})
    record["latency_s"] = round(time.time() - t0, 1)
    record["attempts"] = attempts
    record["usage"] = next((x["usage"] for x in reversed(attempts) if x.get("usage")), None)
    if plan is None:
        # No commander decision this beat: keep every current plan running and give no
        # per-division orders (the rule staff used to send ~95 micro orders here), only
        # the home-defense fill-ins required by the player's hard rule.
        record["error"] = attempts[-1].get("error")
        kept, _, added = home_defense_guard([], input_doc, rules)
        _archive(record)
        out = {"orders": kept, "alerts": rules["alerts"], "intents": []}
        if added:
            out["intents"].append({"intent_id": "home-defense", "kind": "hold_line",
                                   "subject": {"unit_ids": [o["subject"]["unit_ids"][0] for o in added]},
                                   "expands_to_order_seqs": [o["order_seq"] for o in added],
                                   "notes": "按玩家硬性要求补齐本土防线"})
        brief = dict(rules.get("brief") or {})
        if brief:
            brief["summary"] = "总司令本次没有给出决定，维持现有计划不变"
            brief["risks"] = [f"大模型两次都没有给出可用答复（{record['error']}）"]
            out["brief"] = brief
        return out

    try:
        _save_plan(input_doc, plan)
    except Exception as e:
        record["plan_save_error"] = type(e).__name__
    out = {"orders": [], "alerts": rules["alerts"], "intents": []}
    dropped = []
    accepted_plans = []
    projected = json.loads(json.dumps(pview))  # orders of one reply build on each other
    for raw in (plan.get("plan_orders") or [])[:po.MAX_PER_TICK] if isinstance(plan.get("plan_orders"), list) else []:
        if isinstance(raw, dict):
            _army_by_name(raw, projected)
        why = po.validate(raw, input_doc, projected) if isinstance(raw, dict) else "格式错误"
        if why:
            dropped.append({"order": raw, "why": why})
        else:
            accepted_plans.append(raw)
            _project(projected, raw)
    # Deleting an army's lines stops its execution in the game; a redraw without a new execute
    # left two healthy armies idle for a beat (exam 8, 08-27). If the army was attacking and the
    # commander did not order it to stop, keep it attacking after the redraw.
    was_exec = {a["army_id"] for a in po.formations(pview).values() if any(f.get("executing") for f in a.get("fronts", []))}
    redrawn = [o["army_id"] for o in accepted_plans if o.get("type") == "offensive_line"]
    told = {o["army_id"] for o in accepted_plans if o.get("type") == "execute"}
    for aid in dict.fromkeys(redrawn):
        if aid in was_exec and aid not in told and len(accepted_plans) < po.MAX_PER_TICK + 6:
            o = {"type": "execute", "army_id": aid, "on": True, "reason": "系统：重画进攻线后保持进攻"}
            if not po.validate(o, input_doc, projected):
                accepted_plans.append(o)
                _project(projected, o)
                told.add(aid)
    # The game splits a front after an encirclement; the new segment has no line and its
    # divisions stand idle (exam 8: 24 divisions, 1 attacking). Restore the commander's intent:
    # aim the segment at the target of that army's own line. Armies the commander re-fronts
    # this beat are left alone.
    touched = {o["army_id"] for o in accepted_plans if o.get("type") in ("front_line", "delete_offensive_line")}
    for a in list(po.formations(projected).values()):  # after this reply's own orders; army groups too
        if a["army_id"] in touched:
            continue
        aims = [l["path"][-1] for f in a.get("fronts", []) for l in f.get("offensive_lines", []) if l.get("path")]
        bare = [f for f in a.get("fronts", []) if f.get("front_provinces") and not f.get("offensive_lines")]
        if not aims or not bare:
            continue
        for f in bare:
            o = {"type": "offensive_line", "army_id": a["army_id"], "front_plan_id": f["plan_id"],
                 "path": [aims[0]], "reason": "系统：被拆出的前线段补线，指向本集团军已有的目标"}
            if not po.validate(o, input_doc, projected):
                accepted_plans.append(o)
                _project(projected, o)
        if a["army_id"] in was_exec and a["army_id"] not in told:
            o = {"type": "execute", "army_id": a["army_id"], "on": True, "reason": "系统：补线后保持进攻"}
            if not po.validate(o, input_doc, projected):
                accepted_plans.append(o)
                _project(projected, o)
                told.add(a["army_id"])
    # An army whose front vanished (the enemy land in front of it was taken, the game drops the
    # front) stands idle until redrawn; exam 9 had 23 divisions so for two weeks. Give it a front
    # again against the country it fought (or the scenario's primary target); lines stay the
    # commander's choice.
    try:
        remembered = json.loads(po.FRONTS_FILE.read_text(encoding="utf-8")).get("armies", {})
    except (OSError, ValueError, AttributeError):
        remembered = {}
    fronted = {o["army_id"] for o in accepted_plans if o.get("type") == "front_line"}
    at_war = set((pview.get("border_fronts") or {}).keys())
    group_fronted = {i for g in projected.get("army_groups", []) if any(f.get("front_provinces") for f in g.get("fronts", []))
                     for i in (g.get("army_ids") or [])}
    for a in projected.get("armies", []):
        if not a.get("divisions") or a["army_id"] in fronted or a["army_id"] in group_fronted                 or any(f.get("front_provinces") for f in a.get("fronts", [])):
            continue  # an army inside a group that holds the front needs no front of its own
        enemy = (remembered.get(str(a["army_id"])) or {}).get("enemy")
        if enemy not in at_war:
            enemy = next((t for t in sorted(cv.PRIMARY_TARGETS) if t in at_war), None)
        if not enemy:
            continue
        o = {"type": "front_line", "army_id": a["army_id"], "enemy": enemy, "section": "near_units",
             "reason": "系统：集团军没有前线，按原来的作战对象、在它的师所在的那段边境重画"}
        if not po.validate(o, input_doc, projected):
            accepted_plans.append(o)
            _project(projected, o)
    input_doc["_plan_orders"] = {"orders": accepted_plans, "view": pview}
    record["accepted_plan_orders"] = accepted_plans
    seq = 0
    raw_orders = list(plan.get("orders") or []) if isinstance(plan.get("orders"), list) else []
    assault_report = []
    if isinstance(plan.get("assaults"), list):
        extra, assault_report = expand_assaults(input_doc, plan["assaults"][:ASSAULTS_MAX],
                                                busy={o.get("unit_id") for o in raw_orders if isinstance(o, dict)})
        raw_orders += extra
    record["assaults"] = assault_report
    try:  # shown to the commander next beat as last_assaults
        ASSAULT_FILE.write_text(json.dumps(assault_report, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    for raw in raw_orders:
        cand = _to_contract(raw if isinstance(raw, dict) else {}, seq + 1)
        if cand is None:
            dropped.append({"order": raw, "why": "格式或类型不允许"})
            continue
        trial = {"orders": out["orders"] + [cand], "alerts": [], "intents": []}
        errs = contract.validate_output(trial, input_doc)
        if errs:
            dropped.append({"order": raw, "why": errs[0]["message"]})
            continue
        seq += 1
        out["orders"].append(cand)
    if out["orders"]:
        out["intents"].append({"intent_id": "llm-1", "kind": "custom",
                               "subject": {"unit_ids": sorted({o["subject"]["unit_ids"][0] for o in out["orders"]})},
                               "expands_to_order_seqs": [o["order_seq"] for o in out["orders"]],
                               "notes": str(plan.get("intent") or "")[:300]})
    brief = dict(rules.get("brief") or {})
    if brief:
        summary = str(plan.get("summary") or "").strip()
        if summary:
            brief["summary"] = f"【大模型】{summary[:500]}"
        risks = [str(r)[:200] for r in plan.get("risks", []) if isinstance(r, str)][:6]
        brief["risks"] = risks + (rules["brief"].get("risks") or [])
        if dropped:
            brief["risks"].append(f"大模型有 {len(dropped)} 条命令不合规，已剔除")
        out["brief"] = brief
    out["orders"], guard_dropped, added = home_defense_guard(out["orders"], input_doc, rules)
    dropped.extend(guard_dropped)
    if added:
        out["intents"].append({"intent_id": "home-defense", "kind": "hold_line",
                               "subject": {"unit_ids": [o["subject"]["unit_ids"][0] for o in added]},
                               "expands_to_order_seqs": [o["order_seq"] for o in added],
                               "notes": "按玩家硬性要求补齐本土防线"})
        if out.get("brief"):
            out["brief"]["risks"].append(f"本土防线不足，系统按参谋方案补调 {len(added)} 个师")
    before = {o["order_seq"] for o in out["orders"]}
    out = decide_v1._drop_repeated_failures(out, input_doc.get("feedback") or {})
    for o in out_orders_dropped(before, out):
        dropped.append({"order": o, "why": "上一拍同一命令被引擎拒绝，不重复"})
    record["accepted_orders"] = out["orders"]
    record["dropped"] = dropped
    final_errs = contract.validate_output(out, input_doc)
    if final_errs:
        record["fallback"] = final_errs
        _archive(record)
        return rules
    _archive(record)
    return out


ASSAULTS_MAX = 4
ASSAULT_FILE = HERE / "tables" / "last_assaults.json"
ASSAULT_DIVISIONS_MAX = 24
ASSAULT_MIN_ORG = 30


def expand_assaults(doc: dict, assaults: list, busy: set | None = None) -> tuple[list[dict], list[dict]]:
    """A concentrated assault: the commander names an enemy province and how many divisions;
    the program picks the nearest fit ones (exam 8: battles had 1..6 divisions while whole armies
    stood along the front). Divisions next to the target attack it; divisions one province
    further move up next to it (they attack on a later beat if the assault is repeated).
    Skipped: divisions in another fight, below ASSAULT_MIN_ORG organisation, or on the home
    defence line."""
    world = doc.get("world") or {}
    me = ((doc.get("meta") or {}).get("player_country") or {}).get("index")
    nbs = {p["province_id"]: set(p.get("neighbors") or []) for p in world.get("provinces", [])}
    ours = {p["province_id"] for p in world.get("provinces", []) if (p.get("controller") or {}).get("index") == me}
    home = {pp["prov"] for sec in cv.border_sections(doc) if sec["role"] == "home_defense" for pp in sec["provinces"]}
    fight_at = {}
    for c in world.get("combats", []):
        for u in (c.get("attacker_unit_ids") or []) + (c.get("defender_unit_ids") or []):
            fight_at[u] = (c.get("province_id"), u in (c.get("attacker_unit_ids") or []))
    used = set(busy or set())
    orders, report = [], []
    for a in assaults:
        if not isinstance(a, dict) or type(a.get("target")) is not int:
            continue
        tgt, want = a["target"], max(1, min(int(a.get("divisions") or 6), ASSAULT_DIVISIONS_MAX))
        reason = str(a.get("reason") or "集中进攻")[:40]
        ring = {q for q in ours if tgt in nbs.get(q, set())}  # our provinces touching the target
        if not ring:
            report.append({"target": tgt, "ok": False, "why": "我方没有与目标相邻的省份"})
            continue
        ring2 = {}  # our provinces one step behind the ring -> a ring province next to them
        for q in ours - ring:
            nxt = sorted(nbs.get(q, set()) & ring)
            if nxt:
                ring2[q] = nxt[0]
        cands = []
        skipped = {"other_fight": 0, "low_org": 0, "home_defense": 0, "already_used": 0}
        for u in world.get("own_units", []):
            uid, pv = u["unit_id"], u.get("province_id")
            if pv not in ring and pv not in ring2:
                continue
            if uid in used:
                skipped["already_used"] += 1
                continue
            if pv in home:
                skipped["home_defense"] += 1
                continue
            if (u.get("organization") or 0) < ASSAULT_MIN_ORG:
                skipped["low_org"] += 1
                continue
            fa = fight_at.get(uid)
            if fa and not (fa[0] == tgt and fa[1]):
                skipped["other_fight"] += 1
                continue  # busy in another fight (already attacking the target is fine)
            if pv in ring:
                cands.append((0, -(u.get("organization") or 0), uid, "attack", tgt))
            elif pv in ring2:
                cands.append((1, -(u.get("organization") or 0), uid, "move", ring2[pv]))
        cands.sort()
        picked = cands[:want]
        for _, _, uid, kind, dest in picked:
            if kind == "attack" and fight_at.get(uid, (None,))[0] == tgt:
                continue  # already attacking it
            orders.append({"type": kind, "unit_id": uid, "target": dest, "reason": f"集中进攻{tgt}：{reason}"[:60]})
            used.add(uid)
        already = sum(1 for c in picked if c[3] == "attack" and fight_at.get(c[2], (None,))[0] == tgt)
        report.append({"target": tgt, "asked": want, "already_attacking": already,
                       "new_attacks": sum(1 for c in picked if c[3] == "attack") - already,
                       "moving_up": sum(1 for c in picked if c[3] == "move"), "ok": bool(picked),
                       "unusable_nearby": {k: v for k, v in skipped.items() if v}})
    return orders, report


def _army_by_name(order: dict, pv: dict) -> None:
    """The model keeps writing the number in an army's name as its id ("第9集团军" as 9; the
    real id was 570, refused, and a 20-division army stood idle for 8 days in exam 9). When the
    id does not exist and exactly one army is named after that number, use that army."""
    ids = {a["army_id"] for a in pv.get("armies", [])}

    def fix(i):
        if i in ids or type(i) is not int:
            return i
        named = [a["army_id"] for a in pv.get("armies", []) if f"第{i}集团军" in (a.get("name") or "")]
        return named[0] if len(named) == 1 else i
    if "army_id" in order:
        order["army_id"] = fix(order["army_id"])
    if isinstance(order.get("army_ids"), list):
        order["army_ids"] = [fix(i) for i in order["army_ids"]]


def _project(pv: dict, o: dict) -> None:
    """Apply an accepted plan order to the projected view so the next order of
    the same reply can rely on it (front -> offensive line -> execute in one beat)."""
    import plan_orders as po
    armies = po.formations(pv)
    t = o.get("type")
    a = armies.get(o.get("army_id"))
    if t == "front_line" and a is not None and not any(f.get("front_provinces") for f in a["fronts"]):
        a["fronts"].append({"plan_id": None, "front_provinces": 1, "offensive_lines": [], "projected": True})
    elif t == "offensive_line" and a is not None and a["fronts"]:
        seg = next((f for f in a["fronts"] if o.get("front_plan_id") is not None
                    and f.get("plan_id") == o["front_plan_id"]), None)
        (seg or max(a["fronts"], key=lambda f: f.get("front_provinces") or 0))["offensive_lines"].append(
            {"plan_id": None, "path": o.get("path"), "projected": True})
    elif t == "delete_offensive_line" and a is not None:
        for f in a["fronts"]:
            f["offensive_lines"] = [l for l in f["offensive_lines"] if l.get("plan_id") != o.get("plan_id")]
    free = pv.get("unassigned_leaders", [])
    if t == "promote":
        for l in free:
            if l["leader_id"] == o.get("leader_id"):
                l["rank"] = "field_marshal"
    if t in ("create_army", "create_army_group", "appoint") and o.get("leader_id") is not None:
        pv["unassigned_leaders"] = [l for l in free if l["leader_id"] != o["leader_id"]]
    if t == "create_army":
        used = set(o.get("unit_ids") or [])
        pv["divisions_not_in_any_army"] = [d for d in pv.get("divisions_not_in_any_army", []) if d not in used]
    if t == "create_army_group":
        for i in o.get("army_ids") or []:
            if i in armies:
                armies[i]["army_group_id"] = -1  # grouped in this reply


LEAVING = ("move", "retreat", "strategic_redeploy")


def home_defense_guard(orders: list[dict], doc: dict, staff: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Player hard rule: home-defense border provinces never drop below
    DEFENSE_MIN divisions. Drops model orders that would strip them, then adds
    the staff's fill-in redeploys for provinces still short."""
    sections = cv.border_sections(doc)
    count = {p["prov"]: p["divisions"] + p["incoming"]
             for s in sections if s["role"] == "home_defense" for p in s["provinces"]}
    if not count:
        return orders, [], []
    where = {u["unit_id"]: u.get("province_id") for u in (doc.get("world") or {}).get("own_units", [])
             if not (u.get("order") or {}).get("path_province_ids")}
    kept, dropped = [], []
    for o in orders:
        uid = o["subject"]["unit_ids"][0]
        src = where.get(uid)
        tgt = (o.get("target_province_ids") or o.get("to_province_ids") or [None])[0]
        if o["type"] in LEAVING and src in count and tgt != src:
            if count[src] - 1 < cv.DEFENSE_MIN:
                dropped.append({"order": o, "why": f"会让本土防线省 {src} 少于 {cv.DEFENSE_MIN} 个师"})
                continue
            count[src] -= 1
        if o["type"] in LEAVING and tgt in count:
            count[tgt] += 1
        kept.append(o)
    added = []
    busy = {o["subject"]["unit_ids"][0] for o in kept}
    seq = max([o["order_seq"] for o in kept], default=0)
    for o in staff.get("orders", []):
        tgt = (o.get("target_province_ids") or [None])[0]
        uid = o["subject"]["unit_ids"][0]
        if (o["type"] == "strategic_redeploy" and tgt in count and count[tgt] < cv.DEFENSE_MIN
                and uid not in busy and where.get(uid) not in count):
            seq += 1
            new = dict(o, order_seq=seq)
            kept.append(new)
            added.append(new)
            busy.add(uid)
            count[tgt] += 1
    return kept, dropped, added


def out_orders_dropped(before: set[int], out: dict) -> list[int]:
    return sorted(before - {o["order_seq"] for o in out["orders"]})


def _archive(record: dict) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("llm_%Y%m%d_%H%M%S.json")
    (ARCHIVE / name).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
