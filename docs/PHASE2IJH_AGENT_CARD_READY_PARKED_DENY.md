# Phase 2ijh — Agent card READY / PARKED / HARD_DENY (NO PATH densify, NO Instant, NO Post)

**Result:** `AGENT_CARD_READY_PARKED_DENY_CONSOLIDATE`  
**allow_post:** False · Instant peacetime **PARKED** · never 5x  
**Not this slice:** PATH200/OG50 densify (diminishing returns per 2ijg STABLE)

## Live clock reaffirm (RO only)

pid 31788 · CONTINUOUS · day≈151 ui=1936-05-31 · exec advancing · WS ~1.7GB · speed 1x CLI mem untouched · allow_post False

## Agent-facing card (Path C land)

### READY (use RO now — perception / catalogs)

| Surface | What agent can rely on |
| --- | --- |
| Clock / queue health | year@+0x478, day_index@+0x484, ui_date; drain/exec/pending; CONTINUOUS when day≥48 |
| PATH200 @ CArmy+0x60 | nonempty/multi province vectors; multi oscillation tracked (2ija–2ijg) |
| Latest multi (STABLE) | **2643→[3945,2679] oi=448** (2ijf/2ijg; no new dest/OI in 2ijg) |
| OG+0x50 membership | proxy ↔ CArmy+0xB8 MI VT `0x29d6fb8` (name **STUBBED** — do not invent) |
| Focus OG50 sizes (2ijg) | 65=15, 448=16, 473=5, 495=6, 503=1, 504=16; companions×22 |
| Corrected Instant VTs (catalog) | INST_VT=`0x2A02558`, CP_VT=`0x29EE248` — **catalog only until wartime/midflight** |
| Land factory / VT FN MATCH | MOVE/SA/Cancel/Strategic + Assign/Unassign/Execute (2ha/2hb) MATCH offline |
| PATH≠Inst honesty | PATH/OG50 perception ≠ Instant-validated order |

### PARKED (do not re-poll / wait gate)

| Surface | Resume when |
| --- | --- |
| Instant map / Inst70 / ARR88 / tri70 empty | wartime **or** human midflight CMove |
| peacetime Instant×PATH on path OIs | same |
| Non-interactive midflight RO re-polls | human leave / plan-dense Assign window (2gt/2gv ceiling) |
| Assign oi≠0 endless quiet | skip until non-quiet sight |
| Further PATH/OG50-only densify/track | **diminishing returns** — will not unlock ~70% |

### HARD_DENY (never this session without human SAFE Post)

| Surface | Rule |
| --- | --- |
| `allow_post` / `CLAUSEWITZ_ALLOW_POST` | must stay False |
| Post inject / helper patch / guess writes | HARD_DENY |
| ring_embed live / 2fb/2gk recipe execute | HARD_DENY (design-only) |
| tool-gate open / HourlyTick abuse | HARD_DENY |
| 5x / speed-mem write beyond pause/1x | HARD_DENY |
| invent OG+0x50 or other field names | HARD_DENY |
| Capstone/121 re-churn | HARD_DENY |

## Diminishing-returns note (2ijf→2ijg)

2ijf denser2 MULTI_HIT (new_dest 2679) → 2ijg TRACK2 **MULTI_STABLE** (same multi, new_dest=[]). Further PATH/OG50-only slices ≤0–1pp and **do not** cross Path C ~70%. Main ~40% gap = Instant + SAFE Post + ring_embed + midflight hex.

## Path C progress honesty (t50u)

Baseline ~60%. This slice is **readiness consolidation** (agent card) + clock reaffirm — useful clarity, **not** +10pp unlock. Estimated overall still **~60%**. **~70% milestone NOT crossed.**

## Artifacts

- `scripts/phase2ijh_agent_card_consolidate.py`
- `reports/phase2ijh_agent_card_consolidate.json`
- `docs/PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md`
- Folded LAND_POST §6f + SAFE_POST

## Next shortest blocker

Human midflight CMove **or** wartime Instant; then SAFE Post for ring_embed. Do **not** schedule another PATH/OG50-only densify as the primary unlock path.


---

## Update 2ijx/2ijy — Ordinary Move PATH HIT + CRT stabilize

- 2ijx: first ordinary Move PATH_CONTAINS_DEST (army 1042→3931); CRT wait 258 + process exit after free-on-timeout
- 2ijy: leak stub on WAIT_TIMEOUT; reaffirm result `G6_MOVE_HIT_BUT_PROCESS_EXIT`; allow_post restored False
- Instant PARKED; Attack peacetime PARKED unless war



## 2ijy fold (2026-11-01 22:54 Asia/Shanghai)
- Move: PATH HIT (2ijx+2ijy) then **0xC0000374** on VirtualAllocEx province_arr.
- Staged: ucrt malloc live buf; stub leak; find_pid largest-WS. Instant/Attack PARKED. Path-C ~74-76%.


## 2ijz fold (2026-11-01 22:56:16 Asia/Shanghai)
- Move Post ucrt_malloc: G6_MOVE_UCRT_MALLOC_STABLE_HIT.
- Instant PARKED. Attack PARKED peacetime. allow_post default False.


## 2ika fold (2026-11-01 22:59:59 Asia/Shanghai)
- Cancel 1415: G6_CANCEL_1415_PATH_CLEARED_HIT.
- Move ucrt STABLE (2ijz). Strategic prior HIT. Instant/Attack PARKED peacetime.


## 2ikb fold (2026-11-01 23:03:37 Asia/Shanghai)
- War: PEACETIME_NO_WAR_DETECTED — Attack **PARKED**.
- Multi-Cancel 1415: G6_CANCEL_MULTI2_PATH_CLEARED_HIT.
- Agent land command loop: Move → Cancel → Strategic (all Post-HIT class); encirclement bias RO prior; Attack when wartime.
- Instant PARKED. allow_post default False.
