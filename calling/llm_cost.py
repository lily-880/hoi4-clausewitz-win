"""DeepSeek token cost in RMB (official price page, read 2026-11-23).

deepseek-flash, yuan per 1M tokens:
  input cache hit   0.04 peak / 0.02 off-peak
  input cache miss  2.00 peak / 1.00 off-peak
  output            8.00 peak / 4.00 off-peak
Peak: Beijing time Mon-Fri 09:00-12:00 and 14:00-18:00 (holidays not modelled);
everything else is off-peak (half price).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

PRICES = {"deepseek-flash": {"hit": 0.04, "miss": 2.0, "out": 8.0},
          "deepseek-v4-pro": {"hit": 0.30, "miss": 9.0, "out": 27.0}}


def is_peak(at: datetime) -> bool:
    bj = at.astimezone(timezone(timedelta(hours=8)))
    if bj.weekday() >= 5:
        return False
    h = bj.hour + bj.minute / 60
    return 9 <= h < 12 or 14 <= h < 18


def cost_yuan(usage: dict | None, model: str = "deepseek-flash", at: datetime | None = None) -> float:
    if not usage:
        return 0.0
    p = PRICES.get(model, PRICES["deepseek-flash"])
    factor = 1.0 if is_peak(at or datetime.now().astimezone()) else 0.5
    hit = usage.get("prompt_cache_hit_tokens") or 0
    miss = usage.get("prompt_cache_miss_tokens")
    if miss is None:
        miss = max(0, (usage.get("prompt_tokens") or 0) - hit)
    out = usage.get("completion_tokens") or 0
    return factor * (hit * p["hit"] + miss * p["miss"] + out * p["out"]) / 1_000_000
