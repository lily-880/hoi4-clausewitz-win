# Phase 2ijj — G1 Strategic-only acceptance path (NO Post)

**Result:** `G1_STRATEGIC_ONLY_ACCEPTANCE_PATH_HIT`  
**allow_post:** False · Instant peacetime **PARKED** · never 5x  
**Not this slice:** PATH densify · Instant empty · long midflight poll · Post / ring_embed execute / tool-gate

## Live RO reaffirm

pid 31788 · CONTINUOUS · day_index≈185 ui=1936-07-04 · exec advancing · Strat factory **4753 MATCH** · Strat VT FN MATCH · full MOVE family factory+FN MATCH · allow_post False · speed 1x CLI mem untouched

## G1 acceptance (alternate to midflight CMove)

G1 may be treated as **satisfied for SAFE Post discussion** via **Strategic-only path** when all hold:

| Proof | Status |
| --- | --- |
| Offline Strategic 0x50 rebuild bit_identical (2fd) | PASS · factory_idx 4753 · type_id 0x35b9 |
| Recipe v2 DESIGN + StartGame concordance (2gk) | DESIGN only · live ring_embed **STUBBED** |
| Live factory slot 4753 MATCH | **HIT this slice** |
| Live VT+0x48/0x50 IsValid/Execute FN MATCH | **HIT this slice** |
| Ordinary CMove midflight hex | still STUBBED — **not required** if Strategic-only accepted |

**Does NOT enable Post.** Still missing: **G2** ring_embed live · **G4** human ALLOW_POST · **G5** tool-gate · **G6** one Strategic Post @1x. G3 Instant remains PARKED (needed mainly for Move/Instant×PATH path).

## Path C progress honesty (t50u)

Baseline ~60%. G1 Strategic-only acceptance + live MATCH reaffirm clarifies SAFE Post path — **not** +10pp unlock (G2/G4+ still block). Estimated overall still **~60%** (maybe ≤+1–2pp readiness clarity; **~70% NOT crossed**).

## Artifacts

- `scripts/phase2ijj_g1_strategic_only_acceptance.py`
- `reports/phase2ijj_g1_strategic_only_acceptance.json` + `_summary.json`
- `docs/PHASE2IJJ_G1_STRATEGIC_ONLY_ACCEPTANCE.md`
- Folded SAFE_POST G1 + LAND_POST §6f

## Next shortest blocker

**G2** ring_embed live under human SAFE Post (after G4), or document exact ring_embed RO prep without Post. Ordinary CMove midflight no longer the only G1 gate if Strategic-only is accepted.
