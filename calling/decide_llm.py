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
STAFF = os.environ.get("COMMANDER_STAFF", "decide_v2")  # rules that write the staff proposal
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


SYSTEM_PROMPT = """你是《钢铁雄心4》中玩家国家的陆军总司令。每一拍你会收到当前陆战态势（JSON）、参谋按固定规则给出的建议，以及硬性约束。你要决定本拍对己方陆军下达的命令。

职责与边界：
- 只指挥陆军机动：移动、进攻、撤退、战略转移、取消行军。不碰外交、生产、科研、海空军，也不新建或解散部队。
- 玩家方针原文（player_instructions）是你的最高目标，战略取舍（打谁、守哪里、兵力怎么分配）由你自己判断；参谋建议只是参考，可以全部采纳、修改或否决。
- 方针档位（stance）：annihilate=寻机歼灭敌军；preserve_force=保存兵力优先；hold_line=守住防线；economize_manpower=节约人力。
- 目前可用的只有逐师命令（移动、进攻、撤退、战略转移、取消）；前线和进攻线命令还在验证中，暂不可用。
- 地图拓扑：front.regions 是己方控制领土中互不连通的陆地块（例如本土与被敌国隔开的飞地），own_units[].region 是每个师所在的陆地块，hops_to_front 是它离本块最近边境省隔几个省。战略转移和移动只能在同一陆地块内进行，不同陆地块之间陆路不通。
- front.forces 按陆地块汇总兵力：战斗中、行军中、空闲（其中组织度≥60 的生力军数、守在西线等观察边境上的数量、离前线几个省的分布）。空闲的生力军是可以调动的预备队，是否投入、投向哪里由你决定。
- front.key_targets 是敌方仍控制的胜利点省份（victory_points 分值、hops_from_our_land 为离我方控制区几个省）。迫使一国投降主要靠占领它的胜利点，分值越高越关键；进攻方向应指向这些要地。
- front 给出整条边界：own_border 是与交战国接壤的己方省份及其对面省份和控制国；watch_border 是面对未交战邻国的己方省份；enemy_provinces 是各交战国仍控制的省份数（可用来判断战役进度）。
- 你看到的敌军只是正在与我方交战的部队（战争迷雾）。看不见的地方不要假设敌情。
- 没有必要的命令就不下。空命令是正常的。
- 在 reason、intent、summary、risks 里提到己方部队时，一律用部队名称（own_units[].name），不要写编号；unit_id 字段仍填编号。

硬性约束（违反的命令会被系统直接丢弃）：
- unit_id 只能用 own_units 里存在的师；每条命令只给一个师。
- move / retreat / attack 的目标必须是该师所在省份的相邻省份（provinces[].neighbors 或 front.own_border[].neighbors），strategic_redeploy 可以远距离但只能去己方省份。
- attack 只能打与我方交战的国家控制的省份（敌军所在省份）。retreat 只能撤到不在战斗中的己方省份。
- 不要给已经在行军（order.path_province_ids 非空）的师下新的移动类命令；要改道先用 cancel。
- 正在战斗中的师不能发起进攻；只能留守或撤退。
- 组织度很低（< 15）的师不要投入战斗。
- last_orders 里 accepted=false 的命令是上一拍被引擎拒绝的，不要原样重复（同一个师、同一类命令、同一个目标会被系统直接丢弃）。战略转移被拒（ISVALID_FALSE）通常表示陆路不可达，例如被敌国领土隔开的飞地，应换目标或改用其他办法。

只输出一个 JSON 对象，不要输出任何其他文字，格式：
{
  "orders": [
    {"type": "move|attack|retreat|strategic_redeploy|cancel", "unit_id": 1234, "target": 5678, "reason": "中文简短理由"}
  ],
  "intent": "本拍作战意图，一句中文",
  "summary": "给玩家的态势判断，两三句中文",
  "risks": ["中文风险1", "中文风险2"]
}
cancel 不需要 target。没有命令时 orders 为 []。
回复要精简：只给需要改变行动的师下命令（正在执行合理命令的师不用重复下），每条 reason 不超过 20 个字，summary 不超过 120 字，risks 最多 4 条。"""


