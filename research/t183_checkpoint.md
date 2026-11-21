# t183 checkpoint — is_assigned is CScientist; commandlist +8 bound; nothing promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, ETH index 44 1x, country 0x26c4b672530, gs 0x26c259d0ff0. This batch was read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No test war, no orders, no leader assignments issued.

## is_assigned / leaders.assigned_to

Token `is_assigned` 0x385b at `0x26940` is a **string-token registrar** (same family as `is_field_marshal` 0x26c40 and `is_leading_army_group` 0x26e80), not a field reader.

The only non-registrar consumer `0x14a8ec0` belongs to **CScientist** (vtable 0x29fb128, this function at +0x10). It writes the token from `byte [this+0x130]` only if nonzero; the next field is `is_scientist_injured` at +0x134. That is not `world.leaders.assigned_to`.

CArmyLeader writer `0xc7e8c0` has official `deployed` (token 0x41c7, byte at +0x1068, written iff nonzero) and `deploy_army_hq` (+0x1058). Schema `assigned_to` is `{kind: army|army_group|unit, id}`. A boolean is the wrong shape.

Live: CCharacter+0x68 is the country index; CArmyLeader* is at CCharacter+0xa8. 52 player characters, **20** CArmyLeader (handle ids 312–331, same space as t163). All 20 have `deployed=0`, no pointer to an own CArmy, and no handle match to unit `leader_id`. The five own divisions with `CArmy+0x564` in {70392..70396} (16 others −1) use a **different officer space**, already noted in the inventory as 非师军官编号; `SUnitOfficerData` at CArmy+0x568 copies that same id at +0x54. Do not invert unit.leader_id into assigned_to.

## commandlist element

Official element ABI from `0xc5c0a0` (offsets relative to CArmy+0x10):

    0xc5c43f  cmp dword ptr [rdi + 0x2bc], 0
    0xc5c448  mov edx, 0xcb  ; TOKEN commandlist
    0xc5c480  mov rdx, qword ptr [rsi]
    0xc5c483  mov edx, dword ptr [rdx + 8]
    0xc5c489  call 0x2546ce0          ; write the per-command token
    0xc5c48e  mov rdx, qword ptr [rsi]
    0xc5c494  call 0x2544f80          ; serialize the command object

Stride-8 pointers; type token at element+8. 21/21 commandlists still size 0, so +8 cannot be mapped onto schema `OrderType` this scene. Empty official lists still must not be written as `order.type=idle`.

## in_combat

`InCombat(` at 0x29f9547 is the navy assert `pAirBase->GetCarrierShip()->GetNavy()->InCombat() && "Scrambled airwing's carrier is not in combat."` — not a land-unit reader. `land_combat_id` remains a non-CArmy field (t182). GS+0x268 combats are still empty (data 0, size 0): structure candidate only.

## formation / supply

One ETH CTheatre at CCountry+0x168. Group arrays at CTheatre+0x80 / +0x98 / +0xc8 (orders / field_marshal / theater) all size 0. No CTheatre/CArmyGroup/CTheaterGroup pointer on the 21 own CArmy in +0x20..0x800. Empty groups cannot prove `formation.army_id` / `army_group_id`.

`0xf00797` is another object writer (railway_gun_name / repair_line) that also emits the same supply tokens; not a 0..1 getter. CA+0x610 remains 72.0 under /100000. No named `in_supply` / `isolated` CArmy getter bound.

## Not promoted

`in_combat`, `order`, `supply.ratio` / `in_supply` / `isolated`, `formation`, `leaders.assigned_to` stay unverified. `complete_input` stays false. Do not promote 77, `[1835]`, demanded / deficit / affected_unit_ids. `produced` is still not `min(need, current stockpile)`. Building damaged/overlay levels remain restricted; 1552CF0 remains a string formatter.

## Official inventory

D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md was **not** written. Still 116 fields, 14 tables, 3 columns; **43 verified / 73 unverified**. SHA256 `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254` (unchanged from t181).

## Artifacts

- research/t183_checkpoint.md
- research/t183_session_recheck.json
- research/t183_assigned_to_contract.json
- research/t183_commandlist_element.json
- research/t183_combat_reader.json
- research/t183_formation_empty.json
- research/t183_supply_still_not_ratio.json
- research/t183_live_assigned_to.json, research/t183_live_formation_leaders.json, research/t183_live_officerdata.json
- research/t183_inventory_sha256.json
- clips: `_t183_clip_is_assigned_0x26940.txt`, `_t183_clip_is_assigned_0x14a8ec0.txt`, `_t183_clip_is_field_marshal_0x26c40.txt`, `_t183_clip_is_leading_army_group_0x26e80.txt`, `_t183_clip_commandlist_loop_0xc5c43f.txt`, `_t183_clip_leader_writer_0xc7e8c0.txt`, `_t183_clip_supply_ratio_0xf00797.txt`
- offsets key: `assigned_combat_command_t183` (`promoted: false`)
- tests: research/test_t183_input_assigned_combat_command.py (6 tests). Suite 163 + 6 = 169. No new field emission.

## Next independent block

Bind official CTheatre / group / army membership and id writers (CTheatre `0xf81510` and group object serializers) as ABI only; do not promote empty groups. Keep hunting a land-unit current-combat pointer or CLandCombat membership reader without promoting false from empty GS_COMBATS. A static map of commandlist +8 tokens onto `OrderType` can continue from command-class vtables even without a live command, but promotion still needs a present command or an official idle flag. Continue `in_supply` / `isolated` / 0–1 supply only with a named getter. Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

This empty peace scene still cannot finish `in_combat` / `order.type`. `leaders.assigned_to` additionally cannot be finished while all 20 generals are unassigned and no official `{kind,id}` slot is bound. Minimal user conditions, only when those fields must be contrasted: issue one move order to one own division, or provide a live combat, **or assign one of the 20 ETH generals to a division / army / army group**. The agent will not start a war, change speed/pause, give orders, or assign leaders. Other ABI work above can continue without that.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
