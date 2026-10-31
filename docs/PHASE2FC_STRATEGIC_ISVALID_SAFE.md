# Phase 2fc — Strategic IsValid path + SAFE checklist (RO)

**Result:** `STRATEGIC_ISVALID_PATH_DOCUMENTED_SAFE_STILL_CLOSED`  
**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**

## IsValid path (catalog + 2fb)

| piece | RVA |
|-------|-----|
| wrap IsValid | `0x22d8ea0` |
| CStrategicRedeploymentCommand.IsValid | `0x1402260` |
| cmd type_id | `0x35b9` (`0x35b9`) |
| CUnitStrategicMoveAction.IsValid | `0x12c2c20` |
| action type_id (@embed+8) | `0x364a` |
| shared execute thunk (w/ MOVE) | `0x13fc990` |
| action.execute | `0x12c3190` |

### Call path (observation only)

1. Queue/Dummy may hit wrap `0x22d8ea0`
2. Cmd IsValid `0x1402260`
3. Action IsValid `0x12c2c20`
4. Execute: thunk `0x13fc990` → embed+`0x28` → `0x12c3190`

Catalog IsValid callees: `0x57f7b0, 0x1e1510, 0x2607890`  
vs MOVE: shared `0x1e1510, 0x2607890`; strategic-only `0x57f7b0`.

**Do not Capstone/121 re-churn these callees.**

## Must be true before any future Post

| id | status |
|----|--------|
| layout_match | DONE_2fb |
| live_leaf_sample | DONE_2fa_strategic |
| isvalid_path_documented | DONE_2fc |
| ring_recreate_proof | **STUBBED** |
| human ALLOW_POST env | **HARD_DENY** |
| tool-gate open | **CLOSED_NOT_OPENED** |

## Ordinary CMove (cheap note)

Catalog layout complete (`vt 0x2a2c790`, size `0x88`). Live sample still stubbed — **not hunted this slice**. Strategic remains cheaper ring_embed design target.

## SAFE updates

- `docs/SAFE_POST_ENABLE_CHECKLIST.md` — 2fc section appended; gate CLOSED
- `research/safe_enable_checklist.json` — `notes_2fc` + blocks refreshed; `allow_post: false`

2fb recipe present: **True** — still DESIGN ONLY.

## Next shortest blocker

Dummy **ring recreate proof** design/observe for Strategic sample — **still NO ALLOW_POST**, do not execute recipe.

Script: `scripts/phase2fc_strategic_isvalid_safe.py`
