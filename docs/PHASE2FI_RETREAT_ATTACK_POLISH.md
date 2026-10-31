# Phase 2fi — retreat/attack catalog field polish

**Result:** `RETREAT_ATTACK_FIELD_POLISH_OK`  
**Base:** `ef62e72` (2fh) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb recipe **NOT executed**

## Field maps (proven only — no invent)

| layout | fields |
|--------|--------|
| `SUPPORT_ATTACK` | unit_or_attacker_handle@+0x28, target_province@+0x30 |
| `CANCEL_RUNNING_AWAY` | units_data@+0x28 |
| `WITHDRAW_ARMY_HQ` | hq_handle@+0x28 |
| `ARMY_GROUP_FALLBACK` | army_group@+0x28, fallback_flag@+0x30 |
| `MASS_CANCEL` | units_data@+0x28, units_count@+0x34 |
| `ORDER_REPLACE_FALLBACK` | fallback_flag_or_id@+0x54 |
| `ORDERS.COrderNewFallbackCommand` | fallback_flag_or_id@+0x54 |

## LAND_ARMY_FOCUS.core

Keys: `['move', 'strategic_redeploy', 'cancel_movement', 'attack_support', 'retreat_fallback']` (added **retreat_fallback** → CANCEL_RUNNING_AWAY)

## Live factory table

- MATCH: **10** · MISMATCH: **0** · skip: 0

## CancelRunningAway live VT fills

- ['CANCEL_RUNNING_AWAY.clone=0x13f8e80', 'CANCEL_RUNNING_AWAY.serialize=0x14041b0', 'CANCEL_RUNNING_AWAY.deserialize=0x1402e00', 'CANCEL_RUNNING_AWAY.gettypeid=0x13fe2e0', 'CANCEL_RUNNING_AWAY.gate_0x60=False', 'CANCEL_RUNNING_AWAY.gate_0x80=False']

## Live

```json
{
  "pid": 9928,
  "hours": 115,
  "ui_date": "1936-01-05 19:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ETH@1x retreat/attack catalog field polish (no Post)"
}
```

**Next shortest blocker (NON-Post):** NON-Post: peacetime ETH RO ceiling on midflight path/leaf — next cheapest: pause+1x war-dense relaunch observe (ITA/ETH war) for nonempty path OR leaf sight; still NO ALLOW_POST

Script: `scripts/phase2fi_retreat_attack_polish.py`
