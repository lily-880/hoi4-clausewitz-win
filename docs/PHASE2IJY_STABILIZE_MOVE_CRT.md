# Phase 2ijy — Stabilize Move CRT

## Result
G6_MOVE_HIT_BUT_PROCESS_EXIT__HEAP_CORRUPT_DIAG

## What worked
- Stub leak on WAIT_TIMEOUT (no VirtualFreeEx while remote Post may still run)
- ONE Move reaffirm: army 1042 → 3931 → **PATH_CONTAINS_DEST** (path includes dest)
- ind_pid prefers largest WS (zombie 38376 skipped)
- ucrtbase!malloc smoke for province_arr (staged for live Post)

## What failed / stubbed
- Process still exited ~16s after Post with **0xC0000374 STATUS_HEAP_CORRUPTION**
- Stub-leak alone insufficient
- Root hyp: VirtualAllocEx province_arr freed by game vector dtor
- Second live Post **not** run (slice max=1 already used)
- post_wait still 258 (async accept)

## Live left
SELF-RELAUNCH ITA @1x after exit; allow_post False

## Next
2ijz live Move with province_buf_kind=ucrt_malloc + stability metrics
