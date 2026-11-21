# t184 checkpoint — CTheatre / group / CLandCombat writers bound; nothing promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No test war, no orders, no leader assignments.

## Official handle

`0x22858a0` writes token `id` (0xb) from **this+0xc** and token `type` (0xe1) from **this+0x8**. `0x22857c0` is the same layout when `r8` already points at the handle: type=`dword [r8]`, id=`dword [r8+4]`. Groups use `r8=object+8`; CArmy uses `r8=object+0x18` (matches the already-verified unit_id at +0x1c).

## Formation ABI

CTheatre writer `0xf81510` (vtable 0x29f22b8) starts with `0x22858a0`. Official arrays, all omitted when size≤0:

- `area` (0x2b95): data +0x18, size +0x24; province id at `[elem+0x28]+0xa4` (elem is CControllerArea)
- `front` (0x29e0): data +0x50, size +0x5c
- `unit` (0x28a3): data +0x68, size +0x74; each pointer is CArmy*, handle at +0x18 via `0x22857c0`
- `orders_group` (0x30ae): data +0x80, size +0x8c; virtual-serialize the COrdersGroup*
- `field_marshal_group` (0x3801): data +0x98, size +0xa4; CArmyGroup*
- `theater_group` (0x35d1): data +0xc8, size +0xd4; CTheaterGroup*

COrdersGroup writer `0xc4d030` (schema role: world.armies / 集团军): id via `0x22858a0`; name at +0x160; members at +0x50 / size +0x5c, each resolved to a unit handle at +0x18; leader pointer +0x88 with handle at +8; `order_instance` collected from +0x98 / +0xa4; `field_marshal_group` at +0x39 is a **boolean flag**, not a parent id.

CArmyGroup writer `0xc4cfa0` (schema role: world.army_groups / 集团军群) is derived: child `orders_group` array at +0x230 / size +0x23c (handles at child+8), `collapse` byte +0x248, then `jmp 0xc4d030`.

CTheaterGroup writer `0x16d9e10`: id via `0x22858a0`, priority +0x20, name +0x28, child orders_groups at +0x48 / +0x54.

Live ETH: one CTheatre, official id 43 (type 67). **unit array size 21**, ids 1829–1849, all CArmy* — every own division is a theatre member. orders / field_marshal / theater groups are all size 0. area size 1 (province 5010). front size 6 is a structure candidate only, not promoted as plans. The theatre unit list is **not** `formation.army_id`.

## Combat ABI

CLandCombat serialize is vtable 0x2a23898 +0x10: `0x134d5e0 jmp 0x147fe80`. Writer `0x147fe80`: id via `0x22858a0`; location CProvince* at +0x28, id at +0xa4 (token 0x286d); day +0x30; duration +0x34; attacker* +0x18 (token 0x28f5) and defender* +0x20 (0x28f6) virtual-serialized, typically CLandCombatant; terrain from [+0x38]+0x18.

CLandCombatant writer `0x134d5f0` writes unit handles (elem+0x18 via `0x22857c0`) for `front` (data +0xe8, size +0xf4), `reserves` (+0x100 / +0x10c) and `retreat` (+0x118 / +0x124), all omitted when size≤0. This is the official attacker/defender unit-id membership path.

No CArmy current-combat pointer / IsInCombat getter is bound. GS+0x268 remains empty. Do not write `in_combat=false`.

## Command +8 / supply

No `.text` stores of the form `mov dword [reg+8], OrderType-or-command-token`. Objects using `0x22858a0` also keep handle type at +8, so the commandlist +8 dword cannot be mapped onto schema `OrderType` without a live command object. Still not `idle`.

No named `in_supply` / `isolated` token on CArmy. `out_of_supply_days` remains t182. Ratio still 72.0, not 0..1.

## Not promoted

`in_combat`, `order`, `supply.ratio` / `in_supply` / `isolated`, `formation`, `world.armies`, `world.army_groups`, `world.combats`, `leaders.assigned_to` stay unverified. `complete_input` stays false. Do not promote 77, `[1835]`, demanded / deficit / affected_unit_ids. `produced` is still not `min(need, current stockpile)`. Building damaged/overlay levels remain restricted; 1552CF0 remains a string formatter.

## Official inventory

D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md was **not** written. Still 116 fields, 14 tables, 3 columns; **43 verified / 73 unverified**. SHA256 `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254` (unchanged from t181).

## Artifacts

- research/t184_checkpoint.md
- research/t184_session_recheck.json
- research/t184_formation_writers.json
- research/t184_combat_writers.json
- research/t184_command_plus8.json
- research/t184_supply_named_tokens.json
- research/t184_live_theatre.json
- research/t184_inventory_sha256.json
- clips: `_t184_clip_theatre_writer_0xf81510.txt`, `_t184_clip_ordersgroup_writer_0xc4d030.txt`, `_t184_clip_armygroup_writer_0xc4cfa0.txt`, `_t184_clip_theatergroup_writer_0x16d9e10.txt`, `_t184_clip_base_id_writer_0x22858a0.txt`, `_t184_clip_unit_handle_writer_0x22857c0.txt`, `_t184_clip_landcombat_writer_0x147fe80.txt`, `_t184_clip_landcombatant_writer_0x134d5f0.txt`
- offsets key: `formation_combat_writers_t184` (`promoted: false`)
- tests: research/test_t184_input_formation_combat.py (6 tests). Suite 169 + 6 = 175. No new field emission.

## Next independent block

Bind any remaining CLandCombatant side fields needed for combat unit-id shape, and keep hunting a CArmy current-combat pointer / land IsInCombat without promoting false from empty GS_COMBATS. Commandlist +8 still needs a live command object or a constructor/vtype map that is actually a handle-type or token; do not invent OrderType. Continue `in_supply` / `isolated` / 0–1 supply only with a named getter. Formation / armies / army_groups ABI is bound; promotion still needs at least one non-empty orders_group or army group (user would have to create an army or assign units). Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

This empty peace scene still cannot finish `in_combat` / `order.type` / `leaders.assigned_to`, and cannot finish `formation` / `world.armies` / `world.army_groups` while all group arrays are empty. Minimal user conditions, only when those fields must be contrasted: issue one move order to one own division; or provide a live combat; or assign one of the 20 ETH generals to a division / army / army group; **or create one army (orders_group) and assign at least one own division**. The agent will not start a war, change speed/pause, give orders, assign leaders, or create armies. Other ABI work above can continue without that.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
