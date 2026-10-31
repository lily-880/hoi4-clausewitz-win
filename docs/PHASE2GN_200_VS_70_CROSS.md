# Phase 2gn — CArmy+0x200 ↔ Instance+0x70/+0x88 cross (RO)

**Result:** `CROSS_200_VS_70_NO_OVERLAP`
**Live:** pid 30352 · 1936-01-05 18:00 · hours=114 · tag=15
**+0x200 multi armies:** 3 (1045 n=54, 1046 n=54 identical, 1048 n=3) · **Instance+0x70 shaped:** 57 · **any overlap:** False
**Membership:** Instance/OG army-handle scans **0** hits · CArmy oi_u32 hits **noisy/untrusted** (type echo/sizes/tag)

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Method

1. Re-read ITA CArmy `+0x200` CPdxArray<u32> (filter country-tag singletons).
2. Resolve wide OI set (1..95) → COrderInstance via OG+0x98; read `+0x70` / `+0x88` province ids.
3. Cross each multi `+0x200` vs each shaped `+0x70` / `+0x88` (equal / set / subseq / overlap).
4. Heuristic membership: Instance/OG for `{0x33, army_ix}`; CArmy for oi-like u32s.

## Semantics (this window)

- **NO OVERLAP** between any multi `CArmy+0x200` and any shaped Instance`+0x70` (or sampled `+0x88` province ids).
- Extends **2fy** `inst70_no_overlap` specifically against the **2gm `+0x200` candidate**.
- `+0x200` remains a **province-id candidate array**, **not** the order/front path (`+0x70`).
- Named `movement_dest` still **NOT_DEMANGLED**. Proven army↔OI membership field still **STUBBED**.

## Works

- Focused `+0x200` ↔ `+0x70`/`+0x88` cross with dense OI seed (57 shaped)
- Honest negative: no equal/set/subseq/overlap
- Membership handle scans empty; oi_u32 noise classified

## Stubbed / HARD_DENY

- named demangled `movement_dest` / proven membership field
- ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk execute · CMove midflight hex

**Next shortest blocker (NON-Post):** CArmy`+0x200` ⊀ Instance`+0x70` this window (RO ceiling on link) — optional Assign-stage membership sight OR named movement_dest hunt; human midflight CMove / SAFE Post for ring_embed; push when GitHub reachable; still **NO ALLOW_POST**.

Script: `scripts/phase2gn_200_vs_70_cross.py`
Reports: `reports/phase2gn_200_vs_70_cross.json`, `reports/phase2gn_summary.json`

*Phase 2gn · 2026-10-31 15:29 Asia/Shanghai*
