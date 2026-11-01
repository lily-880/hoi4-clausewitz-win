# Phase 2iz — 1x advance → denser PATH200 (NON-Post)

**Result:** `PATH200_ADVANCE_MULTI_HIT`  
*(name = new_dest / third path-army densify; **multi_n still 0** — no multi-prov PATH row)*  
**allow_post:** False · **Speed:** 1x CLI mem untouched · never 5x

## Calendar advance

| | s0 | s1 (after 150s wall @1x) |
|--|----|---------------------------|
| day_index | 24 | **36** (+12) |
| ui | 1936-01-25 | **1936-02-06** |
| drain | 21005 | 31129 |
| exec | 10597 | 12770 |
| pid | 31788 | 31788 |

WS during slice: ~0.8→1.6 GB (recovered; not softlock 238MB class). Calendar_ok=True.

## PATH200 denser (vs 2iy)

| Metric | 2iy | 2iz |
|--------|-----|-----|
| nonempty / multi | 2 / 0 | **3 / 0** |
| dests | 9945, 12857 | + **1903** |
| OIs | 45@1053, 55@1040 | + **58@1041** →[1903] |
| by_class | path_only×2 | focus_oi_seed×2 + path_only×1 |
| inst_ok_ois | [] | [] |
| Inst70/ARR88 × PATH | empty | empty |

PATH vs Inst70 drift honesty: PATH nonempty without Instant VT on same OI — do not treat PATH dest as Instant-validated order.

## Artifacts

- `scripts/phase2iz_path200_advance_dense.py`
- `reports/phase2iz_path200_advance_dense.json` + `_summary.json`
- Folded LAND_POST / SAFE_POST §6f catalog

## Stubbed / HARD_DENY (unchanged)

ring_embed · Assign · midflight · Instant-map/empty re-polls · 2fb/2gk · ALLOW_POST · Post inject / historical 2iw–2iy Post · 5x · speed write beyond pause/1x · invent OG+0x50 name · Capstone/121

## Next shortest blocker

Still no multi-prov PATH (multi_n=0); Instant empty on 45/55/58. Longer CONTINUOUS / later date / human midflight CMove; SAFE Post/ring_embed still NO ALLOW_POST.
