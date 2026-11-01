# Phase 2ikf — Wartime Strategic Redeploy 4753 encircle-bias

**Result:** `G6_STRATEGIC_WARTIME_ENCIRCLE_HIT` HIT=True
**War:** WARTIME_ETH_CONTINUATION
**Speed:** pause/1x only — NEVER 5x
**Authorization:** t52u

## Encircle-bias RO (proven fields only)

- Source army 1037 @ province 3931 (CA+0x28)
- Dest bias: other friendly army provinces (force concentration / stack-forming)
- Adjacency/org/str: HONEST_EMPTY — not invented
- Chosen: {'dest_meta': {'province': 11838, 'via_army': 1038, 'occ_before': 1, 'bias': 'FRIENDLY_COLOC_CONCENTRATE'}, 'trial': {'ok': True, 'result': 'DRY_RUN_VALID', 'army': 1037, 'province': 11838, 'path_before': []}}

## G6 ONE Strategic Post (factory 4753)

- ABI: `calling/strategic_order.py` (proven 2iju/2ijv)
- Post: {'ok': True, 'result': 'PATH_CONTAINS_DEST', 'army': 1037, 'province': 11838, 'post_rax': 1, 'path_before': [11838], 'path_after': [11838]}
- Stability: {'seconds': 30.0, 'responding_stayed': True, 'alive_final': True, 'heap_exit': False, 'samples_n': 30}

## Gates

Restored allow_post=False; strategic_only_tool_gate.OPEN absent; Instant PARKED; Retreat PARKED.

## Path C

estimate_after=~90-92%; crossed_70=YES; +~2pp wartime Strategic encircle-bias after 2ike loop

*Phase 2ikf — 2026-11-01 23:24:12 Asia/Shanghai*


### Fold note (2026-11-01 23:24 Asia/Shanghai)

## PHASE2IKF — wartime Strategic Redeploy 4753 encircle-bias (HIT) — 2026-11-01 23:24 Asia/Shanghai

**Result:** G6_STRATEGIC_WARTIME_ENCIRCLE_HIT HIT=true army **1037** src_prov=3931 dest=11838 (friendly army 1038 province — force-concentration / stack-forming bias).

| Step | Evidence |
|------|----------|
| RO encircle-bias | dest pool = other friendly CA provinces; adjacency HONEST_EMPTY |
| Strategic 4753 | PATH_CONTAINS_DEST post_rax=1; path_before=[11838] path_after=[11838] |
| Stability ~30s | responding_stayed=True alive_final=True heap_exit=False |

**Note:** path_before already contained 11838 (lingering 2ike Move path); Post still IsValid+queue HIT with dest=11838 concentration target.
**Gates:** allow_post False; strategic_only + safe_land markers absent. Instant PARKED. Retreat PARKED_NOT_PROVEN_CHEAP.
**Agent card:** wartime Strategic Redeploy sits beside Move→Attack→Cancel loop as encircle-bias reposition primitive.
**Path-C:** ~90–92% (crossed_70=YES; +~2pp vs 2ike ~88–90%).
**Script:** scripts/phase2ikf_strategic_encircle.py

