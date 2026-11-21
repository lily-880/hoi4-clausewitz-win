# -*- coding: utf-8 -*-
"""Apply clock-alignment doc + code updates on the PC checkout."""
from __future__ import annotations

from pathlib import Path
import shutil
import re

ROOT = Path(__file__).resolve().parent
# When copied next to repo or run from repo with patch dir
# We expect this script to live in the repo root after copy, with sibling patch files.
# Actually CopyToBox will put files under uploads; better: run with REPO env.

import os
REPO = Path(os.environ.get("CW_REPO", r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win"))
PATCH = Path(os.environ.get("CW_PATCH", str(ROOT)))

def copy_into(rel: str) -> None:
    src = PATCH / rel
    dst = REPO / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"copied {rel}")

copy_into("calling/clock.py")
copy_into("docs/CLOCK_ALIGNMENT.md")

# --- offsets.py: add / update hour keys near GS_DATE_* ---
off = (REPO / "calling" / "offsets.py").read_text(encoding="utf-8")
if "GS_DATE_HOUR_TICK" not in off:
    old = '''    "GS_DATE_YEAR": 0x478,  # i32 year
    "GS_DATE_AUX": 0x47C,  # i32, not the day index
    "GS_DATE_HOURS": 0x484,  # i32 days after 1 January of GS_DATE_YEAR, not hours since 1936'''
    new = '''    "GS_DATE_YEAR": 0x478,  # i32 year — verified UI date
    "GS_DATE_AUX": 0x47C,  # i32 hypothesis only; not day-of-month
    "GS_DATE_HOUR_LIKE": 0x480,  # NOT UI hour (stayed 4 while UI 11->13); discard
    "GS_DATE_HOUR_TICK": 0x468,  # u32; +1 each UI hour; ui_hour=(tick%24)+1
    "GS_DATE_HOURS": 0x484,  # i32 days after 1 January of GS_DATE_YEAR (UI date day index)'''
    if old not in off:
        raise SystemExit("offsets.py date block not found")
    off = off.replace(old, new)
    (REPO / "calling" / "offsets.py").write_text(off, encoding="utf-8")
    print("patched offsets.py")
else:
    print("offsets.py already has GS_DATE_HOUR_TICK")

# --- gamestate.py: expose ui_hour in date_full ---
gs = (REPO / "calling" / "gamestate.py").read_text(encoding="utf-8")
old_block = '''    # Date: year@+0x478; days after 1 January of that year @+0x484.
    from clock import ui_date
    year = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_YEAR", 0x478))[0]
    aux = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_AUX", 0x47C))[0]
    day_index = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOURS", 0x484))[0]
    hour_like = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_LIKE", 0x480))[0]
    out["fields"]["date_year_hypothesis"] = year
    out["fields"]["date_aux_0x47c"] = aux
    out["fields"]["date_day_index"] = day_index
    out["fields"]["date_hour_like_0x480"] = hour_like
    out["fields"]["date_full"] = None
    shown = ui_date(year, day_index)
    if 1936 <= year <= 1950:
        out["verified"]["date_year"] = year
    if shown:
        out["fields"]["date_full"] = {
            "year": year,
            "ui": shown,
            "day_index": day_index,
            "source": "G_GAMESTATE+0x478 year + +0x484 days after 1 January",
        }
        out["verified"]["date_full"] = out["fields"]["date_full"]
        out["verified"]["date_note"] = "year@+0x478; day index@+0x484 (1942+229 = 1942-08-18)"
    elif 1936 <= year <= 1950:
        out["verified"]["date_note"] = "year@+0x478; day index@+0x484 out of range"'''

new_block = '''    # Date: year@+0x478; days after 1 January @+0x484.
    # Hour: u32@+0x468 tick; ui_hour=(tick%24)+1 (verified UI 11/12/13). +0x480 is NOT hour.
    from clock import ui_date, ui_hour
    year = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_YEAR", 0x478))[0]
    aux = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_AUX", 0x47C))[0]
    day_index = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOURS", 0x484))[0]
    hour_like = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_LIKE", 0x480))[0]
    hour_tick = struct.unpack_from("<I", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_TICK", 0x468))[0]
    hour_ui = ui_hour(hour_tick)
    out["fields"]["date_year_hypothesis"] = year
    out["fields"]["date_aux_0x47c"] = aux
    out["fields"]["date_day_index"] = day_index
    out["fields"]["date_hour_like_0x480"] = hour_like
    out["fields"]["date_hour_tick_0x468"] = hour_tick
    out["fields"]["date_ui_hour"] = hour_ui
    out["fields"]["date_full"] = None
    shown = ui_date(year, day_index)
    if 1936 <= year <= 1950:
        out["verified"]["date_year"] = year
    if shown:
        out["fields"]["date_full"] = {
            "year": year,
            "ui": shown,
            "day_index": day_index,
            "ui_hour": hour_ui,
            "hour_tick": hour_tick,
            "source": (
                "G_GAMESTATE+0x478 year + +0x484 days after 1 January; "
                "ui_hour=(u32(+0x468)%24)+1 (verified 2026-11-05); +0x480 not hour"
            ),
        }
        out["verified"]["date_full"] = out["fields"]["date_full"]
        if hour_ui is not None:
            out["verified"]["date_ui_hour"] = hour_ui
        out["verified"]["date_note"] = (
            "year@+0x478; day index@+0x484; ui_hour from +0x468 (1942+229 = 1942-08-18)"
        )
    elif 1936 <= year <= 1950:
        out["verified"]["date_note"] = "year@+0x478; day index@+0x484 out of range"'''

if "date_hour_tick_0x468" in gs:
    print("gamestate.py already has hour tick")
elif old_block not in gs:
    raise SystemExit("gamestate.py date block not found exactly")
else:
    gs = gs.replace(old_block, new_block)
    # docstring above read_campaign_summary
    gs = gs.replace(
        "    Date: year@+0x478 plus days-after-1-January @+0x484 (1942 + 229 = 1942-08-18).\n",
        "    Date: year@+0x478 plus days-after-1-January @+0x484 (1942 + 229 = 1942-08-18).\n"
        "    UI hour: (u32(+0x468)%24)+1; +0x480 is not hour.\n",
    )
    (REPO / "calling" / "gamestate.py").write_text(gs, encoding="utf-8")
    print("patched gamestate.py")

# --- WINDOWS_OFFSETS.md campaign fields table ---
wo = (REPO / "research" / "WINDOWS_OFFSETS.md").read_text(encoding="utf-8")
old_table = '''| date_year | GS+`0x478` i32 | **hypothesis** (1936); exposed in status with note |
| date_aux | GS+`0x47c` i32 | **hypothesis** (seen 31) — possible day-of-year; **not** full Y-M-D |'''
new_table = '''| date_year | GS+`0x478` i32 | **verified** with UI (e.g. 1936); exposed in status |
| date_day_index | GS+`0x484` i32 | **verified** — days after 1 January; 1936+4 → 1936-01-05 |
| date_aux | GS+`0x47c` i32 | **hypothesis** (seen 31) — **not** day-of-month / not UI hour |
| ui_hour_tick | GS+`0x468` u32 | **verified** 2026-11-05 — +1 each UI hour (11→12→13) |
| ui_hour | `(u32(+0x468) % 24) + 1` | **verified** matches UI 11/12/13; see `docs/CLOCK_ALIGNMENT.md` |
| ~~hour @ +0x480~~ | GS+`0x480` | **DISCARD as hour** — stayed 4 while UI advanced |'''
if "ui_hour_tick" in wo and "0x468" in wo and "DISCARD as hour" in wo:
    print("WINDOWS_OFFSETS.md already updated")
elif old_table not in wo:
    raise SystemExit("WINDOWS_OFFSETS.md date rows not found")
else:
    wo = wo.replace(old_table, new_table)
    # Ensure GS_DATE_HOURS naming elsewhere stays coherent — append short section near campaign fields
    marker = "### Campaign fields (read-only status)"
    if "### UI clock alignment (2026-11-05)" not in wo:
        insert = '''### Campaign fields (read-only status)

> **UI clock:** date = year@`+0x478` + day_index@`+0x484`; hour = `(u32(+0x468)%24)+1`.  
> `+0x480` is **not** the UI hour. Details: `docs/CLOCK_ALIGNMENT.md`, reports `clock_align_*.json`.
'''
        if marker not in wo:
            raise SystemExit("campaign fields marker missing")
        wo = wo.replace(marker + "\n", insert, 1)
    (REPO / "research" / "WINDOWS_OFFSETS.md").write_text(wo, encoding="utf-8")
    print("patched WINDOWS_OFFSETS.md")

# --- README: short status date note (UTF-8 safe) ---
readme = (REPO / "README.md").read_text(encoding="utf-8")
needle = "| **RO 附着 / 科目** | `clausewitz_win.py status` · `army_subjects` | 读省份、路径、标签 |"
repl = "| **RO 附着 / 科目** | `clausewitz_win.py status` · `army_subjects` | 读省份、路径、标签；**UI 日期/小时**见 `docs/CLOCK_ALIGNMENT.md`（`+0x478/+0x484` 日期，`(u32(+0x468)%24)+1` 小时） |"
if "CLOCK_ALIGNMENT.md" in readme:
    print("README already mentions CLOCK_ALIGNMENT")
elif needle not in readme:
    # mojibake may have broken the table — try softer insert after status section
    soft = "python clausewitz_win.py status\n"
    soft_repl = (
        "python clausewitz_win.py status\n"
        "# status date_full: year@+0x478 + day_index@+0x484; ui_hour=(u32(+0x468)%24)+1\n"
        "# see docs/CLOCK_ALIGNMENT.md\n"
    )
    if soft in readme and "CLOCK_ALIGNMENT.md" not in readme:
        readme = readme.replace(soft, soft_repl, 1)
        (REPO / "README.md").write_text(readme, encoding="utf-8")
        print("patched README.md (status comment)")
    else:
        print("WARN: README needle not found; skipping README fold")
else:
    readme = readme.replace(needle, repl, 1)
    (REPO / "README.md").write_text(readme, encoding="utf-8")
    print("patched README.md")

print("DONE")
