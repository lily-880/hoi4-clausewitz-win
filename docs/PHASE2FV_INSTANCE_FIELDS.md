# Phase 2fv — COrderInstance field map via OG+0x98 (RO)

**Result:** `order_instance_fields_mapped`  
**Base:** `14b6ca2` (2fu) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A progressed)

## Live
- pid **34188** ITA · UI **1936-01-05 18:00** (hours **114**) · **1x/pause only**
- Assign sight ~12s: ois **{0,4,6,8,17}** (oi0 resolve fail); `u32@+0x40=0x35` on samples

## A) COrderInstance map (from OG+0x98[0])
**vt_ok = 10/10** (excl. oi0) · VT `0x2a02558` at `+0x00`.

| Inst off | observation (no invent beyond evidence) | consistency |
|----------|------------------------------------------|-------------|
| +0x00 | VT COrderInstance | 10/10 |
| +0x08 | second image ptr (VT-like `…038b50`) | present; role unnamed |
| +0x38 | **`COrdersGroup*` back-pointer** | **10/10** (`qword_eq_og_offs`) |
| +0x70 | CPdxArray (heap when nonempty) | **7/10** nonempty; elems **u32 stream in province-id-like range** (~200–13000); **candidate path/province list — not named** |
| +0x88 | CPdxArray (heap when nonempty) | **7/10** nonempty; elems **opaque ptr** (paired hi=0x1b9); role unnamed |
| +0xe0 / +0x100 | CPdxArray | **3/10** nonempty; u32 heads small ints / mixed; role unnamed |
| +0x78 / +0x90 | array **capacity/size** meta (false “handle” hits in probe) | matches +0x70/+0x88 sizes |

### Bidirectional link (new)
```
order_index
  → resolve(0x35, oi) → COrdersGroup
  → OG+0x98[0] = COrderInstance*
  → Instance+0x38 = same COrdersGroup*   (10/10)
```

### +0x70 note
Across oi∈{6,9,10,12,17,20,52}: array sizes 3–26; `elems4` values look like **HOI4 province IDs** (e.g. 6208, 3298, 9567). Documented as **province-id-range candidate** only — **no field name invented**.

## B) OG+0x50 opaque elems (light type-pass)
- All sampled elems share **VT RVA `0x29d6fb8`** at `*elem+0` (RTTI **name unresolved** this slice; **≠** Member `0x29ced48`)
- Embedded pointers observed in first 0x40:
  - `+0x08` → owning **COrdersGroup**
  - `+0x20` → linked **COrderInstance**
- Result: **typed object** with known VT + OG/Instance backrefs; **class name still stubbed**

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- Instance via OG+0x98: vt_ok 10; **+0x38 → OG***; +0x70/+0x88 heap arrays; +0x70 u32 province-id-range candidate
- OG+0x50 elems: shared VT `0x29d6fb8` + OG@+0x08 + Instance@+0x20

## Stubbed
- in-process ring embed · 2fb · CMove leaf · SAFE_POST · self-MOVE · tool-gate · Post · path-vector nonempty confirm · HourlyTick · Capstone/121 · NF subject type-id · midflight NF hex · oi→Instance pool-slot · G_GAMESTATE→pool/0x35-reg · **RTTI name for VT 0x29d6fb8** · **named** Instance +0x70/+0x88 fields · +0xe0/+0x100 role

## Next shortest NON-Post blocker
NON-Post: resolve RTTI name for VT `0x29d6fb8` (+0x50 elems) **OR** confirm +0x70 as province/path (cross-check live army provinces) **OR** deepen +0x88 ptr targets **OR** bounded NF/RF; still **NO ALLOW_POST**
