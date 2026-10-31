# Phase 2gt — Non-interactive midflight RO sample

**Result:** `MIDFLIGHT_HONEST_EMPTY`
**Live:** pid 30352 · 1936-01-11 06:00 · hours=246 · tag=15 · @1x
**Observe:** 90.02s · polls=2156 · heap_scans=4 · captures=0
**Hits:** move_hex=0 · cancel_hex=0 · assign_oi≠0=0

**allow_post:** **False** · no ask right-click · never 5x · recipes **NOT executed**

## Method

Pending/stage + bounded heap-edge for CMove / SupportAttack / Cancel / Assign.
No user interaction; no Post.

## Agent-facing (LAND_POST §6c)

Can feed: army locate, +0x200 candidates, Instance+0x70/+0x88, OG+0x50 MI proxy, Assign type=51 resolve when sighted.
Cannot: CMove bit_identical hex (if empty), named dest, Assign oi≠0, ring_embed, Post.

**Next:** NON-Post: human midflight CMove hex / SAFE Post for ring_embed (2gt non-interactive empty) OR later plan-dense Assign oi≠0; push when GitHub reachable; still NO ALLOW_POST

Script: `scripts/phase2gt_midflight_ro_sample.py`
*Phase 2gt · 2026-10-31 15:56 Asia/Shanghai*
