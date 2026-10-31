# Phase 2gd — ETH war-dense relaunch: NF/RF + CArmy path RO

**HEAD parent:** `b3fde92` (2gc)  
**Result:** `war_dense_nf_rf_and_path_empty`  
**allow_post:** False (never opened)

## What ran

Preferred **A**: fresh ETH relaunch via `launch_into_map.py --start-tag ETH --speed 1 --allow-ai`, map wait (~40.5s), then **bounded 75.08s @1x** observe (651 polls).

Targets:

- Midflight NF VT `0x2a84c80` / RF VT `0x2a84d38` (pending + stage + field decode when present)
- CArmy path: catalog soft `+0x2b4` last-path candidate + unnamed path-vector scan (same class as 2fj)

## Live

| field | value |
|-------|-------|
| pid | 14248 |
| hours start→end | 0 → 6 |
| UI | 1936-01-01 00:00 → **1936-01-01 06:00** |
| speed | 1x only (never 5x) |
| scenario | ETH day-1 war-dense AI-on |
| cmdline | `-gdpr-compliant -start_tag=ETH -start_speed=1` |
| counters end | drain=4921 exec=6474 seq=6482 stage_count=0 |

## Honest outcome

- **NF/RF captures:** 0 (sight_counts empty; stage empty; pending had no Fallback VT)
- **path vector nonempty armies:** 0
- **catalog soft 0x2b4 province-shaped hits:** 0 this window
- Same empty class as **2fj** (ETH) / **2fk** (ITA) / **2gc** (peace ITA midflight)

Commands drain/exec advanced (AI issuing other cmds) but **no** NewFallback / ReplaceFallback leaf and **no** nonempty movement path vectors in the 75s window. Do not invent.

## Works

- allow_post False; never 5x; no Post / inject / tool-gate / 2fb / Capstone re-churn
- Relaunch ETH @1x AI-on + map-ready
- Bounded NF/RF + path observe; honest empty documented

## Stubbed (unchanged class)

ring embed · 2fb · CMove leaf · SAFE_POST · self-MOVE · tool-gate · Post · HourlyTick · Capstone/121 · named +0x100 elem beyond allocator · named +0xe0 beyond u32 · demangled RTTI 0x29d6fb8 · **live midflight NF hex (empty this war-dense window)** · **named CArmy path-field offs (empty this window)**

## Next shortest NON-Post blocker

RO ceiling on war-dense NF/path in a bounded day-1 window — longer war-day observe (still ≤90s slices) **or** catalog-only leaf field polish from existing 2fl/2fm map; **still NO ALLOW_POST**.

## Artifacts

- `scripts/phase2gd_war_dense.py`
- `reports/phase2gd_summary.json`
- `reports/phase2gd_war_dense.json`
