# t189 checkpoint — crises / land FoW / damaged buildings not promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, CInGameIdler, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Date 1936-01-01 12, hour tick 60759371, speed index 0 (1x setting), official pause flag CInGameIdler+0x6c1 = 1. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No orders, appointments, army creation, or plan drawing.

## Crises

No official persistent table was bound to schema `Crisis` (`kind`, `unit_ids`, `province_ids`, `severity`). Function `0x1571ef0` (caller `0x156c870` at `0x156cab2`) computes a dword province-id array at **result+0x148**, named `_EncirclementPoints` in the assert string at `0x2a460a0` (points must not be sea). This is a geometry / highlight computer fed from a front-or-order province list, not a standing `world.crises` row. CTheaterGroup remains empty worldwide (t188). UI `ALERT_*` keys (low supply, missing equipment) are not the schema kind enum. An empty or unmapped table was **not** written as “no crisis”.

## Visibility / FoW

- Token `visible` 0x2d2a at `0xf0a978` belongs to a **map/gfx** object writer (`z`, `scale`, `rotation`, `animation`, `min_zoom`).
- Token `already_spotted` 0x3bb3 remains a **naval mission** writer (t188); not land `visibility.spotted`.
- Token `intel` 0x30ec at `0xd689d0` is **national intel pools** (`intel_from_allies`, `static_intel_pools`, `dynamic_intel_pools`, encryption/decryption), not per-unit spotted or 0–1 confidence.

No official land-unit spotted+confidence getter was bound. Foreign-army objects were not exported as player-visible units.

## Building damaged / extra effective levels

Official native slots are unchanged: CBuilding **+0x40 level**, **+0x42 healthy**, overlay arrays **+0x10** and **+0x28**; numeric entry `0x1201750` / `0x12017E0` plus `0x1162FE0` overlays. **1552CF0 remains a string formatter.**

Live official-container scan: 1081 states (`CState+0x120` all `CBuildingStatus`), 2140 state buildings; 10272 provinces via the live `CState+0x18` CProvince* array (ETH state 271 starts at province 5010; the CState writer `0xa2bbc0` does not emit a `provinces` token at that slot), 4560 province buildings at `CProvince+0x190`. **Damaged (healthy < level) = 0. Nonempty overlays = 0.** Every present building is undamaged with empty overlays. That cannot lift the inventory restriction “限未建或无损且无额外加级”, and cannot invent damaged or extra-level semantics.

## Inventory

D drive official table **was not updated**. Still 116 fields, 14 tables, 3 columns, 47/69. SHA256 `98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201`. `complete_input` remains false. Offset key `crisis_fow_buildings_t189` (`promoted: false`). 77 and [1835] were not promoted. world.crises.*, world.visible_units.visibility.*, and the damaged/overlay limitation on infrastructure/fort fields remain as they were.

## Tests

199 prior + 6 new = 205 expected (`research/test_t189_input_crisis_fow_buildings.py`).

## Next

The three targets in this block reached an honest sample-or-named-getter boundary: crises need a stored typed crisis row (or a live encirclement object in an official container), land FoW needs a unit-scoped spotted/confidence getter that is not naval `already_spotted`, gfx `visible`, or national intel pools, and damaged/extra building levels need a live damaged or nonempty-overlay contrast (do not manufacture one). Independent work can continue on other still-unverified inventory fields that do not depend on the six blocked samples, on drawing a plan, or on those contrast states. `world.wars.front_invalidated` still has no named token. Do not issue orders or damage buildings on the user’s behalf.
