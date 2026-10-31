# Phase 2gh — Longer ITA war-day observe + heap Assign corner

**HEAD parent:** `c1c87a3` (2gg)  
**Result:** `ita_warday_and_heap_empty`  
**allow_post:** False (never opened)

## What ran

Preferred **A**: current ITA process (no relaunch); denser war window hours **18→25**; bounded **90.01s @1x** pending/stage multi-leaf observe (964 polls).

Preferred **B**: interleaved writable-heap VT needle scans for Assign (**3350** / vt `0x2a84498`), Unassign (**3365**), Execute (**3352**) — **25 runs**, ≤48 MB/run.

## Live

| field | value |
|-------|-------|
| pid | 30352 |
| hours | 18 → **25** |
| UI | 1936-01-01 18:00 → **1936-01-02 01:00** |
| speed | 1x only (never 5x) |
| scenario | ITA longer war-day + heap Assign corner |
| cmdline | `-gdpr-compliant -start_tag=ITA -start_speed=1` |

## Honest outcome

- pending/stage: Assign/Unassign/Exec/NF/Move = **0** (`sight={}`)
- heap corner: Assign/Unassign/Exec = **0** (25 runs, mb≤48)
- Same quiet class as 2gg day-1 and ETH 2gf — denser hours do not surface plan leaves in bounded RO windows. Do not invent.

## Works

- allow_post False; never 5x; no Post / inject / tool-gate / 2fb / Capstone
- Longer ITA war-day observe hours 18→25
- Heap Assign/Unassign/Execute corner (honest empty)

## Stubbed

ring embed · 2fb · SAFE_POST · self-MOVE · tool-gate · Post · HourlyTick · Capstone/121 · named +0x100/+0xe0 · RTTI 0x29d6fb8 · CArmy path · **live Assign/Unassign (pending+heap)** · midflight NF · CMove leaf

## Next shortest NON-Post blocker

RO ceiling — ITA war-day pending+heap plan leaves empty through denser hours — next cheapest **catalog-only Post-readiness checklist consolidate** (Assign/Exec/NF packing + IsValid/factory already mapped) **or** pause-and-UI-plan scenario (still no ask-user right-click / no Post); **still NO ALLOW_POST**.

## Artifacts

- `scripts/phase2gh_ita_warday_heap.py`
- `reports/phase2gh_summary.json`
- `reports/phase2gh_ita_warday_heap.json`
