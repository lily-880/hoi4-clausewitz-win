# Phase 2gm — CArmy path / movement_dest + Instance field RO

**Result:** `CARMY_PATH_INSTANCE_RO_PLUS200_MULTI_HIT`  
**Live:** pid 30352 · 1936-01-04 22:00 · hours=94 · tag=15 (ITA)  
**Path:** raw nonempty 9/9 · **true multi after tag-filter 2** (both @ `CArmy+0x200`) · poll 0.03s / 1 tick  
**Instance seed OK:** 14 · +0x70 shaped **8** · +0x88 CProvince **8** · +0xe0/+0x100 empty this sample  

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Offline field catalog (perception map)

### COrderInstance

| off | kind | status | role |
| --- | --- | --- | --- |
| `0x70` | `CPdxArray<u32>` | **PROVEN** | ordered province ids for order/front path (NOT army midflight movement_dest) |
| `0x88` | `CPdxArray<CProvince*>` | **PROVEN** | hub/neighbor province ptr pairs over +0x70 prefix |
| `0xe0` | `CPdxArray<u32>` soft/candidates | **PROVEN_SOFT** | u32 stream; often empty |
| `0x100` | packed twin / soft VT `0x2794550` | **PROVEN_SOFT** | twin/soft; not demangled movement_dest |

### CArmy path / movement_dest

| field | status | role |
| --- | --- | --- |
| `CArmy+0x200` CPdxArray\<u32\> multi | **CANDIDATE_HIT (2gm)** | multi-province streams (n=12, n=8) on ITA armies 1039/1042 — path-like / order-linked; **not** demangled `movement_dest` |
| `CArmy+0x3e0` / `+0x400` singleton | **FALSE_POSITIVE** | often `[country_tag]` (15) — **filter out**; not a path |
| stdvec/CPdx u32 scan @+0x40..0x780 | **CANDIDATE_SCAN** | province-shaped vectors; peacetime often empty or tag FPs |
| named `movement_dest` | **NOT_DEMANGLED** | do not invent destinations |

## Live hits (honest)

- **+0x200 multi:** army 1039 @11793 → 12 ids; army 1042 @6993 → 8 ids (overlap tails e.g. 726, 3729).
- **Instance+0x70:** 8/14 seed OIs province-shaped (e.g. oi13 n=26; oi22 n=10).
- **Instance+0x88:** matching CProvince* hubs on those 8.
- **+0xe0 / +0x100:** empty/None this sample.

## Works

- Offline Instance+CArmy perception field catalog (proven vs candidate)
- Bounded ≤60s ITA CArmy path-vector RO deepen (stopped early on multi hit)
- Tag-singleton FP classification (`+0x3e0`/`+0x400`)
- Seed-OI Instance +0x70/+0x88/+0xe0/+0x100 sample

## Stubbed / HARD_DENY

- named demangled `movement_dest`
- in-process ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk execute
- CMove midflight hex · Post inject · ask-user right-click

**Next shortest blocker (NON-Post):** deepen `CArmy+0x200` vs `Instance+0x70` cross **or** human midflight CMove hex / SAFE Post for ring_embed; retry GitHub push when auth reachable — still **NO ALLOW_POST**.

Script: `scripts/phase2gm_carmy_path_instance_ro.py`  
Reports: `reports/phase2gm_carmy_path_instance_ro.json`, `reports/phase2gm_summary.json`

*Phase 2gm · 2026-10-31 Asia/Shanghai*
