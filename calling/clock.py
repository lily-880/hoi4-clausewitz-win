"""Campaign UI date/time from CGameState (read-only).

Date (verified with UI):
  +0x478 i32 year
  +0x484 i32 day_index = days after 1 January of that year
  Example: year=1942, day_index=229 -> 1942-08-18

Hour (verified 2026-11-05 with player UI 11:00 -> 12:00 -> 13:00):
  +0x468 u32 hour tick — increments exactly +1 each UI hour
  ui_hour = (u32(+0x468) % 24) + 1   # matches HOI4 UI clock for samples 11/12/13
  +0x480 is NOT the UI hour (stayed 4 while UI advanced 11->13) — discard as hour
"""
from __future__ import annotations

from datetime import datetime, timedelta


def ui_date(year: int, day_index: int) -> str | None:
    if not (1 <= year <= 3000 and 0 <= day_index < 366):
        return None
    try:
        return (datetime(year, 1, 1) + timedelta(days=int(day_index))).strftime("%Y-%m-%d")
    except ValueError:
        return None


def ui_hour(hour_tick: int) -> int | None:
    """Map G_GAMESTATE+0x468 u32 tick to UI hour (1..24) matching verified samples."""
    try:
        t = int(hour_tick) & 0xFFFFFFFF
    except (TypeError, ValueError):
        return None
    return (t % 24) + 1
