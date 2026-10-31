# Phase 2fn — Assign/Unassign edge deepen

**Result:** `ASSIGN_UNASSIGN_EDGE_DEEPENED`  
**Base:** `87bd306` (2fm) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## CPdxArray units @ +0x28 (both)

| off | Assign / Unassign |
|-----|-------------------|
| +0x28 | units_data |
| +0x30 | units_capacity |
| +0x34 | units_count (size) |
| +0x38 | units_alloc |

Sibling fit: MassCancel / NewFallback units packing (2fm).

## Trailing fields

- **Assign:** `order_index@+0x48`, `assign_to_minimum_order@+0x4C`
- **Unassign:** `unassign_group@+0x48`, `unassign_army_group_instances@+0x49`

## Stage neighbors (prior)

- **2ex ITA:** HourlyTick · Assign stage[9] · Unassign stage[13] · Cancel
- **2fa ETH:** Assign stage[1]/[45..47] · StrategicRedeploy · HourlyTick

## Type-id polish

`HANDLE_TYPE_ARMY = 0x33` (51). NewFallback `subject_handle` type still open (order-domain).

## Live sight (75.0s)

assign_seen=True unassign_seen=True fallback_seen=False  
counts={"CHourlyTickCommand": 48069, "CCancelMovementCommand": 1, "COrderAssignCommand": 2, "COrderUnassignCommand": 2}

```json
{
  "pid": 34188,
  "hours": 135,
  "ui_date": "1936-01-06 15:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ITA@1x Assign/Unassign edge deepen (no Post)",
  "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1"
}
```


## Live on-stage captures (ITA @1x, 75s)

- **Assign** stage[17]: units CPdxArray data≠0 cap=4 size=4; order_index=6; VT match. Proves packing.
- **Unassign** stage[7]/[8]: units size=1; unassign_group=1.
- One later “Assign” capture shows wrong VT in hex → post-drain race (blob after free); ignore that row’s packing.
- Observed u32@+0x40 = `0x35` on good Assign/Unassign rows (between units_alloc end and order_index/unassign_group); **unnamed** — no invent.

**Next shortest blocker (NON-Post):** NON-Post: on-stage Assign/Unassign hex with nonzero units_count OR NewFallback subject type-id from midflight; still NO ALLOW_POST
