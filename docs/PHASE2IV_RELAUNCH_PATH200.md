# Phase 2iv — relaunch PATH200 after reconcile

**Result:** PATH200_RELAUNCH_PATH_ONLY_HIT

**Reconcile:** box ef16ccf → shared HEAD 30272ad (includes prior COHORT_REHOME_HIT). Game was dead; launched hoi4.exe -gdpr-compliant -start_tag=ITA -start_speed=1 (AI on). **No Post. allow_post False. Never 5x.**

**Live:** pid 33840 · tag=15 · year@+0x478=1936 · day_index@+0x484=13 · ui_corrected=1936-01-14 · clock=RELOAD_OR_NEW_CAMPAIGN · drain=23422 exec=8182 · speed=1x CLI only

**PATH200:** ita_ok=17 empty=15 nonempty=2 multi=0 dig_focus=[740, 489, 490, 1656, 3579]
**Rows:** [{"index": 1040, "path_ids": [12857], "path_n": 1, "focus_hit": [], "ois": [70], "kinds": [{"oi": 70, "kind": "other"}], "class": "path_only", "row_kind": "path_only"}, {"index": 1053, "path_ids": [9945], "path_n": 1, "focus_hit": [], "ois": [57], "kinds": [{"oi": 57, "kind": "other"}], "class": "path_only", "row_kind": "path_only"}]
**OG50 reverse:** {"oi_scanned": 2000, "oi_with_arr50": 360} army_to_ois={"1053": [57], "1040": [70]}
**Focus740:** no hit yet on fresh relaunch (path_only only). Prior 2iv cohort 461/1042/… N/A on new process.

**Date honesty:** +0x484 is day index (not hours-since-1936). Legacy live_meta hours model kept for continuity only.

**Next shortest NON-Post:** denser PATH200 after more 1x hours / human midflight CMove / SAFE Post for ring_embed — still **NO ALLOW_POST**. Do not re-run 2iw/2iy Post inject scripts.

*Phase 2iv relaunch · 2026-11-01 Asia/Shanghai*
