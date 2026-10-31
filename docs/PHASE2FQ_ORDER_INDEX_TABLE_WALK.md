# Phase 2fq — order_index→order-object table walk (RO)

**Result:** `heap_live_walk_inconclusive`  
**Base:** `7168db5` (2fp) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run

## Live
- pid **34188** ITA · UI **1936-01-09 18:00 → 1936-01-10 11:00** (hours 210→227) · **1x/pause only**

## A) order RTTI heap + pointer-table attempt
| type | heap count | notes |
|------|------------|-------|
| COrderInstance | **4** | contiguous samples stride **0x3D0** |
| COrdersGroup | **77** | +0x8≈0x35 / +0xC id-like (handle-shaped; **not** claimed) |
| COrdersGroupMember | **47** | |

Contrast: Phase 2cw peacetime Haiti heap counts were **0** for all three.

**Pointer-backref:** 8 samples × ≤55s / 1927MB → **0 owners**. No CPdxArray `data[i]==obj` recovery.  
→ Honest reading: battle-plan `order_index` catalog is **not** (yet) a raw `COrder*` pointer table into these objects; **index-into-pool** more plausible given stride-0x3D0 packing.

**Peeks:** u32 values ∈ live oi edges {1,6,25} appear at **inconsistent** offsets inside COrderInstance — **no field named** (no invent).

## Assign / NF window
- Short 15s stage: Assign empty (quiet)
- Bounded 70s NF/RF watch: **Assign×17** with `order_index` ∈ **{6,9,12}**; **NF=0 RF=0** (honest empty)

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- order RTTI heap LIVE (first non-zero since 2cw peacetime 0): COrderInstance=4 COrdersGroup=77 COrdersGroupMember=47 (scan 6501MB)
- COrderInstance samples contiguous stride 0x3D0 pool: 0x…70a0/7470/7840/7c10
- stage Assign (70s window) ois={6,9,12} sight_counts Assign×17; NF=0 RF=0
- object peeks: u32∈{1,6} appear at inconsistent offs inside COrderInstance (no field named — no invent)
- pointer-backref of 8 samples → 0 owners in 55s/1927MB — catalog likely index-into-pool not raw COrder* table

## Stubbed
- in-process ring embed
- 2fb recipe execution
- ordinary CMove live leaf
- SAFE_POST / ALLOW_POST
- self-MOVE
- tool-gate open
- Post inject
- path-vector nonempty
- HourlyTick abuse
- Capstone/121 re-churn
- NewFallback subject type-id table
- live midflight NewFallback hex
- order_index→COrder* proven catalog root (pointer-backref empty)

## Next shortest NON-Post blocker
NON-Post: resolve COrderInstance pool root (stride 0x3D0) / owner-of-base as index catalog OR map COrdersGroup +0x8/+0xc handle-like pair; NF/RF midflight still open; still NO ALLOW_POST
