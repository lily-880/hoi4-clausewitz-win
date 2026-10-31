# Phase 2gf — Assign/Unassign edge deepen + IsValid polish

**HEAD parent:** `1f0b874` (2ge)  
**Result:** `assign_unassign_edge_empty`  
**allow_post:** False (never opened)

## What ran

Preferred **A**: bounded **90.02s @1x** pending/stage observe for `COrderAssignCommand` (factory_idx **3350**) / `COrderUnassignCommand` (**3365**) on current ETH process — decode units `{type,index}` packing, `order_index`↔type-**0x35**, army resolve when present.

Preferred **B** (A empty): catalog-only IsValid/Execute/factory polish from `cmd_layout` — **no Capstone/121**.

## Live

| field | value |
|-------|-------|
| pid | 14248 |
| hours | 39 → **47** |
| UI | 1936-01-02 15:00 → **1936-01-02 23:00** |
| speed | 1x only (never 5x) |
| scenario | ETH@1x Assign/Unassign edge deepen |
| counters end | see report `last_counters` |

## Honest outcome (A)

- **Assign captures:** 0  
- **Unassign captures:** 0  
- **sight_counts:** `{}` (no Assign/Unassign/NF/Exec on pending/stage this window)  
- ETH war-day plan churn quiet for these leaves (same quiet class as prior NF/path empties). Do not invent.

## IsValid / packing polish (B) — deltas only

| cmd | vt | factory_idx | isvalid | execute |
|-----|-----|-------------|---------|---------|
| COrderAssignCommand | `0x2a84498` | **3350** | `0x18de900` | `0x18d41b0` |
| COrderUnassignCommand | `0x2a84550` | **3365** | `0x18e01d0` | `0x18db050` |
| COrderExecuteCommand | `0x2a85468` | 3352 | `0x18def40` | `0x18d6430` |
| COrderNewFallbackCommand | `0x2a84c80` | 4271 | `0x18df4b0` | `0x18d8fc0` |

Packing (already 2fn/2fo; reaffirmed, no Capstone):

- Assign/Unassign **units** = CPdxArray @ **+0x28** (capacity +0x30, size/count **+0x34**); elem `{u32 type, u32 index}` stride 8  
- Assign **order_index** @ **+0x48**; `assign_to_minimum_order` @ +0x4c  
- Unassign **unassign_group** @ +0x48; **unassign_army_group_instances** @ +0x49  
- NF IsValid gate call still `0xbbb1e0` (ISVALID_PATHS)

**Delta vs prior:** documentation consolidation only — no new RVA from Capstone; Assign/Unassign FN table now cited in-slice for Post-readiness checklist.

## Works

- allow_post False; never 5x; no Post / inject / tool-gate / 2fb / Capstone  
- Bounded Assign/Unassign edge observe (honest empty)  
- Catalog IsValid/Execute/factory_idx polish table

## Stubbed

ring embed · 2fb · CMove · SAFE_POST · self-MOVE · tool-gate · Post · HourlyTick · Capstone/121 · named +0x100/+0xe0 · RTTI 0x29d6fb8 · CArmy path offs · midflight NF · **live midflight Assign/Unassign hex (empty this window)**

## Next shortest NON-Post blocker

Assign/Unassign quiet on ETH war-day pending/stage — **ITA relaunch** for denser plan churn **or** deepen **Execute** `order_index` leaf from catalog; **still NO ALLOW_POST**.

## Artifacts

- `scripts/phase2gf_assign_unassign_edge.py`
- `reports/phase2gf_summary.json`
- `reports/phase2gf_assign_unassign.json`
