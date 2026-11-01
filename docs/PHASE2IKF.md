# PHASE2IKF

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

