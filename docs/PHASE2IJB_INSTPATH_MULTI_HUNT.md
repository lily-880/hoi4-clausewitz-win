# Phase 2ijb — Instant×PATH hunt on multi_n=2 (NON-Post)

**Result:** `INSTPATH_MULTI_PATH_INST_EMPTY`  
**allow_post:** False · **Speed:** 1x CLI mem untouched · never 5x

## Live

- pid 31788 ITA · CONTINUOUS · day 85→90 (+5 during 60s nudge) · ui 1936-03-31 · WS ~1.7GB
- One short 1x nudge only; **no** Instant-empty re-poll loop

## Instant×PATH matrix (focus OIs)

| oi | inst_ok | og50_size | arr70_n | notes |
|----|---------|-----------|---------|-------|
| 65 | false | 23 | 0 | multi 2647→[3938,415] |
| 450 | false | 12 | 0 | multi 2683→[740,2601] |
| 448 | false | 23 | 0 | companion cluster |
| 478 | false | 0 | 0 | |
| 45/55/58 | false | low/0 | 0 | prior thin PATH OIs |

multi_n=**2** stable; nonempty=26; new_oi=[473]; Inst70/ARR88 empty; tri70/tri70_88 none.

## PATH≠Inst honesty (agent-facing)

Multi-prov PATH + fat OG+0x50 can exist with Instant VT false on the same OI. Do **not** treat PATH dest as Instant-validated order. OG+0x50 field name still STUBBED.

## Artifacts

- `scripts/phase2ijb_instpath_multi_hunt.py`
- `reports/phase2ijb_instpath_multi_hunt.json` + `_summary.json`
- Folded LAND_POST / SAFE_POST §6f catalog

## Stubbed / HARD_DENY (unchanged)

ring_embed · Assign · midflight · Instant-map/empty re-polls · 2fb/2gk · ALLOW_POST · Post inject · 5x · speed-mem write · invent OG+0x50 name · Capstone/121

## Next shortest blocker

Instant not surfacing on path OIs under peacetime AI 1x alone — human midflight CMove (or wartime/orders that spawn Instant) needed for Instant×PATH; SAFE Post/ring_embed still NO ALLOW_POST. Do not keep Instant-empty polling.
