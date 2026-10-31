# Phase 2fv — COrderInstance field map via OG+0x98 (RO)

**Result:** `order_instance_fields_mapped`  
**Base:** `14b6ca2` (2fu) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed · Capstone **not** re-run · NF midflight **skipped** (A+B progressed)

## Live
- pid **34188** ITA · UI **1936-01-06 12:00** (hours **132**) · **1x/pause only**
- Assign sight ~12s: ois **{5, 6, 25, 40, 44}**; `u32@+0x40=0x35` on all samples
- Also mapped hist/focus ois via OG+0x98 → **vt_ok 12** total

## A) COrderInstance map (from OG+0x98[0])
VT `0x2a02558` at `+0x00` on all mapped.

| Inst off | observation (no invent beyond evidence) | consistency |
|----------|------------------------------------------|-------------|
| +0x00 | VT COrderInstance | all vt_ok |
| +0x38 | **`COrdersGroup*` back-pointer** | **all vt_ok** (`qword_eq_og_offs=['0x38']`) |
| +0x70 | CPdxArray (heap when nonempty) | **7** nonempty; elems as **u32 stream in province-id range** (observed 58–13081); **candidate path/province list — not named** |
| +0x88 | CPdxArray (heap when nonempty) | **7** nonempty; elems **opaque ptr** (hi dword often `0x1b9`); role unnamed |
| +0xe0 / +0x100 | CPdxArray | **5** nonempty; mixed handle-shaped / opaque; role unnamed |
| +0x78 / +0x90 | capacity/size meta of +0x70/+0x88 (probe false “handle” hits) | size echoes match |

`order_index` u32 echo offs **inconsistent** across samples — **no oi field named**.

### Bidirectional link
```
order_index
  → resolve(0x35, oi) → COrdersGroup
  → OG+0x98[0] = COrderInstance*
  → Instance+0x38 = same COrdersGroup*
```

## B) OG+0x50 elems (type-pass)
- All sampled elems: **VT RVA `0x29d6fb8`** at `*elem+0`
- Catalog match: `research/WINDOWS_OFFSETS.md` lists **`0x29d6fb8` among CArmy MI vtables** (`0x29d6d68` + MI `0x29d6f48`, `0x29d6fb8`, `0x29d7000`) — **army-shaped**; demangled RTTI string not re-resolved this slice
- Layout observed in first 0x28:
  - `+0x00` → VT `0x29d6fb8`
  - `+0x08` → owning **COrdersGroup***
  - `+0x20` → linked **COrderInstance***
- ≠ COrdersGroupMember (`0x29ced48`)

## Works
- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- Instance via OG+0x98: vt_ok 12; **+0x38 → OG***; +0x70/+0x88 heap arrays; +0x70 u32 province-id-range candidate
- OG+0x50 elems: VT `0x29d6fb8` (= CArmy MI catalog) + OG@+0x08 + Instance@+0x20

## Stubbed
- in-process ring embed · 2fb · CMove leaf · SAFE_POST · self-MOVE · tool-gate · Post · path-vector nonempty confirm · HourlyTick · Capstone/121 · NF subject type-id · midflight NF hex · oi→Instance pool-slot · G_GAMESTATE→pool/0x35-reg · named Instance +0x70/+0x88/+0xe0/+0x100 · demangled RTTI string for VT 0x29d6fb8 beyond catalog

## Next shortest NON-Post blocker
NON-Post: confirm Instance+0x70 u32s vs live army provinces/path **OR** deepen +0x88 ptr targets **OR** army-handle cross-check on +0x50 / demangle VT 0x29d6fb8 **OR** bounded NF/RF; still **NO ALLOW_POST**

Script: `scripts/phase2fv_instance_fields.py`  
Reports: `reports/phase2fv_instance_fields.json`, `reports/phase2fv_summary.json`
