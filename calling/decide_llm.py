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
NO_STAFF = os.environ.get("COMMANDER_NO_STAFF") == "1"
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
- 玩家方针原文（player_instructions）是你的最高目标，战略取舍（打谁、守哪里、兵力怎么分配）由你自己判断；参谋建议只是参考，可以全部采纳、修改或否决。参谋规则很机械，不要照单全收，要用下面的打法常识检查它。
- 方针档位（stance）：annihilate=寻机歼灭敌军；preserve_force=保存兵力优先；hold_line=守住防线；economize_manpower=节约人力。
- 你有两套指挥手段，都由你决定怎么用：
  1. 作战计划（plan_orders）：组建集团军/集团军群、任命将领、给集团军画前线、画进攻线、执行或停止计划。挂在前线上的集团军由游戏自动布防、补位；执行后，部队沿进攻线主动进攻、推进。这是大兵团作战的主要手段。
  2. 逐师命令（orders）：移动、进攻、撤退、战略转移、取消。用于计划照顾不到的地方：机动预备队、抓住战机的穿插、救急。挂在计划上的师接到逐师命令后仍留在计划里，但会暂时偏离计划的自动行为，不要大量微操计划内的师。

作战计划用法（order_of_battle 是当前编制与计划）：
- 前线（front_line）：指定集团军和交战国，游戏沿整条边境自动铺开。一个集团军最多 24 个师；同一条边境可以由多个集团军分担。前线只守不攻，直到执行。
- 进攻线（offensive_line）：必须先有前线。path 至少 2 个省（只写一个省会被拒绝），是敌方省份编号序列：第一个必须是与我方接壤的敌方省份（front.own_border[].facing 里有），最后一个是目标（例如胜利点要地），中间可加途经点，2～12 个。进攻线要指向要地、避开坏地形和渡河，装甲集团军适合打穿插。
- 删除进攻线（delete_offensive_line）：给出集团军和进攻线的 plan_id（order_of_battle 里 offensive_lines[].plan_id）。进攻线打不动、方向不对、和别的集团军重复时，先删掉再画新的。
- 不同集团军必须从不同方向进攻：每条进攻线的起点不能和别的集团军重复（系统会拒绝）。几个集团军挤在同一条线上就是过度堆叠。好的布势是南北两翼钳形对进、中路牵制，装甲集团军走平原快速穿插、绕到敌后切断，步兵集团军正面施压。
- 执行（execute）：on=true 后，集团军按进攻线发起进攻；on=false 停止。没有进攻线的集团军不要执行（系统会拒绝），它们守住前线即可。
- 组建（create_army）：从 divisions_not_in_any_army 中选不超过 24 个师组成集团军，并指定 unassigned_leaders 中的将领；集团军群（create_army_group）由 1～5 个集团军组成并指定元帅。
- 前线会随边境变化自动调整。进攻线打到终点或起点被攻占后可能消失；执行中的集团军 offensive_lines 为空时，要及时画新的进攻线指向下一个目标，否则它会停下来。
- 前线不必延伸到盟友或中立国境内；如果某条前线大部分在盟友境内，可以考虑不给那里分配集团军。

本土防御（玩家硬性要求，优先于进攻）：
- 本国本土绝不能被占领。front.sections 里 role=home_defense 的段落（例如面对法国的西线）每个省至少要有 min_per_province 个师，short_provinces 是当前不够数的省份，要优先补齐（用远离前线的空闲师战略转移过去）。
- 不要从 home_defense 段落抽调部队，除非同一拍有别的师补上；系统会丢弃会让防线省份低于下限的调动命令。
- 面对中立国（未交战）的边境不需要驻军，那里的师是白白闲置，应调去有用的地方。