def digest(doc: dict) -> dict:
    """Compact view for the model: only what a commander needs, no evidence."""
    meta, world = doc.get("meta", {}), doc.get("world", {})
    units = []
    for u in world.get("own_units", []):
        row = {"id": u["unit_id"], "name": decide_v0.label(u), "prov": u.get("province_id"),
               "org": round(u.get("organization") or 0, 1),
               "hp": round((u.get("strength") or {}).get("current") or 0, 1)}
        if u.get("in_combat"):
            row["combat"] = u.get("combat_id")
        if (u.get("order") or {}).get("path_province_ids"):
            row["route"] = u["order"]["path_province_ids"]
        top = (doc.get("_ext") or {}).get("topology") or {}
        reg = (top.get("region_of_province") or {})
        prov_key = u.get("province_id")
        r_ = reg.get(prov_key, reg.get(str(prov_key)))
        if r_ is not None:
            row["region"] = r_
        h_ = (top.get("hops_to_border") or {})
        h_ = h_.get(prov_key, h_.get(str(prov_key)))
        if h_ is not None:
            row["hops_to_front"] = h_
        if (u.get("supply") or {}).get("in_supply") is False:
            row["low_supply"] = round((u.get("supply") or {}).get("ratio") or 0, 2)
        units.append(row)
    return {
        "time": meta.get("game_time"), "player": meta.get("player_country"),
        "stance": (doc.get("policy") or {}).get("stance", decide_v0.DEFAULT_STANCE),
        "own_units": units,
        "provinces": [{"id": p["province_id"], "neighbors": p.get("neighbors", []),
                       "ours": (p.get("controller") or {}).get("index") == (meta.get("player_country") or {}).get("index"),
                       "terrain": p.get("terrain"), "vp": (p.get("victory_points") or {}).get("value")}
                      for p in world.get("provinces", [])],
        "enemy_visible": [{"id": v["unit_id"], "prov": v.get("province_id"),
                           "owner": (v.get("owner") or {}).get("tag"),
                           "org": round(v.get("organization") or 0, 1),
                           "hp": round((v.get("strength") or {}).get("current") or 0, 1),
                           "combat": v.get("combat_id")}
                          for v in world.get("visible_units", [])],
        "combats": [{"id": c["combat_id"], "prov": c["province_id"],
                     "we_attack": bool(set(c.get("attacker_unit_ids", [])) & {u["id"] for u in units}),
                     "attackers": c.get("attacker_unit_ids"), "defenders": c.get("defender_unit_ids"),
                     "org_loss": c.get("casualties")} for c in world.get("combats", [])],
        "wars": world.get("wars", []),
        "player_instructions": (doc.get("policy") or {}).get("instructions"),
        "front": _front(doc),
        "last_orders": (doc.get("feedback") or {}).get("last_orders", []),
    }


def _front(doc: dict) -> dict:
    ext = doc.get("_ext") or {}
    if not ext:
        return {}
    ctrl = {e["province_id"]: (e.get("controller") or {}).get("tag") for e in ext.get("enemy_border", [])}
    return {
        "own_border": [{"prov": b["province_id"], "neighbors": b.get("neighbors", []),
                        "facing": [{"prov": n, "owner": ctrl.get(n)} for n in b.get("enemy_neighbors", [])]}
                       for b in ext.get("own_border", [])],
        "watch_border": ext.get("own_watch_border", []),
        "enemy_provinces": ext.get("enemy_controlled_provinces", {}),
        "own_provinces": ext.get("own_controlled_provinces"),
        "regions": [{"region": r["region"], "provinces": r["provinces"], "border_provinces": r["border_provinces"]}
                    for r in (ext.get("topology") or {}).get("regions", [])],
        "key_targets": (ext.get("topology") or {}).get("key_targets", []),
        "forces": _forces(doc),
    }


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
    try:
        return json.loads(INSTRUCTIONS_FILE.read_text(encoding="utf-8")).get("instructions")
    except (OSError, ValueError):
        return None


def _call(messages: list[dict], key: str, retries: int = 1) -> dict:
    """POST with one retry on transport errors (no game effect, so retrying is safe)."""
    import http.client
    last = None
    for attempt in range(retries + 1):
        try:
            return _call_once(messages, key)
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError, OSError) as e:
            last = e
            time.sleep(5)
    raise last


def _call_once(messages: list[dict], key: str) -> dict:
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.3,
                       "response_format": {"type": "json_object"}, "max_tokens": MAX_TOKENS,
                       "reasoning_effort": REASONING_EFFORT}).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
    proposal = [{"type": o["type"], "unit_id": o["subject"]["unit_ids"][0],
                 "target": (o.get("target_province_ids") or o.get("to_province_ids") or [None])[0],
                 "reason": o.get("reason")} for o in rules["orders"]]
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(
                    {"situation": dig, "staff_proposal": proposal}, ensure_ascii=False)}]
    record = {"at": datetime.now().isoformat(timespec="seconds"), "model": MODEL,
              "digest": dig, "staff_proposal": proposal}
    t0 = time.time()
    try:
        resp = _call(messages, key)
        record["latency_s"] = round(time.time() - t0, 1)
        record["usage"] = resp.get("usage")
        choice = resp["choices"][0]
        record["finish_reason"] = choice.get("finish_reason")
        text = choice["message"]["content"]
        record["reply"] = text
        plan = json.loads(text)
    except Exception as e:  # any transport/parse failure: this tick falls back to the rules
        record["error"] = f"{type(e).__name__}: {e}"[:300]
        _archive(record)
        rules.setdefault("brief", {}).setdefault("risks", []).append(
            f"大模型本拍不可用（{type(e).__name__}），已按规则决策")
        return rules

    out = {"orders": [], "alerts": rules["alerts"], "intents": []}
    dropped = []
    seq = 0
    for raw in plan.get("orders", []) if isinstance(plan.get("orders"), list) else []:
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


def out_orders_dropped(before: set[int], out: dict) -> list[int]:
    return sorted(before - {o["order_seq"] for o in out["orders"]})


def _archive(record: dict) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("llm_%Y%m%d_%H%M%S.json")
    (ARCHIVE / name).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
