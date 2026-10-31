# Phase 2gr — Denser Assign oi≠0 churn (RO)

**Result:** `ASSIGN_QUIET_DENSE_OG50_CATALOG_POLISH`
**Live:** pid 30352 · 1936-01-09 21:00 · hours=213 · tag=15 · @1x
**Clock nudge:** waited 7.02s · hours 205→206 · ticked=true (wait-only; never write speed)
**Observe:** 90.01s · Assign=0 · Unassign=0 · nonzero_oi=0 · heap_scans=4
**B polish:** OG+0x50 ≡ CArmy+0xB8 walkback **375/375** (oi 1..127; was 294 @1..95)

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Method

1. Preferred **A**: brief 1x clock nudge (hours tick wait) then ≤90s pending/stage + bounded Assign/Unassign heap-edge corner; require `order_index≠0` → type-0x35 OG / Instance; cross units type=51 → CArmy+0xB8 ∈ OG+0x50.
2. Preferred **B** (A quiet): catalog polish — walkback expand oi 1..127; no demangled name.

## Semantics (this window)

- **Honest empty on A:** no Assign/Unassign on pending/stage or heap edge; cannot confirm units↔OI for nonzero `order_index`.
- **Clock did advance** under 1x (205→213 across nudge+observe) — denser plan window still quiet for Assign.
- **B solid:** membership proxy unchanged — `COrdersGroup+0x50[i] == CArmy+0xB8` (VT `0x29d6fb8`), 375/375.

## Works

- Clock-nudge wait-only @1x + bounded heap-edge Assign corner
- OG+0x50 MI catalog expand 375/375

## Stubbed / HARD_DENY

- Assign units↔OI with `order_index≠0` proven in OG+0x50 this window
- demangled +0x50/MI name · named `movement_dest` · ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk · CMove midflight hex · speed write

**Next shortest blocker (NON-Post):** human midflight CMove hex / SAFE Post for ring_embed OR later plan-dense Assign oi≠0 window; push when GitHub reachable; still **NO ALLOW_POST**.

Script: `scripts/phase2gr_assign_oi_dense.py`
Reports: `reports/phase2gr_assign_oi_dense.json`, `reports/phase2gr_summary.json`

*Phase 2gr · 2026-10-31 15:50 Asia/Shanghai*
