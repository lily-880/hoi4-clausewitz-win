#!/usr/bin/env python3
"""Follow loop_progress.jsonl and print one Chinese line per tick with the
DeepSeek token cost of that tick (matched by time) and the running total.

  python -I -u scripts/loop_report.py --follow
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
import llm_cost  # noqa: E402

OUT = ROOT / "research" / "claude_live"
PROGRESS = OUT / "loop_progress.jsonl"
LLM = OUT / "llm"


def llm_calls_between(t0: datetime, t1: datetime) -> list[dict]:
    rows = []
    for f in sorted(LLM.glob("llm_*.json")):
        stamp = datetime.strptime(f.stem[4:], "%Y%m%d_%H%M%S")
        if t0 < stamp <= t1:
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            r["_at"] = stamp
            rows.append(r)
    return rows


def line(row: dict, prev_at: datetime, total: list[float]) -> str:
    at = datetime.fromisoformat(row["at"]).replace(tzinfo=None)
    calls = llm_calls_between(prev_at, at)
    tin = sum((c.get("usage") or {}).get("prompt_tokens") or 0 for c in calls)
    tout = sum((c.get("usage") or {}).get("completion_tokens") or 0 for c in calls)
    yuan = sum(llm_cost.cost_yuan(c.get("usage"), c.get("model", "deepseek-flash"), c["_at"].astimezone())
               for c in calls)
    total[0] += yuan
    fail = [c.get("error") for c in calls if c.get("error")]
    pol = (row.get("target_provinces") or {}).get("POL")
    return (f"第{row['tick']}拍 {row['game']} 暂停{row['pause']} | 波兰剩余省 {pol} | "
            f"成功{row['orders_ok']} 拒绝{row['orders_refused']} | {row['seconds']}秒 | "
            f"DeepSeek 输入{tin} 输出{tout} 本拍{yuan:.3f}元 累计{total[0]:.2f}元"
            + (f" | 模型故障:{fail[0][:40]}" if fail else "")
            + (f" | 错误:{row['error']}" if row.get("error") else "")
            + (f" | 中止:{row['halted']}" if row.get("halted") else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--follow", action="store_true")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    total = [0.0]
    seen = 0
    prev_at = datetime(2000, 1, 1)
    rows = [json.loads(x) for x in PROGRESS.read_text(encoding="utf-8").splitlines() if x.strip()] \
        if PROGRESS.exists() else []
    if rows:  # first tick: only calls of this run, not older archived runs
        prev_at = datetime.fromisoformat(rows[0]["at"]).replace(tzinfo=None) - timedelta(seconds=rows[0].get("seconds") or 900)
    for r in rows:  # silently account for ticks already reported
        line(r, prev_at, total)
        prev_at = datetime.fromisoformat(r["at"]).replace(tzinfo=None)
        seen += 1
    print(f"已完成 {seen} 拍，DeepSeek 累计约 {total[0]:.2f} 元", flush=True)
    while a.follow:
        rows = [json.loads(x) for x in PROGRESS.read_text(encoding="utf-8").splitlines() if x.strip()]
        for r in rows[seen:]:
            print(line(r, prev_at, total), flush=True)
            prev_at = datetime.fromisoformat(r["at"]).replace(tzinfo=None)
            seen += 1
        time.sleep(5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
