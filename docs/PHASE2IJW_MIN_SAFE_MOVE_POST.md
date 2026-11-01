# Phase 2ijw — Minimum safe Move Post (G4→G5→G6)

**Result:** `G6_MOVE_POST_TIMEOUT` (corrected; prior ACCEPTED_WEAK overclaimed)
**Posts:** move=1 strategic=0
**allow_post final:** False

## G4/G5
- Env CLAUSEWITZ_ALLOW_POST=1 in Post process only then cleared
- Marker research/safe_land_tool_gate.OPEN (Move 1402 + Strategic 4753) then unlinked
- allow_post: env-only False → env+marker True → restored False

## G6 Move
- Factory 1402 / calling/move_order.py
- Dry-run IsValid HIT: army 1042 @ province 6906 → dest 3931
- Live Post: POSTED_DEST_NOT_IN_PATH with post_wait=258 (WAIT_TIMEOUT); post_rax=0; path []; province unchanged
- Observe deltas (seq+3, drain+13) treated as ambient, not acceptance

## Path C
estimate_after=~71-73%; crossed_70=True; live Move Post not proven

*Phase 2ijw — 2026-11-01 22:26 Asia/Shanghai*
