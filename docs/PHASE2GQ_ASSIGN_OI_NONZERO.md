# Phase 2gq — Assign order_index≠0 ↔ OG+0x50 MI confirm (RO)

**Result:** `ASSIGN_QUIET_OG50_CATALOG_POLISH`
**Live:** pid 30352 · 1936-01-08 21:00 · hours=189 · tag=15 · @1x
**Observe:** 90.01s · polls≈1780 · Assign=0 · Unassign=0 · nonzero_oi=0
**B polish:** OG+0x50 ≡ CArmy+0xB8 walkback **294/294** (reaffirm 2gp)

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Method

1. Preferred **A**: ≤90s pending/stage observe for Assign/Unassign with `order_index≠0`; resolve type-0x35 OG / Instance; cross units type=51 → CArmy+0xB8 ∈ OG+0x50.
2. Preferred **B** (A quiet): catalog polish — re-count walkback `elem−0xB8` → primary VT; no new demangled name.

## Semantics (this window)

- **Honest empty on A:** no Assign/Unassign on pending/stage; cannot confirm units↔OI for nonzero `order_index`.
- **B solid:** membership proxy unchanged — `COrdersGroup+0x50[i] == CArmy+0xB8` (VT `0x29d6fb8`), 294/294.
- Prior 2gp Assign sight had `order_index=0` (unset) — still not elevated to valid OI.

## Works

- Bounded Assign oi≠0 hunt (honest quiet)
- OG+0x50 MI catalog reaffirm 294/294

## Stubbed / HARD_DENY

- Assign units↔OI with `order_index≠0` proven in OG+0x50 this window
- demangled +0x50/MI name · named `movement_dest` · ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk · CMove midflight hex

**Next shortest blocker (NON-Post):** denser plan-churn Assign oi≠0 sight **OR** human midflight CMove hex / SAFE Post for ring_embed; push when GitHub reachable; still **NO ALLOW_POST**.

Script: `scripts/phase2gq_assign_oi_nonzero.py`
Reports: `reports/phase2gq_assign_oi_nonzero.json`, `reports/phase2gq_summary.json`

*Phase 2gq · 2026-10-31 15:45 Asia/Shanghai*
