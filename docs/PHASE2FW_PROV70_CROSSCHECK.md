# Phase 2fw — Instance+0x70 vs army provinces; +0x88 = CProvince* (RO)

**Result:** `inst70_not_army_current_prov__inst88_is_cprovince_array`  
**Base:** `55f55c1` (2fv follow-up) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A+B progressed)

## Live
- pid **34188** ITA · A-probe UI **1936-01-07 16:00** (hours **160**) · post-B check **1936-01-08 04:00** (hours **172**) · **1x/pause only** (never 5x)
- Assign sight: **10** Assign ois; rows_ok **11**; with_70 **6**; with_army_prov **10**; with_both **5**

## A) Instance+0x70 vs assigned armies’ current provinces
Cross-check: +0x70 u32 stream (province-id range) vs each assigned army’s `CA_PROVINCE_ID@+0x28` and `CA_PROVINCE_PTR@+0x1F0 → CP_PROVINCE_ID@+0xA4` (both agree when resolved).

| oi | n70 | n_army_prov | overlap | note |
|----|-----|-------------|---------|------|
| 6 | 26 | 3 | **0** | sample70 e.g. 6208,11060,9083…; army 13237/1984/13238 |
| 9 | 6 | 3 | **0** | |
| 68 | 25 | 2 | **0** | |
| 70 | 6 | 1 | **0** | |
| 13 | 4 | 5 | **0** | |

**Honest:** Instance+0x70 is **not** the assigned armies’ **current-province** list. Role still **unnamed** (do not invent “path”).

Army resolve: primary CArmy VT `0x29d6d68` via handle; `+0x28` == via-`+0x1f0` province id when both readable.

## B) Instance+0x88 deepened
Prior 2fv: +0x88 “opaque ptrs”. 2fw: every sampled elem VT RVA **`0x29ee248`** = **`CProvince`** (`research/WINDOWS_OFFSETS.md` / proven live 2cy).

| oi | n70 | n88 | vt_ok (≤32 sampled) | frac 70⊂88 | frac 88⊂70 | equal sets | 88∩army |
|----|-----|-----|---------------------|------------|------------|------------|---------|
| 6 | 26 | 50 | 32/32 | 0.35 | 0.53* | no | **0** |
| 9 | 6 | 13 | 13 | 0.50 | 0.43 | no | **0** |
| 68 | 25 | 50 | 32/32 | 0.32 | 0.47* | no | **0** |
| 70 | 6 | 11 | 11 | 0.50 | 0.43 | no | **0** |
| 13 | 4 | 7 | 7 | 0.50 | 0.40 | no | **0** |
| 17 | 5 | 9 | 9 | 0.60 | 0.50 | no | **0** |

\*frac 88⊂70 for n88>32 uses first-32 sample only.

**Honest:** +0x88 = **`CPdxArray<CProvince*>`**. Province ids at `CProvince+0xA4` **partially overlap** +0x70 u32s (≈32–60% of 70-in-88); **sets not equal**; **neither** overlaps army current provinces. Do **not** invent that +0x70 is “the path” or that +0x88 is “the same list as ptrs”.

## C) OG+0x50 light cross-check
- Elem VT `0x29d6fb8` (= catalogued **CArmy MI** RVA); layout `+0x08→OG*`, `+0x20→Instance*` (reconfirmed).
- Walk-back `-delta` to primary CArmy VT `0x29d6d68`: **hits=0**. Do **not** invent that elem* is a CArmy*. Demangled RTTI string beyond catalog **not** re-dumped this slice.

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- A: `inst70_no_army_province_overlap` (0/0 on with_both)
- B: `inst88_cprovince_partial_overlap_inst70` — +0x88 named as CProvince* array; related-to but ≠ +0x70
- C: OG+0x50 MI VT + backrefs; primary walk-back empty

## Stubbed
- in-process ring embed · 2fb · CMove leaf · SAFE_POST · self-MOVE · tool-gate · Post · path-vector nonempty confirm as named movement path · HourlyTick · Capstone/121 · NF subject type-id · midflight NF hex · oi→Instance pool-slot · G_GAMESTATE→pool/0x35-reg · named +0x70 role · named +0xe0/+0x100 · demangled RTTI string for `0x29d6fb8` beyond catalog

## Next shortest NON-Post blocker
Interpret +0x70 vs +0x88 relationship (superset / adjacency / path graph?) with fuller sample **OR** find army path/history field beyond current province **OR** bounded NF/RF midflight; still **NO ALLOW_POST**.

Scripts: `scripts/phase2fw_prov70_crosscheck.py`, `scripts/phase2fw_88_prov_ids.py`  
Reports: `reports/phase2fw_prov70_crosscheck.json`, `reports/phase2fw_88_vs_70.json`, `reports/phase2fw_summary.json`
