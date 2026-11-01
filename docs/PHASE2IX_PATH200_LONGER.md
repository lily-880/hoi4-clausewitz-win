# Phase 2ix — NON-Post longer 1x advance + PATH200

**Result:** `PATH200_LONGER_STABLE_THIN`

**Important:** Historical Post scripts (`phase2ix_strategic_isvalid_post.py`, `phase2iw_one_strategic_post.py`, `phase2iy_*`) were **NOT** re-run. `allow_post` False.

**Advance:** ~480s wall @1x (drain 52243→89174); day_index **stuck at 13**; exec **flat 8182**; Space unpause attempt → still day=13 exec=8182. Calendar/sim likely stalled; PATH unchanged vs 2iw.

**Live:** pid 33840 · ITA · year=1936 · day_index=13 · ui=1936-01-14 · clock=RELOAD_OR_NEW_CAMPAIGN · drain≈89174+ · allow_post=False · speed mem untouched

**PATH200:** nonempty=2 multi=0 · focus_oi_seed=2 · same 1040→[12857] oi=70 · 1053→[9945] oi=57 · new_dests=[] new_ois=[] inst_ok_ois=[] · Inst70 empty · ARR88×PATH empty · vs_2iw deltas all 0

**Date probe:** year@+0x478=1936 · +0x480=13 · +0x484=13 · aux@+0x47c=31

**Next shortest NON-Post:** unblock calendar (relaunch ITA @1x if softlocked / verify not stuck on popup) then denser multi-path · human midflight CMove · SAFE Post for ring_embed — still **NO ALLOW_POST**

*Phase 2ix NON-Post PATH200 · 2026-11-01 Asia/Shanghai*
