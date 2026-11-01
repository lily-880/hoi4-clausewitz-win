# SAFE_LAND_POST — Path C 阶段验收折页（2026-11-02）

**Gates：** 默认 CLOSED / `allow_post=False`；无 `safe_land_tool_gate.OPEN`。Post 仅在显式开闸窗口内。  
**Speed：** pause/1x only；NEVER 5x。  
**Path-C：** ~99%；crossed_70=YES；durable stack≥2 **关闭**；attack-dest pocket **开放**；Retreat **PARKED**。

演示与关闸步骤：`DEMO_TOMORROW.md` / `DEMO_READY.md`。

---

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


## Phase 2iki (t52u Asia/Shanghai)

- Result: G6_MULTI_ATTACK_CONCENTRATE_HIT

- Primary B: bounded arrive-poll (~8s) ¡ª movers 1037/1038 NOT at 6906; anchor 1042 AT 6906 ¡ú gate open

- Multi SupportAttack 3620: 1042@6906 + 1037 ¡ú prior HIT dest 1886 ¡ú ATTACK_POSTED_STABLE x2 (post_rax=1)

- Retreat: HARD_DENY_PARKED_NOT_PROVEN_CHEAP (no retreat_order.py)

- Instant PARKED; combat densify HONEST_EMPTY; adjacency HONEST_EMPTY

- Stability ~30s responding_stayed=True alive_final=True heap_exit=False

- Gates restored allow_post False markers absent

- Path-C estimate ~96¨C98%; crossed_70=YES


## Phase 2ikj (t52u Asia/Shanghai)

- Result: G6_ENCIRCLE_OBSERVE_STATIC_HONEST / ATTACK_POSTED_STATIC_HOLD

- Primary A: bounded RO observe ~40s after 2iki multi-Attack ¡ª 1042@6906 hold; 1037@3931; 1038@11838; paths empty; no co-location at 1886; combat densify HONEST_EMPTY; no pocket evidenced

- Retreat HARD_DENY_PARKED; Instant PARKED; Posts=0; gates stayed False

- Stability OK; Path-C ~96¨C98% (honesty fold, no invent bump)


## Phase 2ikk (t52u Asia/Shanghai)

- Result: G6_WARTIME_ENCIRCLE_LOOP_HIT

- Fresh ETH wartime rebuild: Strategic 4753 movers 1037+1038 ¡ú 6906 HIT¡Á2 (enroute); anchor 1042@6906; Multi SupportAttack 3620 1042+1037 ¡ú 1886 ATTACK_POSTED_STABLE¡Á2

- Arrive: movers_arrived=false movers_enroute=true anchor_at_dest=true; post-obs paths active; combat densify HONEST_EMPTY; no army yet at 1886

- Retreat HARD_DENY_PARKED; Instant PARKED; Post strategic=2 attack=2; gates restored False

- Stability OK; Path-C ~97¨C99%


## Phase 2ikl (t52u Asia/Shanghai)

- Result: G6_LONGER_ARRIVE_STATIC_HONEST

- Longer arrive ~75s: stack_depth=1 (only 1042@6906); movers 1037@3931 / 1038@11838; paths empty; no early stack; Attack refresh NOT warranted (Posts=0)

- Pocket: no army at 1886; combat densify HONEST_EMPTY; Retreat PARKED; Instant PARKED; gates False

- Stability OK; Path-C ~97¨C99% (honesty fold)


## Phase 2ikm (t52u Asia/Shanghai)

- Result: G6_REISSUE_CONCENTRATE_ATTACK_HIT

- Reissue after paths died: Strategic 4753 1037+1038¡ú6906 HIT¡Á2; arrive early-stop stack_depth=2 (enroute+anchor); Multi SupportAttack 3620 from 1038+1042¡ú1886 ATTACK_POSTED_STABLE¡Á2

- Post-obs honesty: provinces 1037@9857 1038@11838 1042@6906; no army at 1886; paths cleared; combat densify HONEST_EMPTY

- Retreat PARKED; Instant PARKED; Posts strategic=2 attack=2; gates False; Path-C ~98¨C99%


## PHASE2IKN (2026-11-02 00:11 Asia/Shanghai)

Gates opened only for optional reissue Strategic+Attack then closed. Durable observe RO. No Retreat/Instant. allow_post restored False.

## PHASE2IKO (2026-11-02 00:22 Asia/Shanghai)
Gates OPEN for Strategic+immediate Attack(+optional Cancel) then CLOSED. Durable RO. allow_post False.

## PHASE2IKP (2026-11-02 Asia/Shanghai) — stack3 Attack-ALL + Cancel hold
- Result: G6_STACK3_ATTACK_ALL_THEN_PEEL HIT=false (honest durable fail)
- Proven: early_stack3 + Attack HIT×3 all stacked (1037/1038/1042→1886); Cancel×6 + re-Strategic×6 mid-hold
- FAIL: peel at Post snap (stack_depth_at_post=1); durable_stack_ge2=false any_at_1886=false; hold_through_attack=false
- hold_stack_depths=[1,1,1,1,2,2,1] brief ge2 only mid-window
- Retreat PARKED; Instant PARKED; allow_post restored False; markers absent; pid 31084 stable WS~1459 Responding
- Path-C ~98-99%; durable pocket still open (+0pp invent-free)
- Docs: docs/PHASE2IKP_STACK3_ATTACK_CANCEL_HOLD.md; script scripts/phase2ikp_stack3_attack_cancel_hold.py

## PHASE2IKQ (2026-11-02 Asia/Shanghai) — Move-hop concentrate then Attack-all
- Result: G6_MOVE_HOP_NO_ATTACK HIT=false (honest — no stack≥2, Attack not issued)
- Proven: Move 1402 HIT×2 PATH_CONTAINS_DEST (1037/1038→6906); SKIP 1042@6906
- FAIL: Move slower than Strategic; AI peeled anchor 1042 before movers arrived; durable_stack_ge2=false any_at_1886=false
- Cancel light×1 + re-Move×1; Strategic fallback=0; Retreat/Instant PARKED; allow_post False; pid 31084 stable
- Path-C ~98-99%; durable pocket still open (+0pp); AI-limited soft-fail option noted
- Docs: docs/PHASE2IKQ_MOVE_HOP_ATTACK_ALL.md; script scripts/phase2ikq_move_hop_attack_all.py

## PHASE2IKR (2026-11-02 Asia/Shanghai) — hybrid Strategic + anchor-Cancel + Attack-all
- Result: G6_HYBRID_DURABLE_HIT HIT=true (durable_stack_ge2 held across Attack Post + observe)
- Live retarget: 1037 gone; TRACK 1038/1045/1042; concentrate 7213; Attack 1886
- Proven: Strategic HIT×1 + SKIP×2; Attack HIT×2 @stack2; hold_through_attack=true; durable early_stop=DURABLE_STACK_GE2
- any_at_1886=false (pocket-at-attack-dest still open); Retreat/Instant PARKED; allow_post False; pid 31084
- Path-C ~99%; +~0-1pp invent-free durable stack hold
- Docs: docs/PHASE2IKR_STRATEGIC_ANCHOR_PEEL_ATTACK.md; script scripts/phase2ikr_strategic_anchor_peel_attack.py

