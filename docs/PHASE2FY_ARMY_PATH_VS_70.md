# Phase 2fy — Instance+0x70 vs CArmy path/history (RO)

**HEAD parent:** `a560d83` (2fx)  
**Result:** `inst70_no_overlap_with_army_path_candidates`  
**allow_post:** False (never opened)

## Live window

| Field | Value |
|-------|-------|
| pid | 34188 |
| hours | 214 |
| UI date | 1936-01-09 22:00 (Asia/Shanghai label for game clock) |
| speed | pause-or-1x only (never 5x; probe did not change speed) |
| scenario | ITA peacetime Assign sight |
| Assign sight | `COrderAssignCommand` ×9 (unique assigns) |

## A — Prove/refute +0x70 as army movement path

### Method (RO)

1. Stage-watch Assign (~10s) → `order_index` + army handle indices.
2. Resolve `COrderInstance` via OG+0x98; read `Instance+0x70` as CPdxArray u32 province-id stream (same shape as 2fw/2fx).
3. Resolve each assigned `CArmy` primary (VT `0x29d6d68`); current province via `+0x28` / `+0x1F0→CProvince+0xA4`.
4. Scan CArmy blob `0x40..0x780` for `std::vector<u32>` and CPdxArray u32 province-id candidates (2fh-style); also probe candidate dword `@+0x2B4`.
5. Cross-check equal / set-equal / subset / subsequence / overlap vs +0x70. **No writes. No Post.**

### Aggregate

| Metric | Value |
|--------|-------|
| ois probed | 20 |
| with nonempty +0x70 | **11** |
| armies with path cand beyond current-only | **42** |
| ois with both +0x70 and useful path cand | **4** |
| equal / set-equal / subsequence hits | **0** |
| overlap hits | **0** |
| last_path_cand `@+0x2B4` province-shaped | **0** this window |

### Honest conclusion

On the 4 ois where **both** `Instance+0x70` and assigned-CArmy path-shaped candidates were nonempty, **overlap was empty** (examples: oi7 `70=[6673,671,11618]` vs army path samples `[81]`, `[8049,440]`, …; oi52 / oi124 similar). Therefore **+0x70 is not the live CArmy movement path / planned path vector for assigned armies in this peacetime window**.

This refutes the short “+0x70 ≡ army path” identity under current RO evidence. It does **not** name the CArmy scan offsets (`0x60`, `0x170`, `0x200`, `0x3e0`, …) as demangled fields — those remain **candidates** only. Combined with 2fw (+0x70 ≠ army current provinces) and 2fx (+0x88 = hub/neighbor pairs over +0x70 prefix), +0x70 remains an **order/front province-id sequence**, not proven midflight army movement path.

## B — Light Instance+0xe0 / +0x100 peek

Same instances; CPdxArray read at `+0xe0` / `+0x100`.

| Kind counter | +0xe0 | +0x100 |
|--------------|-------|--------|
| empty_or_absent | 11 | 11 |
| u32_province_stream (bytes pass id shape) | 9 | 2 |
| ptr_other (VT not CProvince/CArmy/Instance) | 9 | 9 |

When both u32-shaped and ptr_other fire on the same array, treat **u32_province_stream as likely reinterpretation of pointer bytes** — not a named province-id field. Pointer VT samples include unreadable / nullish / odd RVAs (`0x2bb8bd0`, `0x2794550`, …) — **not identified**. No invent; deepen later if needed.

## Works

- `allow_post` False; never 5x; no Post / inject / tool-gate / 2fb; Capstone not re-run
- Result: `inst70_no_overlap_with_army_path_candidates`
- with_70=11; path_nonempty_armies=42; with_both=4; equal/subseq=0; overlap=0
- Assign sight 9; light +0xe0/+0x100 kind peek documented

## Stubbed (unchanged policy)

- ring embed · 2fb live · CMove leaf · SAFE_POST / ALLOW_POST · self-MOVE · tool-gate · Post inject
- named CArmy path-field offsets · named movement-path proof for +0x70 (refuted as army path this window; still unnamed order geometry)
- HourlyTick abuse · Capstone/121 · NF subject type-id · midflight NF · named +0xe0/+0x100 beyond kind peek · demangled RTTI `0x29d6fb8` beyond catalog

## Artifacts

- `scripts/phase2fy_army_path_vs_70.py`
- `reports/phase2fy_army_path_vs_70.json`
- `reports/phase2fy_summary.json`

## Next shortest NON-Post blocker

Deepen `Instance+0xe0/+0x100` RO identity (named VT / element type) **or** bounded NF/RF midflight **or** war-dense relaunch for named CArmy path fields — **still NO ALLOW_POST**.
