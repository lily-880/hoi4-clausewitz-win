# Phase 2gg — ITA relaunch multi-leaf observe + Execute leaf polish

**HEAD parent:** `c8030fb` (2gf)  
**Result:** `ita_multi_leaf_empty`  
**allow_post:** False (never opened)

## What ran

Preferred **A**: fresh ITA relaunch via `launch_into_map.py --start-tag ITA --speed 1 --allow-ai`, map wait (~35s), then bounded **90.02s @1x** pending/stage observe for:

- Assign / Unassign / Execute / Delete  
- NF / RF  
- CMove (`0x2a2c790`) / SupportAttack (if catalogued)

Preferred **B** (A empty): Execute `order_index` leaf packing polish from 2fn/2ft maps — **no Capstone**.

## Live

| field | value |
|-------|-------|
| pid | 30352 |
| hours | 0 → **7** |
| UI | 1936-01-01 00:00 → **1936-01-01 07:00** |
| speed | 1x only (never 5x) |
| scenario | ITA day-1 relaunch AI-on multi-leaf |
| cmdline | `-gdpr-compliant -start_tag=ITA -start_speed=1` |
| map_wait | ~35s · carmy ready |

## Honest outcome (A)

- Assign / Unassign / Execute / Delete / NF / RF / CMove / SupportAttack: **all 0**  
- `sight_counts`: `{}`  
- Same quiet class as ETH 2gf/2ge/2gd day-1 windows. Do not invent.

## Execute leaf polish (B)

| item | value |
|------|-------|
| vt | `0x2a85468` |
| type_id | `0x3040` |
| factory_idx | **3352** |
| isvalid | `0x18def40` |
| execute | `0x18d6430` |
| order_index | **+0x30** (u32) |
| execute_order | **+0x34** (u8) |
| all | **+0x35** (u8) |

oi↔type-**0x35** same class as Assign (2ft/2fp). Delete: `order_index@+0x30` only (factory_idx 3351).

**Delta:** documentation consolidation — no new Capstone RVA.

## Works

- allow_post False; never 5x; no Post / inject / tool-gate / 2fb / Capstone  
- ITA relaunch @1x AI-on + map-ready  
- Bounded multi-leaf observe (honest empty)  
- Execute order_index leaf polish table

## Stubbed

ring embed · 2fb · SAFE_POST · self-MOVE · tool-gate · Post · HourlyTick · Capstone/121 · named +0x100/+0xe0 · RTTI 0x29d6fb8 · CArmy path · **live midflight Assign/Unassign** · **live midflight NF** · **ordinary CMove/SupportAttack leaf**

## Next shortest NON-Post blocker

ITA day-1 multi-leaf also quiet — **longer ITA war-day observe** (hours≫7, still ≤90s slices) **or** heap/stage corner for lingering Assign; **still NO ALLOW_POST**.

## Artifacts

- `scripts/phase2gg_ita_relaunch_observe.py`
- `reports/phase2gg_summary.json`
- `reports/phase2gg_ita_observe.json`
