# PHASE2IKP — stack=3 Attack-ALL + Cancel mid-hold (durable pocket still open)

HEAD-in: 2cfb4e1 (2iko). Slice: wait Strategic concentrate until stack_depth==3 @6906, IMMEDIATE multi SupportAttack 3620 from ALL three armies (1037/1038/1042) toward PRIOR_HIT dest 1886; Cancel 1415 on diverting paths during Attack hold window + optional re-Strategic; durable observe ~90s.

## Result: G6_STACK3_ATTACK_ALL_THEN_PEEL — HIT=false (honest)

- early_stack3=true; attacked_all3=true; fallback_attack=false
- Strategic: HIT,HIT,SKIP (1042 already@6906)
- Attack: HIT×3 (attackers=[1037,1038,1042]) — Attack-all-three while stacked PROVEN
- attack_moment (~t=29s ui~1936-02-24): stack_depth_at_post=1 already (1037@9896, 1038@6817, 1042@6906) — peel during/immediately after Post
- hold_through_attack=false; hold_stack_depths=[1,1,1,1,2,2,1] — brief ge2 mid-window only, not held across Post into durable
- cancel_n=6 + re_strategic_after_cancel=6 during hold — Cancel ABI exercised; peel persisted (AI diversion)
- durable: durable_stack_ge2=false; any_at_1886=false; final 1037@3931 / 1038@11838 / 1042@6906; combat/adjacency HONEST_EMPTY
- Stability 25s responding_stayed=True alive_final=True heap_exit=False; pid 31084
- Gates restored allow_post=False; markers absent
- Retreat HARD_DENY_PARKED; Instant PARKED; Capstone/121 untouched; Move=0 this slice
- Post attempts: Strategic=2 Attack=3 Cancel=6 (+re-Strategic 6) Move=0 Retreat=0
- Path-C: ~98–99%; crossed_70=YES; +0pp invent-free (Attack-all3-while-stack3 proven; durable pocket still open)

## Evidence vs 2iko
- 2iko: Attack while stack=2 HIT×2; post-snap peel; durable fail
- 2ikp: Attack while stack=3 HIT×3; same peel pattern at Post snap; Cancel mid-hold did not retain durable ge2 / any_at_1886

## Next shortest blocker
- AI peels armies off concentrate dest during/immediately after Attack Post (before hold window can lock stack≥2).
- Options without inventing Retreat/adjacency: shorter Move(1402) hop concentrate then Attack-all; denser Cancel+re-concentrate loop; accept durable pocket as AI-limited for Path-C land agent and move to Capstone only when cheap; OR document durable as soft-fail / observe-only for agent policy.
- Do NOT invent Retreat factory / adjacency / Instant densify.

Script: scripts/phase2ikp_stack3_attack_cancel_hold.py
Report JSON: reports/phase2ikp_stack3_attack_cancel_hold.json (if written) + reports/phase2ikp_run_tee.txt