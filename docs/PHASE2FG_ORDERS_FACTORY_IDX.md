# Phase 2fg — ORDERS factory_idx catalog fill

**Result:** `ORDERS_FACTORY_IDX_FILLED_LIVE_MATCH`  
**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**

## ORDERS factory_idx (was missing → filled)

| command | type_id | factory_idx |
|---------|---------|-------------|
| COrderExecuteCommand | `0x3040` | **3352** |
| COrderAssignCommand | `0x303e` | **3350** |
| COrderUnassignCommand | `0x304d` | **3365** |
| COrderDeleteCommand | `0x303f` | **3351** |
| COrderNewFrontCommand | `0x3327` | **4095** |
| COrderNewRootCommand | `0x3328` | **4096** |
| COrderNewFallbackCommand | `0x33d7` | **4271** |
| COrderGroupCommand | `0x2ecf` | **2983** |
| CArmyGroupCommand | `0x3861` | **5433** |
| CSetArmyLeaderCommand | `0x3051` | **3369** |

## Live factory table verify

- MATCH: **26** · MISMATCH: **0** · skip: 0
- table RVA `0x35011e0`

## Also filled

- `CCancelRunningAwayCommand.factory_idx` **6284** (LAND_ARMY_FOCUS gap)

## Core land (already filled 2fe)

- MOVE 1402 · STRATEGIC **4753** · CANCEL 1415 · SUPPORT_ATTACK 3620

## Live

```json
{
  "pid": 9928,
  "hours": 99,
  "ui_date": "1936-01-05 03:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ETH@1x ORDERS factory_idx catalog RO (no Post)"
}
```

**Next shortest blocker (NON-Post):** NON-Post: short ETH@1x path-vector re-observe for nonempty movement_dest (bounded) OR SupportAttack/Cancel leaf hex sight — still NO ALLOW_POST

Script: `scripts/phase2fg_orders_factory_idx.py`
