# Phase 2iy — calendar/sim unblock → denser PATH200 (NON-Post)

**Result:** `PATH200_CALUNBLOCK_DENSE_HIT`  
**allow_post:** False (untouched)  
**Speed:** 1x CLI launch only — **no** speed memory write; never 5x.

## Stall diagnosis (prior pid 33840)

| Signal | Value |
|--------|-------|
| day_index @+0x484 | stuck **13** |
| exec | flat **8182** |
| drain | still rising (~101k) |
| WorkingSet | collapsed **~238 MB** (healthy map ~4–5 GB) |
| session | `in_game` / CInGameIdler / window title ok / Responding |

**Cause:** softlock — process window alive but sim dead (exec/calendar frozen) while drain counter still ticked. Space/unpause alone (2ix) could not recover a hollowed process.

**Fix:** self-relaunch  
`hoi4.exe -gdpr-compliant -start_tag=ITA -start_speed=1` (+ AI on via launch_into_map `--allow-ai`).  
New pid **31788**, WS ~4.8 GB, map ready; day_index and exec advance under 1x.

## Calendar proof (this slice)

- sample 10s: day **10→11**, exec **7576→7773**, ui **1936-01-11→1936-01-12**
- clock_class: `RELOAD_OR_NEW_CAMPAIGN`

## PATH200 denser dig (catalog-only)

| Metric | 2ix thin | 2iy after relaunch |
|--------|----------|--------------------|
| nonempty / multi | 2 / 0 | 2 / 0 |
| armies | 1040→[12857] oi=70; 1053→[9945] oi=57 | 1040→[12857] oi=**55**; 1053→[9945] oi=**45** |
| new_dests | [] | [] |
| new_ois | [] | **[45, 55]** |
| inst_ok_ois | [] | [] |
| by_class | focus_oi_seed×2 | path_only×2 |

Inst70 / ARR88 empty on dug OIs (single Instant VT check; no Instant-empty re-poll). OG+0x50 reverse hit path membership for 45/55 — field **name still STUBBED**.

## Artifacts

- `scripts/phase2iy_path200_calendar_unblocked.py`
- `reports/phase2iy_path200_calendar_unblocked.json` + `_summary.json`
- Folded: `docs/LAND_POST_READINESS.md`, `docs/SAFE_POST_ENABLE_CHECKLIST.md` §6f pointers (catalog)

## Stubbed / HARD_DENY (unchanged)

ring_embed · Assign oi≠0 · midflight · Instant map / hi-band Instant-empty / 463 Inst70 / OG575 Instant-empty · 2fb/2gk · ALLOW_POST · tool-gate · Post inject / historical phase2iw_one_strategic_post / phase2ix_strategic_isvalid_post / phase2iy Post · never 5x · ask right-click · long midflight empty poll · speed write beyond pause/1x · invent OG+0x50 name

## Next shortest blocker

Human midflight CMove or SAFE Post for ring_embed still NO ALLOW_POST; denser multi-path may need CONTINUOUS clock / later date / more AI movement — calendar now healthy so longer 1x wall is valid again (no softlock).
