# Phase 2fb — StrategicRedeploy layout-only decode

**Result:** `STRATEGIC_LAYOUT_DECODE_MATCH`  
**Source:** 2fa capture `0x26bf0828b90` stage seq 6260 (Asia/Shanghai 2026-10-31 11:44:39)  
**Method:** offline hex decode — **no live re-grab**, no Capstone/121, **allow_post = False**

## Catalog match

All checks: **True**

| check | ok |
|-------|----|
| cmd vt `0x2a2d818` | True |
| embed vt `0x2a1f7e8` | True |
| action type_id@+8 `0x364a` | True |
| fields vs 2fa dump | army/prov/clear/mp all match |

## Command object (`CStrategicRedeploymentCommand` size `0x50`)

| off | field | live |
|-----|-------|------|
| +0x00 | vt | RVA `0x2a2d818` |
| +0x0C | tick | 1 |
| +0x1C | seq | 6260 |
| +0x20 | (echoed seq this sample) | 6260 |
| +0x28 | **action embed** | `CUnitStrategicMoveAction` |

## Embed (`CUnitStrategicMoveAction` size `0x28` @ cmd+0x28)

| off | field | live | token |
|-----|-------|------|-------|
| +0x00 | vt | `0x2a1f7e8` | — |
| +0x08 | type_id | `0x364a` | — |
| +0x10 | army_handle | `[51, 1092]` | `0x289D` |
| +0x18 | province | `11874` | `0x2840` |
| +0x1C | clear | `1` | `0x29F1` |
| +0x20 | move_priority | `2` (PLAYER_ORDER) | `0x37BC` |

## Neighbors vs MOVE / Cancel

- **Shared execute thunk** with MOVE: `0x13fc990` → embed → action.execute `0x12c3190`
- **Shared serialize/deserialize thunks** with MOVE
- **Cheaper than ordinary MOVE for ring_embed design:** scalar province — no province_arr/path_arr game allocs
- Cancel remains adjacent traffic proof; ordinary CMove still stubbed

## ring_embed recipe (OBSERVATION ONLY)

See `reports/phase2fb_ring_embed_recipe.json`.

**Writes FORBIDDEN. Post FORBIDDEN. SAFE_POST CLOSED.**

Birth path (observe): factory `0x13fb580` → size `0x50` → Post/sink/ring → execute thunk → action.execute.

## Next

IsValid-path / SAFE checklist RO around this design — **still NO ALLOW_POST**. Do not Capstone/121 re-churn.

Script: `scripts/phase2fb_strategic_layout_decode.py`
