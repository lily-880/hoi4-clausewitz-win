# Phase 2fr — COrderInstance pool root / COrdersGroup +0x8/+0xc handle map (RO)

**Result:** `orders_group_type0x35_documented`  
**Base:** `11fe169` (2fq) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (B progressed)

## Live
- pid **34188** ITA · UI **1936-01-12 04:00 → 1936-01-12 09:00** (hours 268→273) · **1x/pause only**

## A) COrderInstance pool root / oi→slot
| type | heap count | notes |
|------|------------|-------|
| COrderInstance | **0** | empty this window (2fq had 4 @ Jan 9–10); pool expand len=0 |
| COrdersGroup | **10** | contiguous samples ~0x240 apart |

- oi→`pool_base+oi*0x3D0`: **N/A** (empty pool); live Assign ois **{6,9}**
- owner-of-base backref: **0** (no pool base)
- Honest: A thin this session — no invent of catalog root from empty Instance heap

## B) COrdersGroup +0x8/+0xc → type **0x35** handle (documented)
- `HANDLE_TYPE_TABLE[0x35] = 0x1b85d2ee700`
- Mapped **n=10 / resolved=10 / type0x35=10**
- Layout (observed, not invented field names beyond handle pair):
  - `+0x8` = type **0x35** (u32)
  - `+0xc` = index (u32) ∈ {300,301,302,304,306,307,308,309,310,311}
  - `+0x10` = u32 **1** on all samples
- `resolve_handle(0x35, index)` → **addr − 0x10** for every sample (header immediately before COrdersGroup vtable object)
- `resolved+0x18` echoes `[0x35, index]` (= OG+0x8/+0xc) · **echo_matches=true** all 10
- `resolved` itself is **not** a typed RTTI vtable object (VT reads garbage / non-module) — treat as handleable header prefix, not a second named class

## Assign / NF
- Short Assign sight 25s: Assign×2 ois={6,9}; units army_indices present; **NF=0 RF=0**
- Bounded NF/RF midflight **not run** (B produced progress)

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- heap COrderInstance=0 COrdersGroup=10 (6152MB / 50s)
- COrdersGroup +0x8/+0xc = type-0x35 handle pair; resolve → self−0x10; echo at resolved+0x18
- HANDLE_TYPE_TABLE[0x35] registry live
- Assign sight ois={6,9}

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
- order_index→COrderInstance pool-slot proven
- stable G_GAMESTATE→pool root pointer path

## Next shortest NON-Post blocker
NON-Post: deepen type-0x35 handle resolve path (what owns the 0x35 table / index→OG catalog) **or** re-probe COrderInstance pool when Instances are live again **or** bounded NF/RF subject midflight; still **NO ALLOW_POST**
