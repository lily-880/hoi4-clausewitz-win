# t190 checkpoint — remaining 69 unverified fields triaged; none promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, CInGameIdler, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Date 1936-01-01 12, hour tick 60759371, speed index 0 (1x setting), official pause flag CInGameIdler+0x6c1 = 1. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No orders, appointments, army creation, plan drawing, or manufactured damage/encirclement.

## Triage of the 69 unverified fields

Every remaining unverified inventory field was classified. **None can be honestly promoted on this snapshot.** Nothing was split to inflate the count, and config/ledger fields were not marked 已验证.

### 12 are not memory fields

- `meta.allow_write`, `meta.geography_scope`: already documented as configuration (default false / null).
- `policy.stance`, `policy.instructions`: player policy / interface defaults, not memory discoveries.
- `feedback.last_orders.*` (7) and `feedback.ticks_since_issue`: local command receipt ledger, not memory fields.

These stay 未验证. They do not become verified just because a default exists.

### 57 already need a contrast sample or sit on a recorded boundary

- **Combat / order / supply / formation / leaders.assigned_to** (30): the six blocked clusters. Empty command, combat, orders_group, and assignment tables still must not be written as false/idle/unassigned.
- **Plans** (8): official object is COrderInstance; live world count is 0; the 6/910 CFronts are border structures (t188).
- **Visible units / FoW** (4): no land-unit spotted/confidence getter; gfx `visible`, naval `already_spotted`, and national `intel` pools are not that getter (t188–t189). Foreign armies must not be exported as player-visible units.
- **Crises** (5): no official persistent table mapped to the Crisis schema (t189).
- **world.wars.front_invalidated** (1): no named token.
- **Equipment shortages** (4): the 77 / [1835] / `produced=min(need,stock)` trail stays closed.
- **Manpower needed / deficit / affected_unit_ids** (3): official per-division gap remains `CC6480 = max(sum(need table)−sum(value table), 0)` (value table at CArmyManpower+8, need table at +0x28; CC6570 uses data at table+8, size at table+0x14). Live recheck: 21 own divisions, backlinks OK, **current total = need total = 105000, gap = 0**. There is no under-strength contrast, and no separate official country-level `needed` writer (the `need` token at `0x15ab8c4` belongs to the reinforcement produced/need row; `0x108660d` is garrison). A full-strength zero is not promoted as country `manpower.needed` / `deficit` / empty `affected_unit_ids`.
- **front_cannot_hold / missing_divisions** (2): need a front that cannot hold.

## Inventory

D drive official table **was not updated**. Still 116 fields, 14 tables, 3 columns, 47/69. SHA256 `98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201`. `complete_input` remains false. Offset key `unverified_triage_t190` (`promoted: false`). 77 and [1835] were not promoted.

## Tests

205 prior + 6 new = 211 expected (`research/test_t190_input_unverified_triage.py`).

## Honest stop

On this ETH 1936-01-01 snapshot, **there is no remaining unverified inventory field that can still be independently promoted without a new contrast sample or a contract decision that config/ledger may be marked verified**. The standing samples already reported — and not to be performed by the agent — remain: issue one move order to one own division; provide a live land combat; assign one of the 20 ETH generals; create one army (`orders_group`) and assign at least one own division; draw one player plan; and, only if those shortage/building/crisis fields are wanted, an under-strength division, a damaged or overlay-bearing building, or a live encirclement/crisis row. Do not manufacture those states.
