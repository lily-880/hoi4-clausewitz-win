from pathlib import Path
import re
land = Path("docs/LAND_POST_READINESS.md")
safe = Path("docs/SAFE_POST_ENABLE_CHECKLIST.md")
t = land.read_text(encoding="utf-8")
block = (
    "**2iv relaunch PATH200:** result=`PATH200_RELAUNCH_PATH_ONLY_HIT` · fresh ITA "
    "`-start_tag=ITA -start_speed=1` pid=33840 · ita_ok=17 nonempty=2 multi=0 · "
    "1040→[12857] oi=70 · 1053→[9945] oi=57 · focus740 miss · "
    "OG50 reverse oi_scanned=2000 oi_with_arr50=360 · clock=RELOAD_OR_NEW_CAMPAIGN "
    "year=1936 day_index=13 ui=1936-01-14 · allow_post=False · speed=1x CLI only · "
    "prior cohort 461/1042 N/A on new process · still NO ALLOW_POST / NO Post inject "
    "(2iw/2iy scripts not re-run).\n\n"
)
if "PATH200_RELAUNCH_PATH_ONLY_HIT" not in t:
    m = re.search(r"\*Phase 2iv.*?Asia/Shanghai\*", t)
    if m:
        t = t[: m.end()] + "\n\n" + block + t[m.end() :]
    else:
        t = t.rstrip() + "\n\n" + block
    old = "| **2iv** | `COHORT_REHOME_HIT` | 2iu focus-740 cohort rehome after oi recycle | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |"
    new = "| **2iv** | `COHORT_REHOME_HIT` + `PATH200_RELAUNCH_PATH_ONLY_HIT` | cohort rehome + fresh ITA relaunch PATH200 path_only oi=70/57 | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |"
    if old in t:
        t = t.replace(old, new, 1)
    land.write_text(t, encoding="utf-8")
    print("LAND folded")
else:
    print("LAND already")

s = safe.read_text(encoding="utf-8")
if "PATH200_RELAUNCH_PATH_ONLY_HIT" not in s:
    s = s.replace(
        "| 2iv | 2iu focus-740 cohort rehome after oi recycle | **COHORT_REHOME_HIT** (Post still CLOSED) |",
        "| 2iv | 2iu focus-740 cohort rehome after oi recycle | **COHORT_REHOME_HIT** (Post still CLOSED) |\n"
        "| 2iv-relaunch | fresh ITA PATH200 path_only oi=70/57 | **PATH200_RELAUNCH_PATH_ONLY_HIT** (Post still CLOSED) |",
        1,
    )
    s = s.replace(
        "*Phase 2iv — cohort rehome. Gate stays CLOSED. 2026-11-01 Asia/Shanghai*",
        "*Phase 2iv — cohort rehome + relaunch PATH200. Gate stays CLOSED. 2026-11-01 Asia/Shanghai*",
        1,
    )
    safe.write_text(s, encoding="utf-8")
    print("SAFE folded")
else:
    print("SAFE already")