打法常识（这是游戏的机制，请据此判断）：
- 战斗宽度：每场战斗双方能同时上阵的兵力有限（provinces 的地形决定宽度，平原约 70，森林约 60，丘陵约 80，山地 75，沼泽 50，城市 96；每多一个进攻方向再加约一半）。超出宽度的师只能排队，同一个目标堆十几个师是浪费，应分散去打多个目标。
- 多方向夹击：从两个以上相邻省份同时进攻同一个省，宽度更大，且有包抄加成。
- 地形和渡河：进攻山地、丘陵、沼泽、城市和有要塞（fort_level）的省份很吃亏；跨河进攻（river_crossing_to 列出的方向）有大幅惩罚。优先打平原、无河的方向。
- 装甲和摩托化（kind=armor/motorized）是突破和扩张的拳头：放在平原、无河的方向打开缺口，打开后继续向纵深推进、切断敌军，而不是和步兵一起顶在坚固阵地上。步兵负责正面牵制和填补战线。
- 包围：敌军被切断补给后会迅速崩溃。两路钳形向敌后合拢比正面平推更快。front.near_closed 是快要被我方包围的敌方省份。
- 疲兵轮换：组织度低于 30 的师进攻效果很差，应该停下休整，让生力军顶上；组织度不是兵力，休整几天就能恢复。
- 投降进度：迫使一国投降主要靠占领胜利点（front.key_targets，分值越高越关键，首都最重要）。进攻方向应指向这些要地，不要平均用力。
- combats 里的 trend 是由连续两拍的组织度变化推算的胜负趋势（winning/losing/even，非游戏原生字段），losing 的战斗要么增援要么停止。
- 进攻命令下达后，师会留在出发省直到打赢才进入目标省，所以出发省看起来很拥挤是正常的；但同一个出发省的师太多，说明它们在排队，应该改打别的目标。

态势字段说明：
- 地图拓扑：front.regions 是己方控制领土中互不连通的陆地块（例如本土与被敌国隔开的飞地），own_units[].region 是每个师所在的陆地块，hops_to_front 是它离本块最近边境省隔几个省。战略转移和移动只能在同一陆地块内进行，不同陆地块之间陆路不通。
- 盟友或附庸国的领土（例如斯洛伐克）里也可能驻有我方部队：own_border 中带 friendly_controller 的省份就是这种盟友省份，那里的师可以直接进攻相邻的敌方省份（例如从斯洛伐克向北进攻波兰，形成南路钳形），但移动和战略转移的目的地只能是本国控制的省份。
- own_units[].kind 是部队类型（infantry 步兵、armor 装甲、motorized 摩托化、mountain 山地、cavalry 骑兵、paratrooper 伞兵），width 是战斗宽度。
- front.forces 按陆地块汇总兵力：战斗中、行军中、空闲（其中组织度≥60 的生力军数、离前线几个省的分布）。空闲的生力军是可以调动的预备队，是否投入、投向哪里由你决定。
- front.key_targets 是敌方仍控制的胜利点省份（victory_points 分值、hops_from_our_land 为离我方控制区几个省）。
- front.own_border 是与交战国接壤的己方省份；facing 列出对面省份的控制国、地形、要塞等级、胜利点和是否需要渡河；enemy_provinces 是各交战国仍控制的省份数（可用来判断战役进度）。
- 你看到的敌军只是正在与我方交战的部队（战争迷雾）。看不见的地方不要假设敌情。
- 没有必要的命令就不下。空命令是正常的。
- 在 reason、intent、summary、risks 里提到己方部队时，一律用部队名称（own_units[].name），不要写编号；unit_id 字段仍填编号。

硬性约束（违反的命令会被系统直接丢弃）：
- unit_id 只能用 own_units 里存在的师；每条命令只给一个师。
- move / retreat / attack 的目标必须是该师所在省份的相邻省份（provinces[].neighbors 或 front.own_border[].neighbors），strategic_redeploy 可以远距离但只能去己方省份。
- attack 只能打与我方交战的国家控制的省份（敌军所在省份）。retreat 只能撤到不在战斗中的己方省份。
- 不要给已经在行军（order.path_province_ids 非空）的师下新的移动类命令；要改道先用 cancel。
- 正在防守战斗中的师（它所在的省被敌军进攻）下进攻命令曾被引擎拒绝，这类师只能留守或撤退；进攻中的师可以改打别的目标。
- 组织度很低（< 15）的师不要投入战斗。
- 不能让 home_defense 段落的任何省份低于 min_per_province 个师。
- last_orders 里 accepted=false 的命令是上一拍被引擎拒绝的，不要原样重复（同一个师、同一类命令、同一个目标会被系统直接丢弃）。战略转移被拒（ISVALID_FALSE）通常表示陆路不可达，例如被敌国领土隔开的飞地，应换目标或改用其他办法。

