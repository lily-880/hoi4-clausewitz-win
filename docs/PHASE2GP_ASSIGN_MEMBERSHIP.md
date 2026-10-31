# Phase 2gp — Assign-stage membership + OG+0x50↔CArmy MI (RO)

**Result:** `ASSIGN_SIGHT_PLUS_OG50_MI_HIT`
**Live:** pid 30352 · 1936-01-07 12:00 · hours=156 · tag=15 · @1x
**Observe:** 90.01s · polls=1781 · Assign=1 · Unassign=1
**OG+0x50 membership:** elem ≡ **CArmy+0xB8** (VT `0x29d6fb8`) — walkback **292/292** any-CArmy; ITA-filtered trusted links **1** (army 1049 @ oi 48)
**Assign units:** type=51 indices **445, 410** resolve live ITA CArmy (tag=15); `order_index=0` **unset/not claimed** as valid OI

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Method

1. Preferred **A**: bounded ≤90s pending/stage observe for Assign/Unassign; decode units `{type,index}`.
2. Preferred **B**: build live CArmy MI map (VT `0x29d6f48` @+0x10, `0x29d6fb8` @+**0xB8**); cross each OG+0x50 ptr vs MI/primary; walkback `elem−0xB8` → primary VT.
3. Enrich: widen army index 400..1600; fix MI delta **0xB8** (missed in initial 8-aligned list that skipped 0xB8).

## Semantics (this window)

- **Proven proxy:** `COrdersGroup+0x50[i]` points at **CArmy MI subobject @ +0xB8** (VT `0x29d6fb8`); `elem+0x08→OG*`, `elem+0x20→Instance*` (reconfirmed).
- Walkback identity **292/292** across wide OIs — army↔OG membership readable without Post.
- Assign/Unassign **sighted** on ITA stage; units are real ITA armies; Assign `order_index=0` not treated as OG link.
- Extends 2fv/2fw (+0x50 MI-shaped, primary walk-back empty when 0xB8 omitted).

## Works

- Bounded Assign/Unassign observe with unit decode
- OG+0x50 ↔ CArmy+0xB8 MI membership (structural + ITA sample)
- Assign unit resolve for ix 410/445

## Stubbed / HARD_DENY

- demangled field name for +0x50 / MI (proxy only)
- Assign `order_index=0` → valid OI claim
- named `movement_dest` · ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk execute · CMove midflight hex

**Next shortest blocker (NON-Post):** confirm Assign units↔OI when `order_index` nonzero **OR** human midflight CMove hex / SAFE Post for ring_embed; push when GitHub reachable; still **NO ALLOW_POST**.

Script: `scripts/phase2gp_assign_membership.py` (+ `scripts/_phase2gp_enrich.py`)
Reports: `reports/phase2gp_assign_membership.json`, `reports/phase2gp_summary.json`

*Phase 2gp · 2026-10-31 15:40 Asia/Shanghai*
