# Phase 2fx — Instance+0x70 vs +0x88 structure (RO)

**Result:** `inst88_hub_neighbor_pairs__inst70_ordered_prefix_nodes`  
**Base:** `4935ac6` (2fw) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A progressed)

## Live
- pid **34188** ITA · UI **1936-01-09 01:00** (hours **193**) · **1x/pause only**
- Stage sight ~10s: Assign counts **22**, unique assigns **10**; nonempty structure rows **8**

## A) Fuller +0x70 vs +0x88 (sets / order / adjacency)

Prior 2fw: +0x88 = `CProvince*` (VT `0x29ee248`); partial id overlap with +0x70; ≠ army current provinces.

### Evidence (all 8 nonempty samples)
Pack +0x88 province ids as consecutive **(hub, neighbor)** pairs (odd leftover = unpaired trailing id when `n88` odd):

| check | result |
|-------|--------|
| every pair **hub** ∈ set(+0x70) | **8/8** |
| `hub_unique` (order-preserving) is a **prefix** of +0x70 | **8/8** |
| every pair **neighbor** ∉ set(+0x70) | **8/8** |
| +0x70[i+1] ∈ neighbors(+0x70[i]) from those pairs | **0** hits on all samples |
| consecutive +0x70 as undirected edges in pair-set | **0** (already in probe) |

Examples:
- oi **7**: +0x70=`[6673,671,11618]`; +0x88 pairs `(6673,11595),(6673,9613),(6673,3657)` — star from prefix hub `6673`
- oi **9**: hubs `9418,9444,13081` = prefix of +0x70; neighbors exterior
- oi **6**: `n70=26`, `n88=50` → 25 pairs; 13 unique hubs = prefix of +0x70; neighbors exterior (e.g. 6208→3058,6130)

### Honest interpretation (no invent)
- **+0x70**: ordered **u32 province-id sequence** (path-*like* node list). **Not** proven to be the unit movement path; **not** army current-province list (2fw).
- **+0x88**: `CPdxArray<CProvince*>` packed as **(hub, neighbor)** adjacency pairs for a **prefix** of +0x70; neighbors are **side** provinces, **not** path successors.
- Relationship: related by hub∈prefix(+0x70); **not** equal sets; **not** simple edge-list of the +0x70 polyline.

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- Structure hyp confirmed on 8/8 nonempty: hub-neighbor pairs + ordered +0x70 prefix

## Stubbed
- ring embed · 2fb · CMove · SAFE_POST · self-MOVE · tool-gate · Post · named movement-path proof for +0x70 · HourlyTick · Capstone/121 · NF subject type-id · midflight NF · army path/history beyond current province · named +0xe0/+0x100 · demangled RTTI for `0x29d6fb8` beyond catalog

## Next shortest NON-Post blocker
Prove/refute +0x70 as movement path via army path/history field **OR** bounded NF/RF midflight **OR** deepen +0xe0/+0x100; still **NO ALLOW_POST**.

Script: `scripts/phase2fx_70_88_structure.py`  
Reports: `reports/phase2fx_70_88_structure.json`, `reports/phase2fx_summary.json`
