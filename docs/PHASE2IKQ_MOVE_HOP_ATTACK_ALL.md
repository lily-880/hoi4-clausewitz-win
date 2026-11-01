# PHASE2IKQ — Move 1402 hop concentrate then Attack-all (durable pocket still open)

HEAD-in: 57a5501 (2ikp). Slice: shorter Move (not Strategic) hops to concentrate dest 6906 → wait stack≥2/3 → IMMEDIATE multi SupportAttack 3620 ALL stacked → 1886; light Cancel + re-Move only; durable ~90s.

## Result: G6_MOVE_HOP_NO_ATTACK — HIT=false (honest)

- Move 1402: HIT,HIT,SKIP (1037/1038 PATH_CONTAINS_DEST →6906; 1042 already@6906)
- Strategic fallback: 0 (Move dry succeeded)
- Attack: 0 — stack never reached ≥2 within ~100s arrive window
- Evidence: t≈0–22s stack_depth=1 (1042@6906 only) while 1037/1038 enroute (path_len 7–9); then AI peeled 1042 off 6906 before movers arrived; tail stack_depth=0; movers still enroute at timeout
- hold_stack_depths all 0; hold_through_attack=false; durable_stack_ge2=false; any_at_1886=false
- Final provs ~1037@9785 / 1038@13223 / 1042@10024; combat/adjacency HONEST_EMPTY
- Cancel light ×1 + re_move ×1 only (not endless densify)
- Stability 25s responding_stayed=True alive_final=True heap_exit=False; pid 31084
- Gates restored allow_post=False; markers absent
- Retreat HARD_DENY_PARKED; Instant PARKED; Capstone/121 untouched
- Post attempts: Move=3 Attack=0 Cancel=1 Strategic_fallback=0 Retreat=0
- Path-C: ~98–99%; crossed_70=YES; +0pp invent-free (Move-hop concentrate issued; stack/Attack never armed because Move is slower than Strategic + anchor AI-peel)
- AI-limited soft-fail option: durable pocket may be AI-limited for Path-C agent policy (no claim HIT) — Move hop did not beat peel timing

## vs 2ikp
- 2ikp: Strategic → stack3 → Attack×3 HIT then peel at Post
- 2ikq: Move → movers enroute slow; anchor peeled; **no Attack** (NO_ATTACK)

## Next shortest blocker
- Move hops too slow vs AI peel of concentrate anchor before stack forms.
- Invent-free next: hybrid Strategic for concentrate (proven fast stack) + Move only for short local adjust; OR longer arrive wait with Cancel-on-anchor-peel + re-Move/Strategic to hold anchor; OR accept durable as AI-limited soft-fail for Path-C policy.
- Do NOT invent Retreat/adjacency/Instant densify.

Script: scripts/phase2ikq_move_hop_attack_all.py
Reports: reports/phase2ikq_move_hop_attack_all.json + summary + tee