# Phase 2fh — bounded ETH path-vector re-observe

**Result:** `PATH_EMPTY_LEAF_SIGHT_EMPTY`  
**Base:** `aedb230` (2fg) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb recipe **NOT executed**

## A) Path poll (bounded — preferred)

| | |
|---|---|
| window | **75.0s** @ 2.0s interval |
| polls | 37 · elapsed 75.16s |
| ETH CArmy subjects | 17 per poll |
| nonempty path armies | **0** |
| first_hit_at | none |

Honest empty — no invent. No endless poll.

## B) Leaf sight (fallback after empty paths)

| | |
|---|---|
| window | 30.0s @ 0.05s |
| polls | 594 |
| focus names seen | **[]** (Cancel / SupportAttack / Move / Strategic / CancelRunningAway) |
| focus samples | 0 |

## Live (Asia/Shanghai wall ≈ 2026-10-31 12:08)

- pid **9928** · UI **1936-01-05 19:00** · hours≈115 · ETH tag=15 · speed policy pause-or-1x only
- scenario: `ETH@1x bounded path re-observe (no Post)`

## Works / stubbed

**Works:** bounded path poll 75s; nonempty=0 documented; allow_post stays False; fallback leaf sight 30s focus=[].

**Stubbed (unchanged):** in-process ring embed · 2fb recipe exec · ordinary CMove live leaf · SAFE_POST/ALLOW_POST · self-MOVE · tool-gate open · Post inject · path-vector nonempty (reconfirmed empty this window).

## Next shortest blocker (NON-Post)

RO ceiling on midflight path/leaf this peacetime ETH window — next cheapest: **pause+1x war-dense relaunch observe** OR catalog-only retreat/attack field polish; still **NO ALLOW_POST**.

Script: `scripts/phase2fh_path_reobserve.py`  
Reports: `reports/phase2fh_path_reobserve.json`, `reports/phase2fh_summary.json`
