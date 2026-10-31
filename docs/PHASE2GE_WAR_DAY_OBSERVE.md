# Phase 2ge — Longer war-day observe + catalog leaf polish

**HEAD parent:** `823c935` (2gd)  
**Result:** `war_day_nf_rf_and_path_empty`  
**allow_post:** False (never opened)

## What ran

Preferred **A** on **current** ETH process (pid 14248, no relaunch): bounded **90.08s @1x** observe (789 polls) through a denser war window than 2gd dawn.

Preferred **B** (because A empty): catalog-only leaf polish snapshot from existing **2fl/2fm** maps — deltas only, **no Capstone/121**.

## Live

| field | value |
|-------|-------|
| pid | 14248 |
| hours | 19 → **26** |
| UI | 1936-01-01 19:00 → **1936-01-02 02:00** |
| speed | 1x only (never 5x) |
| scenario | ETH war-day current-process AI-on |
| cmdline | `-gdpr-compliant -start_tag=ETH -start_speed=1` |

## Honest outcome (A)

- **NF/RF captures:** 0
- **path vector nonempty armies:** 0
- **catalog soft 0x2b4:** 0
- Same empty class as 2gd/2fj/2fk; denser window (into Jan 2) still emitted no Fallback midflight leaf and no nonempty movement path vectors. Do not invent.

## Catalog polish deltas (B)

From `cmd_layout.ORDERS["COrderNewFallbackCommand"]` (already baked by 2fl/2fm/2fg) — **no new Capstone**:

| item | value |
|------|-------|
| vt | `0x2a84c80` |
| type_id | `0x33d7` |
| factory_idx | **4271** (2fg tid-0x2328) |
| size | `0x60` |
| subject_handle | +0x28 |
| units CPdxArray | data+0x30 / cap+0x38 / count+0x3c |
| provinces CPdxArray | data+0x48 / cap+0x50 / **size+0x54** |
| fields_note | 2fm: +0x54=`provinces.size` (not AG fallback_flag); subject_handle via gate `0xbbb1e0` |
| RF soft vt | `0x2a84d38` |

**Delta vs prior docs:** none new — catalog already complete for NF packing; this slice only **re-affirms** no live hex to deepen against.

## Works

- allow_post False; never 5x; no Post / inject / tool-gate / 2fb / Capstone re-churn
- Current-process war-day observe hours 19→26
- Catalog-only leaf polish snapshot (deltas: none beyond 2fm)

## Stubbed

ring embed · 2fb · CMove · SAFE_POST · self-MOVE · tool-gate · Post · HourlyTick · Capstone/121 · named +0x100/+0xe0 · RTTI 0x29d6fb8 · **live midflight NF hex (empty this war-day window)** · **named CArmy path offs**

## Next shortest NON-Post blocker

RO ceiling — war-day NF/path empty through hours 19–26 — next cheapest is **Assign/Unassign edge deepen** or leaf **IsValid gate RO polish** from existing maps; **still NO ALLOW_POST**.

## Artifacts

- `scripts/phase2ge_war_day_observe.py`
- `reports/phase2ge_summary.json`
- `reports/phase2ge_war_day.json`