只输出一个 JSON 对象，不要输出任何其他文字，格式：
{
  "plan_orders": [
    {"type": "front_line", "army_id": 534, "enemy": "POL", "reason": "中文简短理由"},
    {"type": "offensive_line", "army_id": 534, "path": [6567, 3544], "reason": "..."},
    {"type": "delete_offensive_line", "army_id": 531, "plan_id": 47, "reason": "..."},
    {"type": "execute", "army_id": 534, "on": true, "reason": "..."},
    {"type": "create_army", "unit_ids": [1, 2], "leader_id": 349, "reason": "..."},
    {"type": "create_army_group", "army_ids": [531, 532], "leader_id": 342, "reason": "..."},
    {"type": "appoint", "leader_id": 349, "group_id": 534, "reason": "..."}
  ],
  "orders": [
    {"type": "move|attack|retreat|strategic_redeploy|cancel", "unit_id": 1234, "target": 5678, "reason": "中文简短理由"}
  ],
  "intent": "本拍作战意图，一句中文",
  "summary": "给玩家的态势判断，两三句中文",
  "risks": ["中文风险1", "中文风险2"]
}
cancel 不需要 target。没有命令时 orders 为 []，plan_orders 为 []。plan_orders 每拍最多 12 条，只写需要改变的（已有的前线、进攻线、执行状态不必重复下）。
回复要精简：只给需要改变行动的师下命令（正在执行合理命令的师不用重复下），每条 reason 不超过 20 个字，summary 不超过 120 字，risks 最多 4 条。"""


def digest(doc: dict) -> dict:
    """Compact view for the model: only what a commander needs, no evidence."""
    meta, world = doc.get("meta", {}), doc.get("world", {})
    units = []
    for u in world.get("own_units", []):
        row = {"id": u["unit_id"], "name": decide_v0.label(u), "prov": u.get("province_id"),
               "kind": cv.unit_kind(u), "width": cv.width(u),
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
        "combats": _combats(doc),
        "wars": world.get("wars", []),
        "player_instructions": (doc.get("policy") or {}).get("instructions"),
        "front": _front(doc),
        "last_orders": (doc.get("feedback") or {}).get("last_orders", []),
    }


def _combats(doc: dict) -> list[dict]:
    world = doc.get("world") or {}
    view = {c["id"]: c for c in cv.combat_view(doc, remember=bool((doc.get("meta") or {}).get("allow_write")))}
    out = []
    for c in world.get("combats", []):
        row = {"id": c["combat_id"], "prov": c["province_id"],
               "attackers": c.get("attacker_unit_ids"), "defenders": c.get("defender_unit_ids")}
        v = view.get(c["combat_id"]) or {}
        for k in ("we_attack", "ours", "enemy", "trend", "org_change_since_last_tick", "org_damage_total"):
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


def _call(messages: list[dict], key: str, retries: int = 3) -> dict:
    """POST with one retry on transport errors (no game effect, so retrying is safe)."""
    import http.client
    last = None
    for attempt in range(retries + 1):
        try:
            return _call_once(messages, key)
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError, OSError) as e:
            last = e
            if attempt < retries:
                time.sleep(10 * 2 ** attempt)  # 10, 20, 40 s: rides out short network drops
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
    import plan_orders as po
    pview = po.view(input_doc)
    dig["order_of_battle"] = pview
    dig["last_plan_orders"] = (input_doc.get("feedback") or {}).get("last_plan_orders", [])
    proposal = [{"type": o["type"], "unit_id": o["subject"]["unit_ids"][0],
                 "target": (o.get("target_province_ids") or o.get("to_province_ids") or [None])[0],
                 "reason": o.get("reason")} for o in rules["orders"]]
    payload = {"situation": dig} if NO_STAFF else {"situation": dig, "staff_proposal": proposal}
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
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
    accepted_plans = []
    for raw in (plan.get("plan_orders") or [])[:po.MAX_PER_TICK] if isinstance(plan.get("plan_orders"), list) else []:
        why = po.validate(raw, input_doc, pview) if isinstance(raw, dict) else "格式错误"
        if why:
            dropped.append({"order": raw, "why": why})
        else:
            accepted_plans.append(raw)
    input_doc["_plan_orders"] = {"orders": accepted_plans, "view": pview}
    record["accepted_plan_orders"] = accepted_plans
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
