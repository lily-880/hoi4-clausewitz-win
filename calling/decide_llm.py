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
import generalissimo_output as contract  # noqa: E402

VERSION = "decide_llm"
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
TIMEOUT_S = 90
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
- 按玩家方针（policy.stance）行事：annihilate=寻机歼灭敌军；preserve_force=保存兵力优先；hold_line=守住防线；economize_manpower=节约人力。
- 你看到的敌军只是正在与我方交战的部队（战争迷雾）。看不见的地方不要假设敌情。
- 没有必要的命令就不下。空命令是正常的。

硬性约束（违反的命令会被系统直接丢弃）：
- unit_id 只能用 own_units 里存在的师；每条命令只给一个师。
- move / retreat / attack 的目标必须是该师所在省份的相邻省份（provinces[].neighbors），strategic_redeploy 可以远距离但只能去己方省份。
- attack 只能打与我方交战的国家控制的省份（敌军所在省份）。retreat 只能撤到不在战斗中的己方省份。
- 不要给已经在行军（order.path_province_ids 非空）的师下新的移动类命令；要改道先用 cancel。
- 正在战斗中的师不能发起进攻；只能留守或撤退。
- 组织度很低（< 15）的师不要投入战斗。

只输出一个 JSON 对象，不要输出任何其他文字，格式：
{
  "orders": [
    {"type": "move|attack|retreat|strategic_redeploy|cancel", "unit_id": 1234, "target": 5678, "reason": "中文简短理由"}
  ],
  "intent": "本拍作战意图，一句中文",
  "summary": "给玩家的态势判断，两三句中文",
  "risks": ["中文风险1", "中文风险2"]
}
cancel 不需要 target。没有命令时 orders 为 []。"""


def digest(doc: dict) -> dict:
    """Compact view for the model: only what a commander needs, no evidence."""
    meta, world = doc.get("meta", {}), doc.get("world", {})
    units = []
    for u in world.get("own_units", []):
        row = {"id": u["unit_id"], "prov": u.get("province_id"),
               "org": round(u.get("organization") or 0, 1),
               "hp": round((u.get("strength") or {}).get("current") or 0, 1)}
        if u.get("in_combat"):
            row["combat"] = u.get("combat_id")
        if (u.get("order") or {}).get("path_province_ids"):
            row["route"] = u["order"]["path_province_ids"]
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
        "last_orders": (doc.get("feedback") or {}).get("last_orders", []),
    }


def _call(messages: list[dict], key: str) -> dict:
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.3,
                       "response_format": {"type": "json_object"}, "max_tokens": 2000}).encode("utf-8")
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
    rules = decide_v1.decide(input_doc)
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
        text = resp["choices"][0]["message"]["content"]
        record["reply"] = text
        plan = json.loads(text)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as e:
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
    record["accepted_orders"] = out["orders"]
    record["dropped"] = dropped
    final_errs = contract.validate_output(out, input_doc)
    if final_errs:
        record["fallback"] = final_errs
        _archive(record)
        return rules
    _archive(record)
    return out


def _archive(record: dict) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("llm_%Y%m%d_%H%M%S.json")
    (ARCHIVE / name).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
