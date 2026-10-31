# Phase 2fj — war-dense ETH relaunch observe

**Result:** `PATH_EMPTY_LEAF_SIGHT_EMPTY`  
**Base:** `7920ce9` (2fi) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb recipe **NOT executed**

## Relaunch (preferred A)

- CLI: `-gdpr-compliant -start_tag=ETH -start_speed=1` (AI on, **no** `-noai`)
- map_wait: ok · **46.9s** · carmy=17 · start UI 1936-01-01 00:00
- new pid **28492** (prior 9928 killed)

## Path poll (bounded)

| | |
|---|---|
| window | **75.0s** @ 2.0s |
| polls | 37 · elapsed 75.25s |
| nonempty armies | **0** |
| first_hit_at | none |

Honest empty — no invent. Fresh war-start window (hours 0→8) still no CArmy path vectors.

## Leaf sight (fallback)

- window 30s · focus Move/Strategic/SupportAttack/Cancel/Retreat family: **[]**
- sight_counts: `CHourlyTickCommand` only (19) — no land leaf midflight this window

## Live

- pid **28492** · ETH tag=15 · UI **1936-01-01 08:00** · hours≈8 · **1x**
- scenario: ETH war-dense relaunch @1x AI-on bounded path/leaf (no Post)

## RO ceiling (this slice)

Even fresh ETH day-1 war @1x AI-on produced **no** nonempty movement_dest and **no** focus leaf hex in the bounded window (same empty class as 2fh peacetime-late Jan 5).

## Next shortest blocker (NON-Post)

ITA@1x war-dense relaunch observe **or** catalog NewFallback subject wiring beyond +0x54; still **NO ALLOW_POST**.

Script: `scripts/phase2fj_war_dense_observe.py`  
Reports: `reports/phase2fj_war_dense_observe.json`, `reports/phase2fj_summary.json`
