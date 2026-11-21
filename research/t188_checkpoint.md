# t188 checkpoint — plans not promoted (empty COrderInstance / border CFront only)

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, CInGameIdler, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Date 1936-01-01 12, hour tick 60759371, speed index 0 (1x setting), official pause flag CInGameIdler+0x6c1 = 1. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. Pause/speed were not toggled for contrast.

## Official plan objects vs border fronts

Player-drawn plans are **COrderInstance**, not CFront.

- Writer `0x10d1450` (vtable `0x2a026e8` +0x10) writes **type** as dword `[this+0x30]` with token `type` 0xe1; **instance_id** `[this+0x244]` token 0x30af; **path** array +0x70 token 0x174; **states** array +0xe0 token 0x2e3b; also `can_execute` 0x30b2 (this is not `plans.executing`), `order_children`, `fallback`, `midpoints`, `root_front` / `root_section`, `area_defense_settings` / `area_defense_state_assignment`.
- GetOrderType on that same +0x30 slot is proven only for **1 = ORDER_MOVE** (assert 0x10b2c8a / string `GetOrderType() == ORDER_MOVE`) and **3 = ORDER_INVASION** (assert 0x10b038e). Type 4 is compared near ORDER_PARADROP UI; type 5 is used in instance code but not named. Schema `frontline` / `offensive_line` / `garrison` / `area_defense` are therefore **not** numerically bound.
- COrdersGroup writer `0xc4d030` emits token `order_instance` 0x35f7 from the array at **+0x98 / size +0xa4**. Group-level `execution_type` 0x36aa is also not proven as `plans.executing`.
- Official hang-off: CTheatre `orders_group` token 0x30ae at **+0x80 / +0x8c**.

CTheatre **front** token 0x29e0 at +0x50 / +0x5c is a different object. CFront writer `0xf809b0` writes `dirty`, `provinces`, `enemies`, `id_counter`, `section`, `area` — no type / instance_id / path / executing. These are border structures.

## Live snapshot

ETH: one CTheatre id 43, **orders_group / field_marshal_group / theater_group all size 0**, **0 COrderInstance**. Six objects at +0x50 are all `.?AVCFront@@` (ids 420–425, handle type 66). World walk of official country theatre containers: 99 theatres, **910 CFronts**, **0 COrdersGroup**, **0 COrderInstance**. Path / vertices / assigned armies or units / executing cannot be shown on a live plan object.

`already_spotted` token 0x3bb3 belongs to a **naval mission** writer (mission / radar / navy_engagement_rule / spotting_target around 0x104353b), not `world.visible_units.visibility.spotted`.

## Inventory

D drive official table **was not updated**. Still 116 fields, 14 tables, 3 columns, 47/69. SHA256 `98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201`. `complete_input` remains false. Offset key `plan_orderinstance_t188` (`promoted: false`). 77 and [1835] were not promoted. world.plans.*, world.crises.*, world.visible_units.visibility.*, world.wars.front_invalidated remain 未验证.

## Tests

193 prior + 6 new = 199 expected (`research/test_t188_input_plans.py`).

## Next

Independent ABI can continue, still without the six blocked samples and without promoting empty plan tables or border CFronts: **crises**, **visibility / FoW** spotted+confidence (do not treat naval `already_spotted` as land FoW; foreign-army samples may prove structure, do not export fog-hidden situation), and building damaged / extra effective levels (1552CF0 remains a string formatter). `world.wars.front_invalidated` still has no named token.

Promoting `world.plans.*` still needs at least one **player-drawn** COrderInstance (create an army / orders_group and draw a frontline or other plan). That is a standing optional condition only for those fields; other work does not wait on it. Do not issue that order on the user's behalf.
