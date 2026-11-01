# Phase 2ijr — Stack-depth / encirclement-bias perception (RO)

**Result:** `STACK_ENCIRCLE_BIAS_RO_HIT`  
**allow_post:** False (never flipped)  
**Live:** pid=31788 ITA ui=1936-11-16 day=320 clock=CONTINUOUS drain=274715 exec=69396

## What this adds

- Ranked province stacks by depth (proven CA fields only).
- Concentration ratio = armies in multi-army provinces / total armies.
- Stack-depth histogram + top multi-army clusters.
- Strategic/Cancel recipe catalog for top stacks — **posting DISABLED**.
- Province adjacency graph: **HONEST_EMPTY** (not invented).

## Proven fields only

| Field | Offset |
|-------|--------|
| CA_HANDLE | +0x18 |
| CA_PROVINCE_ID | +0x28 |
| CA_COUNTRY_TAG | +0x1E0 |
| CA_PROVINCE_PTR | +0x1F0 |
| CP_ID | +0xA4 |
| HANDLE_TYPE_ARMY | 0x33 |

## Live snapshot

- armies=58 unique_provinces=37 multi=18 max_stack=3
- concentration_ratio=0.6724
- handle/province/ptr/cp_id match: 58/58/58/58 of 58

## Gates G1–G6

- G1 ACCEPTABLE Strategic-only
- G2 RO prep HIT / live STUBBED
- G3 Instant PARKED
- G4 HARD_DENY until human CLAUSEWITZ_ALLOW_POST=1
- G5 CLOSED_NOT_OPENED
- G6 FORBIDDEN now

## Stubbed / not invented

- Theater/frontline live handles STUBBED
- CProvince+0x58 controller_tag hypothesis_strong — not fed as proven
- org/str @0x520/0x6ec HYPOTHESIS_ONLY — not invented
- Province neighbor edges: HONEST_EMPTY

## Path C honesty

~60–62% baseline; this slice ≤+1pp perception polish; **~70% NOT crossed**.

## Next

Human G4 → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x.

*Phase 2ijr — 2026-11-01 Asia/Shanghai*
