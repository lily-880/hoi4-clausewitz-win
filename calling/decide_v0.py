"""decide() v0: observe-and-report generalissimo.

decide(input) -> output per 陆军总司令函数接口.md. Version 0 never issues orders,
even when meta.allow_write is true: the write path is not yet verified end to
end on 1.19.5, so v0 only produces alerts and a brief from what the input
actually contains. It accepts a partial input (fields the engine could not
read are simply absent) and never fills them in.

Judgement calls that are the commander's own (not engine readings), and so
allowed to be decided here:
  * alert severity (encircled -> critical, encirclement_imminent/plan_failed
    -> high, shortages -> watch);
  * default stance preserve_force when policy.stance is absent (spec text).

Pure offline code: no process reads, no Post, no save access.

CLI:
  python calling/decide_v0.py --input research/t201_full_capture_recursive_a.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import generalissimo_output as contract  # noqa: E402

VERSION = "decide_v0"
DEFAULT_STANCE = "preserve_force"  # 宪章: stance 未给时按「保部队优先，再寻歼灭机会」
WORLD_BLOCKS = ("own_units", "visible_units", "army_groups", "armies", "leaders",
                "provinces", "plans", "combats", "crises", "wars", "shortages")


def _present(d: dict, *keys):
    return {k: d[k] for k in keys if k in d}


def _alerts(world: dict) -> list[dict]:
    alerts: list[dict] = []

    def add(kind, severity, message, payload, action=None):
        a = {"alert_id": f"{kind}-{len(alerts) + 1}", "severity": severity, "kind": kind,
             "message": message, "payload": payload}
        if action:
            a["suggested_player_action"] = action
        alerts.append(a)

    for crisis in world.get("crises", []):
        kind = crisis.get("kind")
        units = sorted(crisis.get("unit_ids", []))
        provs = sorted(crisis.get("province_ids", []))
        if kind == "encircled":
            add(kind, "critical", f"{len(units)} 个师被包围", {"unit_ids": units, "province_ids": provs})
        elif kind == "encirclement_imminent":
            add(kind, "high", f"{len(units)} 个师即将被包围",
                {"unit_ids": units, "province_ids": provs})
        elif kind == "plan_failed":
            add(kind, "high", "计划无法执行", {})

    shortages = world.get("shortages", {})
    for eq in shortages.get("equipment", []):
        units = sorted(eq.get("affected_unit_ids", []))
        if not units:
            continue
        payload = _present(eq, "equipment_type", "stockpile", "demanded", "deficit",
                           "affected_plan_ids")
        payload["affected_unit_ids"] = units
        stock = f"，库存 {eq['stockpile']}" if "stockpile" in eq else ""
        add("equipment_shortage", "watch",
            f"{eq['equipment_type']} 不足：{len(units)} 个师未满编{stock}",
            payload, "调整生产或装备分配（总司令无生产权限）")
    mp = shortages.get("manpower", {})
    if mp.get("affected_unit_ids"):
        payload = _present(mp, "available", "needed", "deficit")
        payload["affected_unit_ids"] = sorted(mp["affected_unit_ids"])
        add("manpower_shortage", "watch", f"{len(payload['affected_unit_ids'])} 个师缺人力",
            payload, "检查征兵法与人力（总司令无征兵权限）")
    md = shortages.get("missing_divisions")
    if isinstance(md, dict) and md.get("reason"):
        add("missing_divisions", "high", "某段战线现有兵力不足",
            _present(md, "plan_id", "province_ids", "needed_estimate", "reason"))

    for combat in world.get("combats", []):
        result = combat.get("result")
        if result in ("our_victory", "our_defeat"):
            kind = "major_victory" if result == "our_victory" else "major_defeat"
            add(kind, "info" if kind == "major_victory" else "high",
                f"战斗 {combat['combat_id']} 结束：{'胜' if kind == 'major_victory' else '败'}",
                _present(combat, "combat_id", "province_id", "casualties"))
    return alerts


def _brief(meta: dict, policy: dict, world: dict, stance: str) -> dict | None:
    if "game_time" not in meta:
        return None
    units = world.get("own_units", [])
    unit_by_id = {u["unit_id"]: u for u in units if "unit_id" in u}
    own = set(unit_by_id)

    combats = []
    for c in world.get("combats", []):
        att = own & set(c.get("attacker_unit_ids", []))
        dfn = own & set(c.get("defender_unit_ids", []))
        if att or dfn:
            combats.append((c, att, dfn))

    plans = world.get("plans", [])
    executing = sum(1 for p in plans if p.get("executing") is True)
    allow = meta.get("allow_write") is True
    mode = "允许写入，但 v0 不下令" if allow else "观察模式（allow_write=false）"
    summary = (f"{mode}。己方 {len(units)} 个师，{len(combats)} 场战斗涉及我方，"
               f"{len(plans)} 条计划（执行中 {executing}）。")
    missing = [b for b in WORLD_BLOCKS if b not in world]
    if missing:
        summary += "输入未提供：" + "、".join(missing) + "。"

    army_units = {a["army_id"]: set(a.get("unit_ids", []))
                  for a in world.get("armies", []) if "army_id" in a}
    fronts = []
    for p in sorted(plans, key=lambda p: p["plan_id"]):
        direct = set(p.get("assigned_unit_ids", []))
        armies = p.get("assigned_army_ids", [])
        via_army = set().union(*(army_units.get(a, set()) for a in armies)) if armies else set()
        state = "执行中" if p.get("executing") else "未执行"
        text = (f"{state}；绑定 {len(armies)} 个集团军；直接绑定 {len(direct)} 个师，"
                f"经集团军共 {len(direct | via_army)} 个师；控制点 {len(p.get('vertex_province_ids', []))} 个")
        if not direct and not via_army:
            text += "；没有可见的部队绑定"
        fronts.append({"plan_id": p["plan_id"], "assessment": text})

    risks = []
    for c, att, dfn in combats:
        if dfn:
            orgs = [unit_by_id[u].get("organization") for u in sorted(dfn)]
            orgs = [round(o, 1) for o in orgs if isinstance(o, (int, float))]
            org_text = f"，组织度 {orgs}" if orgs else ""
            risks.append(f"省份 {c.get('province_id')} 我方 {len(dfn)} 个师正在防守"
                         f"（战斗 {c.get('combat_id')}，敌方 {len(c.get('attacker_unit_ids', []))} 个单位）"
                         f"{org_text}")
    short = sorted((u["unit_id"], u["supply"].get("ratio")) for u in units
                   if u.get("supply", {}).get("in_supply") is False)
    if short:
        # in_supply=false is the engine's out-of-supply flag; it is not isolation.
        parts = [f"{uid}" + (f"({ratio:.0%})" if isinstance(ratio, (int, float)) else "")
                 for uid, ratio in short]
        risks.append(f"{len(short)} 个师补给不满足（引擎缺补给判定，括号内为补给满足率，"
                     f"不代表被切断）：{'、'.join(parts)}")
    for crisis in world.get("crises", []):
        if crisis.get("kind") in ("org_collapse", "out_of_supply"):
            risks.append(f"危机 {crisis['kind']}：师 {sorted(crisis.get('unit_ids', []))}")
    for war in world.get("wars", []):
        if war.get("front_invalidated") is True:
            risks.append("战争状态变化导致前线失效，需要重布")

    watch = [f"战斗 {c.get('combat_id')} @ 省份 {c.get('province_id')}" for c, _, _ in combats]

    brief = {"game_time": meta["game_time"], "summary": summary, "stance_applied": stance}
    if fronts:
        brief["fronts"] = fronts
    if risks:
        brief["risks"] = risks
    if watch:
        brief["next_watch"] = watch
    return brief


def decide(input_doc: dict) -> dict:
    meta = input_doc.get("meta", {}) or {}
    policy = input_doc.get("policy", {}) or {}
    world = input_doc.get("world", {}) or {}
    stance = policy.get("stance", DEFAULT_STANCE)
    output = {"orders": [], "alerts": _alerts(world), "intents": []}
    brief = _brief(meta, policy, world, stance)
    if brief:
        output["brief"] = brief
    return output


def load_input(path: Path, policy_path: Path | None, use_policy: bool) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if "observation" in doc and "meta" not in doc:  # capture export wrapper
        doc = doc["observation"]
    if use_policy:
        import commander_config
        doc = commander_config.merge_commander_policy(doc, policy_path)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run decide_v0 on a saved input (offline).")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--policy", type=Path, default=None,
                    help="commander policy JSON (default calling/tables/commander_policy.json)")
    ap.add_argument("--no-policy", action="store_true", help="do not merge commander policy")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    doc = load_input(args.input, args.policy, not args.no_policy)
    out = decide(doc)
    errors = contract.validate_output(out, doc)
    print(json.dumps({"decider": VERSION, "output": out, "validation_errors": errors},
                     ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
