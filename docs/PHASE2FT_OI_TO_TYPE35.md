# Phase 2ft — battle-plan order_index ↔ type-0x35 / COrdersGroup (RO)

**Result:** `order_index_is_type35_index`  
**Base:** `967a7ed` (2fs) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A progressed)

## Live
- pid **34188** ITA · UI **1936-01-14 00:00 → 1936-01-14 05:00** (hours ~312→317) · **1x/pause only**

## A) Tie order_index → HANDLE_TYPE_TABLE[0x35]
**Thesis tested (no invent):** battle-plan `order_index` is the **same integer** as type-**0x35** handle index.

| source | order_index values |
|--------|-------------------|
| live Assign (25s) | **{1, 10, 33}** (Assign×4) |
| hist (2fo–2fq) | {1, 6, 9, 12, 25} |
| probe set | {1, 6, 9, 10, 12, 25, 33} |

**For every probe oi:**
```
resolve_handle(0x35, oi) → header
header+0x10 → COrdersGroup (RTTI 0x29ced90)
header+0x18 echo [0x35, oi]
COrdersGroup+0x8/+0xc = (0x35, oi)   # plus0c == order_index
```
- resolve_ok **7/7** · og_rtti COrdersGroup **7/7** · plus0c_eq_oi **7/7**
- live_oi ties: **{1, 10, 33}** · hist ties: **{1, 6, 9, 12, 25}**

**Assign packing note (was unnamed in 2fp):** all live Assign samples have **`u32@+0x40 = 0x35`** (= handle type of the order slot). Together with `order_index@+0x48`, Assign carries the order-domain handle pair **(type=0x35, index=order_index)** split across +0x40/+0x48.

**OG peeks (observed only — field names not claimed):**
- array-shaped `{ptr,size,cap}` candidates at +0x18 / +0x30 / +0x50 / +0x60; +0x18/+0x30/+0x60 often image sentinels; +0x50 sometimes heap with size∈{1,2,3}
- no direct COrdersGroupMember VT qword in first 0x80 this window

## B) COrderInstance re-probe
- heap Instance/OG/Member counts **0** this 35s window (resolve path did not need heap) · pool len=0 · oi→slot N/A · honest empty

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- **order_index ≡ type-0x35 handle index** → COrdersGroup (7/7 including live Assign ois)
- Assign `u32@+0x40=0x35` documented as order handle type beside `order_index@+0x48`

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
- full G_GAMESTATE→type-0x35-reg owner path
- COrdersGroup internal order-slot field names (arrays observed only)

## Next shortest NON-Post blocker
NON-Post: map COrdersGroup internals (members/arrays @+0x50 etc.) for path/units **OR** re-probe COrderInstance when live **OR** bounded NF/RF subject; still **NO ALLOW_POST**
