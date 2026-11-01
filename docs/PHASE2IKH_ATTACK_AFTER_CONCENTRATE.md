# Phase 2ikh — Attack after concentrate (Retreat HARD_DENY)

**Result:** G6_ATTACK_AFTER_CONCENTRATE_HIT HIT=True
**Primary:** B | Retreat HARD_DENY_PARKED_NOT_PROVEN_CHEAP
**Army 1042** @ 6906 (concentrate anchor at 6906) → SupportAttack 3620 target **1886**
**Post:** ATTACK_POSTED_STABLE post_rax=1 post_wait=0
**Stability:** {'seconds': 30.0, 'responding_stayed': True, 'alive_final': True, 'heap_exit': False, 'samples_n': 30}
**Arrive RO:** movers 1037/1038 not at dest; anchor 1042 yes.
**Gates:** allow_post=False; Instant PARKED.
**Path-C:** ~94-96%; +~2pp Attack from concentrate-anchor army

*2026-11-01 23:31:30 Asia/Shanghai*


### Fold (2026-11-01 23:31 Asia/Shanghai)

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

