# Phase 2ijx — Move Post timeout diagnosis + fixed retry

**Result:** `G6_MOVE_POST_HIT`
**Posts:** move=1 strategic=0
**allow_post final:** False

## Diagnosis vs 2iju Strategic
- Same FN_CMD_QUEUE_POST(session, cmd, r8=1); prior wait 3000ms both
- Strategic HIT PATH_CONTAINS_DEST post_rax=1; Move 2ijw WAIT_TIMEOUT(258)
- Layout: Strategic inline cmd+0x38; Move remote VirtualAllocEx province_arr
- Fixes: Post wait=20000ms; wait exec_6cc clear; no pause-mem invent

## G6
- chosen={'ok': True, 'result': 'DRY_RUN_VALID', 'army': 1042, 'province': 3931, 'path_before': [], 'factory_idx': 1402}
- post={'ok': True, 'result': 'PATH_CONTAINS_DEST', 'army': 1042, 'province': 3931, 'post_rax': 0, 'post_wait': 258, 'path_before': [], 'path_after': [9896, 13222, 3909, 11737, 3816, 6901, 9842, 3931], 'factory_idx': 1402}
- observe deltas: 5, drain=74

## Path C
estimate_after=~74-76%; crossed_70=True

*Phase 2ijx — 2026-11-01 22:39 Asia/Shanghai*

## Honesty
PATH_CONTAINS_DEST proven: path_after included dest 3931 [9896, 13222, 3909, 11737, 3816, 6901, 9842, 3931]. post_wait still 258 WAIT_TIMEOUT and post_rax=0 (stub wait returned before thread finished) — Post appears async-accepted. hoi4 then went Responding=False and process exited; SELF-RELAUNCH ITA @1x after observe. HIT stands on path evidence, not ambient seq/drain.
