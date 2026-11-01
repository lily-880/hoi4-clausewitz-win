# Phase 2ija — longer 1x advance → CONTINUOUS + multi_n PATH200 (NON-Post)

**Result:** `PATH200_LONGER_ADVANCE_MULTI_N_HIT`  
**allow_post:** False · **Speed:** 1x CLI mem untouched · never 5x

## Calendar

| | s0 | s1 (300s wall @1x) |
|--|----|---------------------|
| day_index | 51 | **74** (+23) |
| ui | 1936-02-21 | **1936-03-15** |
| clock_class | (crossing) | **CONTINUOUS** |
| drain / exec | 43804 / 15319 | 63995 / 21207 |
| pid / WS | 31788 | 31788 ~1.7GB (healthy) |

## PATH200 denser (vs 2iz)

| Metric | 2iz | 2ija |
|--------|-----|------|
| nonempty / **multi** | 3 / **0** | **15 / 2** |
| new_dests | 1903 | **415, 740, 2601, 3938, 3945, 6906, 9764, 11707** |
| new_ois | 58 | **65, 448, 450, 478** |
| by_class | focus_oi_seed + path_only | path_only×17 |
| inst_ok_ois | [] | [] |

Multi-prov PATH rows present (multi_n=2). Inst70/ARR88 still empty — PATH≠Inst honesty stands. OG+0x50 name STUBBED.

## Artifacts

- `scripts/phase2ija_path200_longer_advance.py`
- `reports/phase2ija_path200_longer_advance.json` + `_summary.json`
- Folded LAND_POST / SAFE_POST §6f catalog

## Stubbed / HARD_DENY (unchanged)

ring_embed · Assign · midflight · Instant-map/empty re-polls · 2fb/2gk · ALLOW_POST · Post inject · 5x · speed-mem write · invent OG+0x50 name · Capstone/121

## Next shortest blocker

Inst still empty on path OIs; human midflight CMove or SAFE Post/ring_embed still NO ALLOW_POST; denser Instant×PATH when Instant appears; push origin if lagging.
