# t185 checkpoint — CCombatant combined unit-id list bound; CArmy combat pointer still unbound; nothing promoted

## Session

Live process rechecked first and again at the end of the batch: pid 26976, HOI4 1.19.5.0.7c6c, in_game, CInGameIdler, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Date 1936-01-01 12 (Asia/Shanghai wall clock is the box zone; the campaign date is the in-game date). Hour tick 60759371. Speed notch 1 (index 0). 21 own divisions. GS+0x268 combats size 0. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No test war, no orders, no leader assignments, no new army.

## CCombatant / CLandCombatant unit-id shape (complete)

`.pdata` of `0x147ff20` is only 7 bytes (push rbx / push rdi / sub rsp, 0x28). Disassembled through the tail `jmp 0x126a4c0`.

This function is the official serialize of **CCombatant** (vtable `0x2a367d0` slot +0x10). CLandCombatant (vtable `0x2a236a0` slot +0x10 = `0x134d5f0`) starts with `call 0x147ff20`, then writes the t184 front / reserves / retreat sublists.

CCombatant official fields:

- **`unit` (token 0x28a3)**: data +0x20, size +0x2c, omitted when size≤0. Each element is a CArmy*; official handle at elem+0x18 via `0x22857c0`. This is the official combined unit-id list for that side. Schema `Combat.attacker_unit_ids` / `defender_unit_ids` map to this array, **not** to a guessed union of front/reserves/retreat.
- `losses` +0xb8 (token 0x28f8)
- a size list at +0xa0 / +0xac, written iff size≠0
- `has_flanked_opponent` byte +0xdb (0x3517), written iff nonzero
- `last_hit` +0xe0 (0x30ac), written iff count>0
- `shore_bombardment_collateral_damage_factor` +0x10 (0x288d), written iff >0
- `weighted_participants` +0x80 (0x2a03), written iff [+0x90]≠0

CLandCombat (t184) still has attacker* +0x18 and defender* +0x20 pointing at CLandCombatant / CCombatant. The membership path is: CLandCombat side pointer → CCombatant `unit` array → unit handle +0x18.

`world.combats` is **not** promoted: CCombatManager is embedded at GS+0x260 (array at manager+0x8 = GS+0x268, already known), writer `0xc0eae0` emits `history` (0x2835). Live size is still 0. Empty GS_COMBATS is not written as false.

## CArmy current-combat pointer (still unbound)

`SArmyUnitActivityData` (vtable `0x29d7098`, writer `0x19eeaa0`, reader `0x19ee810`) is the official DTO for a unit's activity: **combat dword at +0x8** (token 0x2916, written iff nonzero via `0x25459e0`), **training dword at +0xc** (0x2fba, iff nonzero), **division handle at +0x10**. This is *not* embedded in CArmy (no vtable and no pointer in the 0x688 object). The vtable sits in rdata immediately after CArmy's +0x338 interface (`0x29d7030`); a first-pass read treated `0x19eeaa0` as a CArmy method at +0x338, which is wrong. Live CA+0x340 is a **CNameGroupMember*** on all 21 ETH divisions, not a combat id. Do not use CA+0x340 as `in_combat`.

Fill sites seen (`0xce8ea0`, `0xcecd10`, `0x1338c40`, `0x1468293`) copy or construct stack/array ActivityData records. No official CArmy slot that *sources* ActivityData.combat was bound.

The `pLandCombat` assert string at `0x2a04720` is referenced from `0x11105b0` (r14 is CArmy: location +0x1f0, path size +0x20c). The assert tests the result of `0x25c38b0` (typed lookup/cast) on rsi, not a proven CArmy field. Sibling `pMovingTo` assert calls `0xc52e90` after path size > 0; that is a moving-to candidate only, not `order.type`. `InCombat()` remains the navy carrier assert at 0x29f9547. No land IsInCombat getter is bound. Do not write `in_combat=false`.

## Command / OrderType

COrderInstance writer `0x10d1450` (vtable `0x2a026e8` +0x10) writes **type as dword [this+0x30]** with token `type` 0xe1 via `0x25459e0`. This is the same slot already seen in GetOrderType (`cmp [rcx+0x30], 1` ORDER_MOVE; `cmp …, 3` ORDER_INVASION). It is a **battle-plan COrderInstance**, not `world.own_units.order.type`. commandlist +8 is still unmapped; no live command object; do not invent OrderType. Empty commandlist/path is still not `idle`.

## Supply

CSupplyConsumer writer `0xf4ca30` (vtable `0x29cfa58` +0x10) writes id via `0x22858a0`, then `disrupted_supply` (0x4cf2) and `motorization_level` (0x4de7). **No `in_supply` or `isolated` token.** The class is not embedded in CArmy 0x688. GS+0x3d8 holds a live CSupplySystem*. Named-token search on CArmy is unchanged (out_of_supply_days / out_of_supply_factor / encirclement stats only). Do not invent a 0–1 ratio from 72/108.

## Inventory

D drive official table was **not** updated. Still 116 fields, 14 tables, 3 columns (`字段名 | 已验证/未验证 | 说明`), 43 verified / 73 unverified. SHA256 `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254`. `complete_input` remains false. Offset key `land_combatant_activity_t185` (`promoted: false`). 77 and [1835] were not promoted. No produced=min(need, stock).

## Tests

175 prior + 6 new = 181 passing (`research/test_t185_input_combatant_activity.py`).

## Honest boundary — remaining items that need a sample or a still-unfound named getter

Independent ABI work on this block has reached an honest boundary. Do not spin. The following cannot be promoted without a contrast sample or an official none-vs-unreadable CArmy reader that has not been found:

1. **`world.own_units.in_combat`** (and optional combat id): need a live land combat so a CArmy current-combat pointer or ActivityData.combat source can be contrasted, *or* a named land IsInCombat / stored flag on CArmy that distinguishes “none” from “unreadable.” Empty GS_COMBATS and the ActivityData DTO alone are not enough.
2. **`world.own_units.order.type` / target / path**: need one own division given a move (or other) order, *or* a proven commandlist-element +8 → OrderType map from a live command object. COrderInstance+0x30 is battle-plan only. Empty commandlist/path is not `idle`.
3. **`leaders.assigned_to`**: need one of the 20 ETH generals assigned to a division / army / army group. `is_assigned` is CScientist. All 20 remain unassigned; do not write `unassigned`.
4. **`formation.army_id` / `army_group_id`, `world.armies`, `world.army_groups`**: ABI is already bound (t184). Promotion needs at least one non-empty `orders_group` (create an army and put at least one own division in it) or a non-empty army group. Theatre unit list id 43 / units 1829–1849 is not `formation.army_id`. Empty group arrays are not verified false.
5. **`world.combats`**: CLandCombat / CCombatant / CLandCombatant unit-id shape is bound, but promotion needs a live combat. Do not write empty as false.
6. **`supply.in_supply` / `isolated` / 0–1 `supply.ratio`**: continue only with a named getter. CSupplyConsumer has no such token; 72.0 / 108.0 is not a 0–1 ratio.

Minimal user conditions (already reported; the agent must not create these samples): give one own division a move order; or provide a live combat; or assign one of the 20 ETH generals to a division / army / army group; or create one army and assign at least one own division.

Building damaged / overlay states remain restricted. 1552CF0 remains a string formatter.

## Next

No further independent ABI slice on these six fields is honest without the samples or a newly found named CArmy getter. Stop here rather than idle-scan. Authorization remains t169u for a later resume if the user provides a sample or a new independent target appears.
