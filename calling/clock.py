"""Campaign date from CGameState.

+0x478 is the year. +0x484 is the number of days after 1 January of that year.
1942 and 229 is 1942-08-18. It is not an hour count since 1936-01-01.
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
