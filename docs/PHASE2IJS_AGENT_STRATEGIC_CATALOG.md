# Phase 2ijs — Agent card + Strategic-only recipe catalog (RO)

**Result:** `AGENT_STRATEGIC_CATALOG_HIT`  
**allow_post:** False (never flipped)  
**Live:** pid=31788 ITA ui=1936-11-25 day=329 clock=CONTINUOUS drain=282032 exec=70994  
**HEAD:** b6d443b

## Agent card (consumption)

- Folds **2ijr** stack-encircle: armies=58 → provinces=37; multi=18; max_stack=3; concentration≈0.6724; adjacency=HONEST_EMPTY
- Live refresh: armies=58; handle_ok=58; province_id_ok=58; all_subject_ok=True
- Proven fields only: CA_HANDLE / CA_PROVINCE_ID / CA_COUNTRY_TAG / CA_PROVINCE_PTR / CP_ID / HANDLE_TYPE_ARMY=0x33

## Strategic-only recipe catalog

- Family: Strategic ACCEPTABLE (G1); samples=5; cancel-batch sample included
- MoveAction documented (path vectors need game allocs — do NOT WPM hand-wave)
- **posting DISABLED** until human G4 → G5 → G6

## Gates G1–G6 (crisp)

| Gate | State | Agent note |
|------|-------|------------|
| G1 | ACCEPTABLE | Strategic-only when Post opens |
| G2 | RO_PREP_HIT / live STUBBED | ring_embed live blocked |
| G3 | PARKED | Instant peacetime — do not poll |
| G4 | HARD_DENY_UNTIL_HUMAN | CLAUSEWITZ_ALLOW_POST=1; executor cannot flip |
| G5 | CLOSED_NOT_OPENED | tool-gate after G4 |
| G6 | FORBIDDEN_NOW | ONE Strategic Post @1x after G4+G5 |

## Stubbed / not invented

- Theater/frontline live handles STUBBED
- CProvince+0x58 controller_tag hypothesis_strong — not proven
- org/str @0x520/0x6ec HYPOTHESIS_ONLY
- Province adjacency HONEST_EMPTY

## Path C honesty

~60–62% baseline; this slice **0pp** catalog; **~70% NOT crossed**.

## Next

Human G4 → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x.

*Phase 2ijs — 2026-11-01 Asia/Shanghai*
