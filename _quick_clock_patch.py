# -*- coding: utf-8 -*-
from pathlib import Path
REPO = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")

# offsets
p = REPO / "calling" / "offsets.py"
t = p.read_text(encoding="utf-8")
if "GS_DATE_HOUR_TICK" not in t:
    needle = '"GS_DATE_HOURS": 0x484,'
    insert = (
        '"GS_DATE_HOUR_LIKE": 0x480,  # NOT UI hour; discard\n'
        '    "GS_DATE_HOUR_TICK": 0x468,  # u32 +1/UI hour; ui_hour=(tick%24)+1\n'
        '    "GS_DATE_HOURS": 0x484,'
    )
    if needle not in t:
        raise SystemExit("offsets needle missing")
    p.write_text(t.replace(needle, insert, 1), encoding="utf-8")
    print("offsets")
else:
    print("offsets skip")

# gamestate — only add ui_hour if block still old
g = REPO / "calling" / "gamestate.py"
gt = g.read_text(encoding="utf-8")
if "date_hour_tick_0x468" not in gt:
    gt2 = gt.replace(
        "from clock import ui_date",
        "from clock import ui_date, ui_hour",
        1,
    )
    old = '    hour_like = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_LIKE", 0x480))[0]\n'
    add = (
        '    hour_like = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_LIKE", 0x480))[0]\n'
        '    hour_tick = struct.unpack_from("<I", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_TICK", 0x468))[0]\n'
        '    hour_ui = ui_hour(hour_tick)\n'
    )
    if old not in gt2:
        raise SystemExit("gamestate hour_like missing")
    gt2 = gt2.replace(old, add, 1)
    gt2 = gt2.replace(
        '    out["fields"]["date_hour_like_0x480"] = hour_like\n',
        '    out["fields"]["date_hour_like_0x480"] = hour_like\n'
        '    out["fields"]["date_hour_tick_0x468"] = hour_tick\n'
        '    out["fields"]["date_ui_hour"] = hour_ui\n',
        1,
    )
    old_df = '''        out["fields"]["date_full"] = {
            "year": year,
            "ui": shown,
            "day_index": day_index,
            "source": "G_GAMESTATE+0x478 year + +0x484 days after 1 January",
        }
        out["verified"]["date_full"] = out["fields"]["date_full"]
        out["verified"]["date_note"] = "year@+0x478; day index@+0x484 (1942+229 = 1942-08-18)"'''
    new_df = '''        out["fields"]["date_full"] = {
            "year": year,
            "ui": shown,
            "day_index": day_index,
            "ui_hour": hour_ui,
            "hour_tick": hour_tick,
            "source": "G_GAMESTATE+0x478/+0x484 date; ui_hour=(u32(+0x468)%24)+1; +0x480 not hour",
        }
        out["verified"]["date_full"] = out["fields"]["date_full"]
        if hour_ui is not None:
            out["verified"]["date_ui_hour"] = hour_ui
        out["verified"]["date_note"] = "year@+0x478; day@+0x484; ui_hour from +0x468"'''
    if old_df not in gt2:
        raise SystemExit("gamestate date_full missing")
    g.write_text(gt2.replace(old_df, new_df, 1), encoding="utf-8")
    print("gamestate")
else:
    print("gamestate skip")

# WINDOWS_OFFSETS fold
w = REPO / "research" / "WINDOWS_OFFSETS.md"
wt = w.read_text(encoding="utf-8")
if "DISCARD as hour" not in wt:
    old = "| date_year | GS+`0x478` i32 | **hypothesis** (1936); exposed in status with note |\n| date_aux | GS+`0x47c` i32 | **hypothesis** (seen 31) — possible day-of-year; **not** full Y-M-D |"
    new = (
        "| date_year | GS+`0x478` i32 | **verified** with UI; exposed in status |\n"
        "| date_day_index | GS+`0x484` i32 | **verified** days after Jan 1 (1936+4→1936-01-05) |\n"
        "| date_aux | GS+`0x47c` i32 | hypothesis only — not day-of-month |\n"
        "| ui_hour_tick | GS+`0x468` u32 | **verified** +1 each UI hour (11→12→13) |\n"
        "| ui_hour | `(u32(+0x468)%24)+1` | **verified** UI 11/12/13; `docs/CLOCK_ALIGNMENT.md` |\n"
        "| ~~+0x480~~ | GS+`0x480` | **DISCARD as hour** (stayed 4) |"
    )
    if old not in wt:
        raise SystemExit("WINDOWS_OFFSETS rows missing")
    wt = wt.replace(old, new, 1)
    if "CLOCK_ALIGNMENT.md" not in wt:
        wt = wt.replace(
            "### Campaign fields (read-only status)\n",
            "### Campaign fields (read-only status)\n\n> UI clock: year@+0x478 + day@+0x484; hour=`(u32(+0x468)%24)+1`. +0x480 not hour. See `docs/CLOCK_ALIGNMENT.md`.\n\n",
            1,
        )
    w.write_text(wt, encoding="utf-8")
    print("WINDOWS_OFFSETS")
else:
    print("WINDOWS_OFFSETS skip")

# README one-liner
r = REPO / "README.md"
rt = r.read_text(encoding="utf-8")
if "CLOCK_ALIGNMENT.md" not in rt:
    rt = rt.replace(
        "python clausewitz_win.py status\n",
        "python clausewitz_win.py status\n# UI date/hour: docs/CLOCK_ALIGNMENT.md  (+0x478/+0x484 date; (u32(+0x468)%24)+1 hour)\n",
        1,
    )
    r.write_text(rt, encoding="utf-8")
    print("README")
else:
    print("README skip")
print("OK")
