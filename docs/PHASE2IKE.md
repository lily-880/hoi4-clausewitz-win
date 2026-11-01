# PHASE2IKE

## PHASE2IKE — wartime Move→Attack→Cancel agent loop (HIT) — 2026-11-01 23:20 Asia/Shanghai

**Result:** G6_LOOP_MOVE_ATTACK_CANCEL_HIT HIT=true on army **1037** under WARTIME_ETH_CONTINUATION.

| Step | Post | Evidence |
|------|------|----------|
| Move 1402 | ucrt_malloc province_arr | PATH_CONTAINS_DEST dest=11838 post_wait=0 post_rax=1 |
| Attack 3620 | inline handle@+0x28 province@+0x30 | ATTACK_POSTED_STABLE target=1886 post_wait=0 post_rax=1 |
| Cancel 1415 | ucrt units Qii | PATH_CLEARED_ALL path_before=[11838] path_after=[] post_wait=0 post_rax=1 |

**Stability:** responding_stayed=True alive_final=True heap_exit=False (~30s observe). Game left pid largest-WS Responding @1x/pause.
**Gates:** allow_post restored False; research/safe_land_tool_gate.OPEN absent.
**Instant:** PARKED (no empty poll / Instant×PATH densify).
**Combat densify:** HONEST_EMPTY_PATH_PROVINCE — no invent org/str/adjacency.
**Post attempts this slice:** Move=1 Attack=1 Cancel=1 Strategic=0.
**Path-C estimate:** ~88–90% (crossed_70=YES; +~2pp agent loop after multi-Attack ~86–88%).
**Script:** scripts/phase2ike_move_attack_cancel.py; reports/phase2ike_move_attack_cancel_summary.json.

