# Phase 2ga — Instance+0x100 elem type vs +0xe0 twin (RO)

**HEAD parent:** `578ffdd` (2fz)  
**Result:** `inst_e100_packed_twin_of_e0__no_named_elem_class`  
**allow_post:** False (never opened)

## Live window

| Field | Value |
|-------|-------|
| pid | 34188 |
| hours | 265 |
| UI date | 1936-01-12 01:00 |
| speed | pause-or-1x only (never 5x) |
| scenario | ITA peacetime |
| Assign sight | empty this window (seeded hist ois) |

## B — Name +0x100 elem type

### Method (RO)

1. Resolve Instance via OG+0x98; read CPdxArray `+0xe0` / `+0x100`.
2. Test homogeneous hypotheses: `u32` province stream, `float[]`, `CProvince*`/`CArmy*`/`COrderInstance*` ptr array, stride-16 structs.
3. Pair index-wise with `+0xe0` u32s; dump raw head bytes.
4. **No writes. No Post.** War-dense (A) and NF (C) skipped — B progressed.

### Findings (honest)

| Claim | Evidence |
|-------|----------|
| **Size twin of +0xe0** | `size(+0x100)==size(+0xe0)` on **8/8** nonempty |
| **First dword echoes e0[0]** | **8/8** — raw head `u32[0] == e0[0]` |
| **Not homogeneous u32-province** | 0/8 all-province (2fz confirmed; 2ga reconfirmed) |
| **Not float[]** | float reinterpretation inconsistent / non-weightish across samples |
| **Not CProvince* / CArmy* array** | 0 catalog-named ptr majority; `ptr_array_named=false` |
| **Packed / heterogeneous buffer** | Within `cap×8` bytes: mix of e0-echo dword, small ints, heap ptrs, recurring **module ptr** |
| **Recurring unnamed VT RVA** | Soft hits on module ptr → **`0x2794550`** (34× this window) — **catalog miss; not demangled; do not invent class name** |
| **Elem class unnamed** | No single Clausewitz element type proven for `+0x100` |

### Sample heads `(oi, e100_u320, e100_u321, e0[0])`

`(4,6,441,6)` · `(5,11,81,11)` · `(8,295,0,295)` · `(40,70,9411,70)` · `(44,42,0x3f800000,42)`

### Progress vs 2fz

2fz: `+0xe0` = u32 province stream; `+0x100` = parallel non-u32.  
2ga: rules out named homogeneous elem classes; establishes **packed twin** constraints (size twin + first-dword e0 echo + recurring `0x2794550` module soft-hit).

## Works

- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- Result: `inst_e100_packed_twin_of_e0__no_named_elem_class`
- size_twin 8/8; first_u32_echoes_e0 8/8; ruled out u32/float/CProvince*/CArmy* elem arrays
- Recurring soft VT RVA `0x2794550` documented unnamed

## Stubbed

- ring embed · 2fb · CMove · SAFE_POST · self-MOVE · tool-gate · Post
- demangled name for VT `0x2794550` / +0x100 elem class
- named +0xe0 role beyond u32 province stream
- named CArmy path offs · war-dense relaunch observe · HourlyTick · Capstone/121 · NF type-id · midflight NF · demangled RTTI `0x29d6fb8`

## Artifacts

- `scripts/phase2ga_e100_elem_type.py`
- `reports/phase2ga_e100_elem_type.json`
- `reports/phase2ga_summary.json`

## Next shortest NON-Post blocker

Bounded NF/RF midflight **or** war-dense named CArmy path **or** demangle `0x2794550` / deepen packed +0x100 layout — **still NO ALLOW_POST**.
