#!/usr/bin/env python3
"""Observer: read-only analysis of the running campaign from saved tick files.

Never touches the game or the commander's inputs. Prints a Chinese summary.
  python -I scripts/observer.py
"""
from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "claude_live"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    prog = [json.loads(x) for x in (OUT / "loop_progress.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    prog = [r for r in prog if r.get("game") and "None" not in r["game"]]
    print("== 进度曲线（每 4 拍取一点）")
    for r in prog[::4] + prog[-1:]:
        print(f"  第{r['tick']}拍 {r['game']}  波兰剩余省 {r['target_provinces'].get('POL')}  成功命令 {r['orders_ok']}")
    caps = sorted(glob.glob(str(OUT / "tick_*_capture.json")))
    cap = load(caps[-1])
    w, ext = cap["observation"]["world"], cap.get("commander_ext") or {}
    top = ext.get("topology") or {}
    units = w["own_units"]
    U = {u["unit_id"]: u for u in units}
    V = {v["unit_id"]: v for v in w.get("visible_units", [])}
    print("\n== 当前（%s）" % cap["observation"]["meta"]["game_time"])
    fighting = [u for u in units if u.get("in_combat")]
    marching = [u for u in units if not u.get("in_combat") and u.get("order")]
    idle = [u for u in units if not u.get("in_combat") and not u.get("order")]
    print(f"  兵力：战斗 {len(fighting)}，行军 {len(marching)}，空闲 {len(idle)}（组织度≥60 的 {sum(1 for u in idle if u['organization']>=60)}）")
    att = [c for c in w["combats"] if set(c["attacker_unit_ids"]) & set(U)]
    dfn = [c for c in w["combats"] if set(c["defender_unit_ids"]) & set(U)]
    print(f"  战斗：我方进攻 {len(att)} 场，我方防守 {len(dfn)} 场")
    good = bad = 0
    rows = []
    for c in att:
        ours = [x for x in c["attacker_unit_ids"] if x in U]
        cas = c.get("casualties") or {}
        lo, le = cas.get("our_org_loss", 0), cas.get("enemy_org_loss", 0)
        ratio = le / lo if lo else float("inf")
        good += ratio >= 1.5
        bad += ratio < 0.8
        enemy_org = [round(V[x]["organization"], 1) for x in c["defender_unit_ids"] if x in V]
        rows.append((c["province_id"], len(ours), round(sum(U[x]["organization"] for x in ours) / len(ours), 1),
                     len(c["defender_unit_ids"]), enemy_org, round(lo, 1), round(le, 1)))
    print(f"  进攻战斗中战损比明显有利（敌损≥我损1.5倍）{good} 场，明显不利 {bad} 场")
    for r in sorted(rows, key=lambda r: -r[1])[:10]:
        print(f"    省{r[0]}：我{r[1]}师 均组织度{r[2]} vs 敌{r[3]}师 组织度{r[4]}  损耗 我{r[5]}/敌{r[6]}")
    stack = Counter(len([x for x in c["attacker_unit_ids"] if x in U]) for c in att)
    print("  每场进攻投入师数分布：", dict(sorted(stack.items())))
    kt = top.get("key_targets") or []
    print("  波兰胜利点要地（前8）：", [(k["province_id"], k["victory_points"], k["hops_from_our_land"]) for k in kt[:8]])
    print("  敌控省份：", {k: v for k, v in (ext.get("enemy_controlled_provinces") or {}).items() if k in ("POL", "FRA", "ENG")})
    print("\n== DeepSeek 最近 5 次作战意图")
    for f in sorted(glob.glob(str(OUT / "llm" / "llm_*.json")))[-5:]:
        r = load(f)
        try:
            p = json.loads(r.get("reply") or "{}")
        except ValueError:
            p = {}
        print(f"  {Path(f).stem[4:]}  采纳{len(r.get('accepted_orders') or [])}条  {p.get('intent') or r.get('error')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
