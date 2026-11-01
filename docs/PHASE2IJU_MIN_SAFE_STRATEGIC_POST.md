# Phase 2iju — Minimum safe Strategic Post (G4→G5→G6)

**Result:** `G6_STRATEGIC_POST_HIT`  
**Authorization:** user t52u / pt52u  
**Speed:** pause/1x only — NEVER 5x

## G4 — CLAUSEWITZ_ALLOW_POST=1

- Set via `os.environ['CLAUSEWITZ_ALLOW_POST']='1'` in the Post Python process.
- Env alone: allow_post **False** (marker required).

## G5 — Strategic-only tool-gate

- Created `research/strategic_only_tool_gate.OPEN`
- `config.allow_post()` returns True only when env=1 AND marker present
- Checklist `command_queue_tool_gate` → OPEN_STRATEGIC_ONLY for the shot
- Scope: Strategic Redeploy only; NEVER_POST families still forbidden

## G6 — ONE Strategic Redeploy

- Factory idx **4753** / RVA `0x13FB580` via `calling/strategic_order.py`
- Source army: 1042 province 6841
- Chosen: {'ok': True, 'result': 'DRY_RUN_VALID', 'army': 1042, 'province': 3986, 'path_before': [9767, 3938, 858, 9881, 6832]}
- Post result: {'ok': True, 'result': 'PATH_CONTAINS_DEST', 'army': 1042, 'province': 3986, 'post_rax': 1, 'path_before': [9767, 3938, 896, 3986], 'path_after': [9767, 3938, 896, 3986]}
- Observe: {'pre': {'pid': 31788, 'year': 1937, 'day_index': 22, 'ui_date': '1937-01-23', 'clock_class': 'CONTINUOUS', 'drain': 331897, 'exec': 82404, 'pending': 0, 'stage': 0, 'gate725': 1, 'seq': 82537, 'allow_post': True}, 'src_pre': {'index': 1042, 'army': '0x19fc683ef50', 'province': 6841}, 'immediate': {'pid': 31788, 'year': 1937, 'day_index': 22, 'ui_date': '1937-01-23', 'clock_class': 'CONTINUOUS', 'drain': 332079, 'exec': 82476, 'pending': 0, 'stage': 0, 'gate725': 1, 'seq': 82609, 'allow_post': True}, 'src_immediate': {'index': 1042, 'army': '0x19fc683ef50', 'province': 6841}, 'later': {'pid': 31788, 'year': 1937, 'day_index': 23, 'ui_date': '1937-01-24', 'clock_class': 'CONTINUOUS', 'drain': 332307, 'exec': 82600, 'pending': 0, 'stage': 0, 'gate725': 1, 'seq': 82733, 'allow_post': True}, 'src_later': {'index': 1042, 'army': '0x19fc683ef50', 'province': 6841}, 'drain_delta': 182, 'exec_delta': 72, 'seq_delta': 72, 'province_changed': False, 'path_before': [9767, 3938, 896, 3986], 'path_after': [9767, 3938, 896, 3986]}

## Gate restore

After one-shot: env cleared, marker removed, checklist re-closed. final allow_post=False.

## Path C honesty

estimate_after=~70-72%; crossed_70=True

*Phase 2iju — 2026-11-01 Asia/Shanghai*
