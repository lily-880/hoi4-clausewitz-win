# Phase 2fs — type-0x35 handle table ownership / index→OG catalog (RO)

**Result:** `type35_index_og_catalog_documented`  
**Base:** `6b77760` (2fr) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A progressed)

## Live
- pid **34188** ITA · UI **1936-01-13 04:00 → 1936-01-13 08:00** (hours ~292→296) · **1x/pause only**

## A) type-0x35 registry + index→OG catalog
**Registry** (`HANDLE_TYPE_TABLE[0x35]` → `0x1b85d2ee700`):
| off | observed | role (from handle.py / live) |
|-----|----------|------------------------------|
| +0x00 | 0 | not a vtable |
| +0x08 | buckets `0x1b9e1dbb210` | hash bucket base |
| +0x10 | u32 `0x1c0` | observed counter-like |
| +0x14 | mask **511** (`0x1ff`) | hash mask → **512** slots |
| +0x18 | u32 `0xb` | observed (≈ live OG heap count scale) |

**Ownership path (documented, not invented beyond known statics):**
- Static: `image+HANDLE_TYPE_TABLE+0x35*8` = `rva 0x34ffda8` → reg (**equals_reg true**)
- `G_GAMESTATE[0..0x800)` qword==reg: **0 hits** (no direct gs→reg in first 2KB)
- Full owner graph above the type table **not** claimed this slice

**Catalog walk** (bucket×chain, same layout as `resolve_handle`):
- slot hits collected: **964** (includes chain-overlap dupes when walking every h)
- unique indices: **448** · range **1..481** (33 gaps)
- `resolve_handle` match: **964/964** · echo `[0x35,index]` at header+0x18: **964/964**
- header+0x10 RTTI **COrdersGroup**: **803** (others may be non-OG or transient)

**Layout confirmed (extends 2fr):**
```
resolve(0x35, index) → header
header + 0x10 → COrdersGroup vtable object
header + 0x18 → (type=0x35, index) echo
COrdersGroup + 0x8/+0xc → same (type, index) pair
```

**Live OG cross-check:** heap COrdersGroup **10/10** catalog hit · **10/10** header = OG−0x10

## B) COrderInstance re-probe
- heap COrderInstance=**0** (still) · pool len=0 · oi→slot N/A · honest empty

## Assign / NF
- NF/RF midflight **not run** (A produced progress)

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- type-0x35 registry mask=511 buckets live; catalog resolve/echo OK
- index→OG via header−/+0x10; live OG 10/10 cross-check
- HANDLE_TYPE_TABLE slot ownership documented; gs direct ptr absent in +0x800

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

## Next shortest NON-Post blocker
NON-Post: tie battle-plan `order_index` to type-0x35/OG graph **OR** re-probe COrderInstance pool when Instances live; NF/RF midflight still open; still **NO ALLOW_POST**
