# PHASE2IKR — hybrid Strategic + Cancel-on-anchor-peel + Attack-all (DURABLE STACK HIT)

HEAD-in: 0ab07a2 (2ikq). Slice: Strategic 4753 fast concentrate + Cancel 1415 on anchor peel + re-Strategic; Attack-all stacked → PRIOR_HIT 1886; durable observe.

## Live retarget
- Army **1037 missing** mid-campaign (scan 0–4000). TRACK → **1038, 1045, 1042**; concentrate dest → **7213** (1038+1045 already co-located). Attack dest still **1886** (prior wartime HIT).

## Result: G6_HYBRID_DURABLE_HIT — HIT=true

- Strategic: SKIP,SKIP,HIT (1038/1045 already@7213; 1042 HIT rejoin)
- Attack: HIT×2 attackers=[1038,1045] while stacked @7213 (`stack_depth_at_post=2`)
- early_stack3=false (1042 still enroute @10024); Attack at stack≥2 after ~40s gate
- hold_through_attack=true; hold_after_attack stack_depths all ≥2 across hold window
- durable_observe: durable_stack_ge2=true; early_stop=DURABLE_STACK_GE2; any_at_1886=false
- Cancel×1 + re-Strategic×1 (anchor/divert handling)
- Move=0 (short local adjust not needed after live co-locate)
- Stability 25s responding_stayed=True alive_final=True heap_exit=False; pid 31084
- Gates restored allow_post=False; markers absent
- Retreat HARD_DENY_PARKED; Instant PARKED; Capstone/121 untouched
- Post attempts: Strategic=1 Attack=2 Cancel=1 (+re-Strategic 1) Move=0 Retreat=0
- Calendar: day stalled @141 during/after run (space taps; pause allowed); game Responding WS stable
- Path-C: ~99% invent-free; crossed_70=YES; +~0–1pp (durable stack≥2 held across Attack Post + observe; pocket-at-1886 still open)

## vs 2ikp / 2ikq
- 2ikp: Strategic stack3 Attack×3 then peel at Post (durable FAIL)
- 2ikq: Move-hop too slow; NO_ATTACK
- 2ikr: hybrid Strategic + live co-locate concentrate; Attack×2; **durable stack≥2 HELD** (not any_at_1886)

## Next shortest blocker
- any_at_1886 / combat pocket still open (Attack posted but armies remained @concentrate)
- Retreat still PARKED
- Capstone/121 when cheap
- Calendar pause/stall watch on long runs

Script: scripts/phase2ikr_strategic_anchor_peel_attack.py
Reports: reports/phase2ikr_strategic_anchor_peel_attack.json + tee