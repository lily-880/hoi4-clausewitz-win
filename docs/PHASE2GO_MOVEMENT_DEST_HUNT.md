# Phase 2go — Named movement_dest hunt (RO)

**Result:** `MOVEMENT_DEST_NAMED_HONEST_EMPTY`
**Live:** pid 30352 · 1936-01-06 10:00 · hours=130 · tag=15 · @1x
**Strict string hits:** 0 (`movement_dest` / `MovementDest` / `move_destination` / …)
**Loose:** `target_province` ×7 in PE ASCII (not demangled CArmy field)
**Soft +0x2B4:** None on multi armies this window · **eq path_last frac:** 0.0
**Scalar offs ≡ path200[-1]:** none ranked · **best_off:** null
**+0x200 multi:** 3 (1045/1046 n=41 identical path_last=740; 1048 n=4)

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Method

1. PE ASCII needle scan of `hoi4.exe` for named destination families (strict + loose).
2. Live ITA CArmy: re-read `+0x200` multi (tag-FP filtered); soft `+0x2B4`; scalar u32 agreement with `path200[-1]`.
3. Rank scalar offs by agreement; never claim demangled name from agreement alone.
4. One-shot probe — no endless poll, no speed change.

## Semantics (this window)

- **No demangled / named** `movement_dest` string in image for CArmy path destination.
- Soft `+0x2B4` last_path_cand **empty** this window (prior soft candidate not confirmed live).
- No scalar offset stably ≡ `+0x200[-1]` across multi armies.
- `+0x200` multi still visible as province-id candidate array (perception only).

## Works

- Focused named-string + soft/scalar agreement hunt
- Honest empty on strict family; documented loose `target_province` PE hits without overclaim
- Live multi path still readable (3 armies)

## Stubbed / HARD_DENY

- named demangled `movement_dest` · proven army↔OI membership
- ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk execute · CMove midflight hex

**Next shortest blocker (NON-Post):** Assign-stage membership sight (≤90s) OR human midflight CMove hex / SAFE Post for ring_embed; retry GitHub push when auth reachable; still **NO ALLOW_POST**.

Script: `scripts/phase2go_movement_dest_hunt.py`
Reports: `reports/phase2go_movement_dest_hunt.json`, `reports/phase2go_summary.json`

*Phase 2go · 2026-10-31 15:32 Asia/Shanghai*
