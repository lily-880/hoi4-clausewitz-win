# Phase 2fz — Deepen Instance+0xe0 / +0x100 (RO)

**HEAD parent:** `3f8e79a` (2fy)  
**Result:** `inst_e0_u32_province_stream__e100_parallel_non_u32`  
**allow_post:** False (never opened)

## Live window

| Field | Value |
|-------|-------|
| pid | 34188 |
| hours | 232 (primary) / refine shortly after |
| UI date | 1936-01-10 16:00 |
| speed | pause-or-1x only (never 5x; probe did not change speed) |
| scenario | ITA peacetime Assign sight |
| Assign sight | `COrderAssignCommand` ×3 (primary) |

## A — Identity deepen

### Method (RO)

1. Resolve `COrderInstance` via OG+0x98; read CPdxArray at `+0xe0` / `+0x100` (also `+0x70` / `+0x88` for relation).
2. Dual stride test: `size×4` as u32 stream vs `size×8` as qword ptr/handle (2fy false-friend).
3. Classify qword elems against catalog VTs (`CProvince`/`CArmy`/`COrderInstance`/MI); resolve handle-shaped pairs.
4. Cross province-id sets vs `+0x70` and `+0x88` hub/neighbor ids.
5. **No writes. No Post.**

### Findings (honest)

| Observation | Evidence |
|-------------|----------|
| **`+0xe0` ≡ CPdxArray&lt;u32&gt; province-id stream** (shape) | 8/8 nonempty: all elems in province-id range when read as `size` u32s (`size×4`). Same **shape** as named-candidate `+0x70`. |
| **`size×8` qword view is wrong stride** | Packs consecutive u32s into qwords → false “handle_shaped” / “unreadable_ptr” / rare spurious `CArmy*` hits. 2fy “u32 coexists with ptr_other” explained. |
| **`+0x100` same size as `+0xe0`, not u32-province** | `size(+0xe0)==size(+0x100)` on **all** sampled ois; 0/8 `+0x100` u32 streams all-province; 0 CProvince* elems; dwords include 0, float-ish `0x3f800000` (1.0f), heap-looking values. **Parallel sibling array; element type unnamed.** |
| **No link to `+0x70` / `+0x88` this window** | nonempty `+0xe0/+0x100` ois had **empty** `+0x70`/`+0x88` here; overlap/subset/equal vs 70 & hub/neigh = **0**. Complementary population, not the same list. |
| **Role still unnamed** | Do **not** invent front/path/fallback labels. Only: u32 province-id stream at `+0xe0`; parallel non-u32 array at `+0x100`. |

### Sample (refine)

| oi | n_e0=n_100 | +0xe0 u32s (all-prov) | +0x100 u32 reinterpret (not all-prov) | n70/n88 |
|----|------------|------------------------|----------------------------------------|---------|
| 8 | 8 | 295,538,718,768,769,888,889,890 | 295,0,large,441,1,1,… | 0/0 |
| 5 | 5 | 11,188,189,814,815 | 11,81,large,441,1 | 0/0 |
| 40 | 5 | 70,71,72,73,664 | 70,9411,large,441,1 | 0/0 |

Primary probe also saw occasional catalog `CArmy` VT when over-reading `+0xe0` as qwords — treat as **stride artifact**, not elem type.

## Works

- allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run
- Result: `inst_e0_u32_province_stream__e100_parallel_non_u32`
- +0xe0: u32 province-id stream (8/8); wrong-stride×8 documented
- +0x100: parallel size twin; not u32-province; not CProvince*
- No +0x70/+0x88 overlap this window
- Assign sight 3 (primary)

## Stubbed

- ring embed · 2fb · CMove · SAFE_POST · self-MOVE · tool-gate · Post
- named role for +0xe0 beyond “u32 province-id stream”
- named +0x100 element type / demangled VT
- named CArmy path offs · +0x70 as army movement path (already refuted 2fy)
- HourlyTick · Capstone/121 · NF type-id · midflight NF · demangled RTTI `0x29d6fb8`

## Artifacts

- `scripts/phase2fz_e0_e100_identity.py`
- `scripts/_phase2fz_u32_refine.py`
- `reports/phase2fz_e0_e100_identity.json`
- `reports/phase2fz_summary.json`
- `reports/_phase2fz_u32_refine.json`

## Next shortest NON-Post blocker

Bounded NF/RF midflight **or** name `+0x100` elem type (RTTI/struct) **or** war-dense named CArmy path fields — **still NO ALLOW_POST**.
