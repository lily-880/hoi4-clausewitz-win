

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

## PHASE2IKF — wartime Strategic Redeploy 4753 encircle-bias (HIT) — 2026-11-01 23:24 Asia/Shanghai

**Result:** G6_STRATEGIC_WARTIME_ENCIRCLE_HIT HIT=true army **1037** src_prov=3931 dest=11838 (friendly army 1038 province — force-concentration / stack-forming bias).

| Step | Evidence |
|------|----------|
| RO encircle-bias | dest pool = other friendly CA provinces; adjacency HONEST_EMPTY |
| Strategic 4753 | PATH_CONTAINS_DEST post_rax=1; path_before=[11838] path_after=[11838] |
| Stability ~30s | responding_stayed=True alive_final=True heap_exit=False |

**Note:** path_before already contained 11838 (lingering 2ike Move path); Post still IsValid+queue HIT with dest=11838 concentration target.
**Gates:** allow_post False; strategic_only + safe_land markers absent. Instant PARKED. Retreat PARKED_NOT_PROVEN_CHEAP.
**Agent card:** wartime Strategic Redeploy sits beside Move→Attack→Cancel loop as encircle-bias reposition primitive.
**Path-C:** ~90–92% (crossed_70=YES; +~2pp vs 2ike ~88–90%).
**Script:** scripts/phase2ikf_strategic_encircle.py

## PHASE2IKG — multi-army Strategic concentration HIT (Retreat PARKED) — 2026-11-01 23:27 Asia/Shanghai

**Result:** G6_MULTI_STRATEGIC_CONCENTRATE_HIT HIT=true
**Primary choice:** B (Retreat PARKED_NOT_PROVEN_CHEAP — no retreat_order Post ABI; NewFallback/ReplaceFallback/WithdrawArmyHq RO/DISABLED only)

| Army | Strategic 4753 | path_after (tail→dest 6906 anchor 1042) |
|------|----------------|------------------------------------------|
| 1037 | PATH_CONTAINS_DEST | …→6906 (10-prov strategic path) |
| 1038 | PATH_CONTAINS_DEST | …→6906 (10-prov strategic path) |

**Bias:** MULTI_ARMY_FRIENDLY_COLOC_CONCENTRATE onto anchor province 6906; adjacency HONEST_EMPTY.
**Stability ~30s:** responding_stayed=True alive_final=True heap_exit=False.
**Gates:** allow_post False; markers absent. Instant PARKED. Cancel not needed.
**Path-C:** ~92–94% (crossed_70=YES; +~2pp vs 2ikf ~90–92%).
**Script:** scripts/phase2ikg_multi_strategic.py

## PHASE2IKH — Attack after concentrate HIT (Retreat HARD_DENY) — 2026-11-01 23:31 Asia/Shanghai

**Result:** G6_ATTACK_AFTER_CONCENTRATE_HIT HIT=true
**Primary choice:** B (Retreat HARD_DENY_PARKED_NOT_PROVEN_CHEAP — NewFallback 4271 RO/DISABLED; NF midflight empty; no retreat_order.py)

| RO / Post | Evidence |
|-----------|----------|
| Concentrate arrive | 1037@3931 no; 1038@11838 no; **1042@6906 yes** (anchor) |
| SupportAttack 3620 | army **1042** src 6906 → target **1886** ATTACK_POSTED_STABLE post_rax=1 post_wait=0 |
| Stability ~30s | responding_stayed=True alive_final=True heap_exit=False |

**Note:** First friendly-only target pool → NO_ISVALID; retry used prior wartime HIT dest 1886 (IsValid-proven, not adjacency invent).
**Gates:** allow_post False; markers absent. Instant PARKED. Combat densify HONEST_EMPTY.
**Path-C:** ~94–96% (crossed_70=YES; +~2pp vs 2ikg ~92–94%).
**Script:** scripts/phase2ikh_attack_after_concentrate.py
