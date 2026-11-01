# Phase 2ijp — ITA army→province occupancy map RO

**Result:** `ARMY_PROVINCE_MAP_RO_HIT`  
**allow_post:** **False** · Post **NOT** called · Instant **PARKED** · never 5x

## Live clock / queue

pid 31788 · CONTINUOUS · day_index=291 ui=1936-10-18 ·  
drain=249519 exec=63856 pending=0 · calendar_ok=True

## Army → province map (proven fields only)

- armies=58 · handle_ok=58 · province_id_ok=58
- province_ptr@+0x1F0 match=58/58 · CP_ID@+0xA4 match=58/58
- unique_provinces=37 · singleton=19 · multi_army=18 · max_stack=3
- Proven used: CA_HANDLE / CA_PROVINCE_ID / CA_COUNTRY_TAG / CA_PROVINCE_PTR / CP_ID
- Co-location clusters exported for encirclement-bias perception (RO only)

## Honest STUBBED / NOT invented

- Theater/frontline **live handles** STUBBED (only HANDLE_TYPE_ARMY=0x33 proven)
- CProvince+0x58 controller_tag remains hypothesis_strong (2ct) — **not** fed as proven
- CArmy+0x520/+0x6ec org/str remain HYPOTHESIS_ONLY — **not** invented

## G1–G6

| Gate | State |
| --- | --- |
| G1 | ACCEPTABLE Strategic-only |
| G2 | RO prep HIT · live STUBBED |
| G3 | PARKED |
| G4 | HARD_DENY until human |
| G5 | CLOSED_NOT_OPENED |
| G6 | FORBIDDEN now |

## Path C honesty (t50u)

~60–62% baseline; occupancy-map perception ≤+1–2pp, **not** +10pp. **~70% NOT crossed.**

## Next

Human G4 → G5 → G2 live / G6. No densify/poll churn.

*Phase 2ijp · 2026-11-01 Asia/Shanghai*
