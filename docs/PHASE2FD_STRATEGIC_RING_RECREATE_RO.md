# Phase 2fd — Strategic Dummy ring recreate RO

**Result:** `STRATEGIC_OFFLINE_REBUILD_PASS_LIVE_FACTORY_RO_RING_EMBED_STILL_STUBBED`  
**allow_post:** **False** · 2fb recipe **NOT executed** · never 5x

## A) Offline rebuild (harness)

Rebuilt `CStrategicRedeploymentCommand` size `0x50` from catalog offsets + 2fa fields  
(absolute VTs from capture for ASLR).

| check | value |
|-------|-------|
| status | **PASS** |
| bit_identical | True |
| army_handle | [51, 1092] |
| province | 11874 |
| clear / move_priority | 1 / 2 |
| embed type_id | 0x364a |

## B) Live factory / recreate wiring (RO)

| check | value |
|-------|-------|
| type_id | `0x35b9` |
| factory_idx formula | 4753 (catalog factory_idx 4505 STALE) |
| table slot RVA | 0x13fb580 |
| catalog factory | `0x13fb580` |
| slot match | True |
| recreate `0x22d8ad0` readable | True |
| gettypeid imm match | True |
| action ser tokens | True |

Birth path (observe only): GetTypeId(0x35b9) → ser → recreate(0x22d8ad0) → factory_lookup idx=4753 → factory 0x13fb580 → vt+0x18 des → ring@+0xa0

## C) Harness gap (STOP ceiling)

**In-process** serialize→recreate→ring embed still **STUBBED** — requires Post/sink write.  
Not done this slice. No Capstone/121. No endless-poll.

Dummy ring RO snapshot: pending=0 execlist=0 seq=15146

## Next

Offline PASS + live factory RO is the proof ceiling without Post.  
Any real ring push waits on SAFE human enable — **still NO ALLOW_POST**.

Artifacts: `reports/phase2fd_*.json`, `scripts/phase2fd_strategic_ring_recreate_ro.py`
