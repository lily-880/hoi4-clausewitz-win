# Phase 2fk — war-dense ITA relaunch observe

**Result:** `PATH_EMPTY_LEAF_SIGHT_EMPTY`  
**Base:** `a879908` (2fj) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb recipe **NOT executed**

## Relaunch (preferred A)

- CLI: `-gdpr-compliant -start_tag=ITA -start_speed=1` (AI on, **no** `-noai`)
- map_wait: ok · **29.0s** · carmy(tag=15)=17 · start UI 1936-01-01 00:00
- new pid **34188** (prior ETH 28492 killed)

## Path / leaf window 1 (GS_PLAYER_TAG=15 filter)

| | |
|---|---|
| window | **75s** @ 2.0s |
| polls | 32 · elapsed ~75.3s |
| nonempty armies | **0** |
| leaf focus | **[]** · sight `CHourlyTickCommand` only |

Note: `GS_PLAYER_TAG@0x518=15` matches `00_countries.txt` ITA index, but only ~17 CArmy rows carry `CA_COUNTRY_TAG==15` (East-Africa-ish provinces). Majors dominate other tags (e.g. tag5=74). Filter alone is insufficient.

## Path / leaf window 2 (ALL CArmy, no tag filter) — same live ITA@1x

| | |
|---|---|
| carmy_all | **873** · top tags (5,48,38,16,10,…) |
| window | **75s** · polls 32 · elapsed **76.39s** |
| nonempty armies | **0** |
| leaf focus | **[]** · sight `CHourlyTickCommand`×23 |
| UI end | **1936-01-02 09:00** · hours≈33 · **1x** |

Honest empty on both windows — no invent.

## RO ceiling (this slice)

Fresh ITA day-1/2 war @1x AI-on produced **no** nonempty movement_dest path-vector and **no** Move/Strategic/SupportAttack/Cancel/Retreat leaf hex in bounded windows (same empty class as 2fj ETH), including all-carmy scan.

## Next shortest blocker (NON-Post)

Catalog **NewFallback subject beyond +0x54** OR Assign/Unassign edge deepen; still **NO ALLOW_POST**.

Script: `scripts/phase2fk_war_dense_observe.py`  
Reports: `reports/phase2fk_war_dense_observe.json`, `reports/phase2fk_summary.json`
