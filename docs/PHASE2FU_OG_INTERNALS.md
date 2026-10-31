# Phase 2fu — COrdersGroup internals (arrays / path-units) (RO)

**Result:** `orders_group_internals_mapped`  
**Base:** `34af121` (2ft) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A progressed)

## Live
- pid **34188** ITA · UI **1936-01-01 21:00 → 1936-01-02 01:00** (hours 21→25; session appears reset vs 2ft Jan-14 clock) · **1x/pause only**
- Assign sight 20s: ois **{17, 20, 52}**; `u32@+0x40=0x35` on all

## A) COrdersGroup field map (via resolve(0x35, oi))
CPdxArray layout (proven 2fm/2fn): **`data@0 capacity@8 size@0xC alloc@0x10`**.

Mapped **10/10** OGs for oi ∈ focus∪live∪hist `{1,6,9,10,12,17,20,25,33,52}`.

| OG off | role (observed) | notes |
|--------|-----------------|-------|
| +0x08/+0x0c | type-0x35 handle echo | `(0x35, order_index)` — 2ft |
| +0x18 | CPdxArray | empty image sentinel (`size=0`) all samples |
| +0x50 | CPdxArray\<ptr\> | **heap**, size∈{1..13}; elems = **opaque_ptr** (no known RTTI at `*p` or `*p+0x10`; **not** named Member yet) |
| +0x98 | CPdxArray\<COrderInstance*\> | **size=1, cap=1** on **all** mapped OGs; elem0 RTTI **COrderInstance** (`vt 0x2a02558`) |

### Critical path (new)
```
order_index
  → resolve_handle(0x35, order_index) → header
  → header+0x10 = COrdersGroup
  → COrdersGroup+0x98 CPdxArray[0] = COrderInstance*
```
This is the first **live object path** from battle-plan `order_index` to a **COrderInstance** (pool-slot arithmetic still unproven; heap Instance scan this window still 0 — pointers obtained via OG, not heap VT scan).

### +0x50 opaque list
- Consistent ptr array; sizes track “something” per order (oi20 size=13, oi33 size=1)
- Elem classification: opaque only this slice — **no invent** of Member/unit/path
- Next slice candidate: deeper typed walk of `*elem` (Member VT at non-zero offset, army handle embed, province list)

### Assign cross
- live armies seen: oi52→[1042], oi17→[24], oi20→[] — **no** overlap into +0x50/+0x98 elem classes this window (army_overlap=0)

## B) COrderInstance heap re-probe
- heap VT scan Instance=0 Member=0 (30s) · pool len=0 · oi→slot N/A
- Instances **still live** via OG+0x98 pointers (above) — scan miss ≠ absence

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- OG internals: +0x18 sentinel, +0x50 opaque ptr array, **+0x98 → COrderInstance\*** (10/10)
- order_index→COrdersGroup→COrderInstance object path documented
- CPdxArray layout confirmed on OG

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
- order_index→COrderInstance **pool-slot** arithmetic
- typed identity of +0x50 opaque elems
- stable G_GAMESTATE→pool root pointer path
- full G_GAMESTATE→type-0x35-reg owner path

## Next shortest NON-Post blocker
NON-Post: type +0x50 opaque elems (Member/units/path) **OR** map COrderInstance fields from OG+0x98 targets **OR** bounded NF/RF subject; still **NO ALLOW_POST**
