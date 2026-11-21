# t192 checkpoint — create one ETH army and appoint one general; promote formation/armies/assigned_to

Authorization: [pt180u] still valid. Continue from delivered t191; write/Post a minimal create-army and/or appoint-leader command to auto-validate remaining input fields and learn Post/output. Pause/1x only; no save I/O; no commit/push; no combat/supply/building-damage/crisis work. Fog rule unchanged. Do not cancel the t191 path on unit 1829 unless it blocks the next step (it did not).

## Session

Confirmed immediately before the first t192 write: pid 26976, HOI4 Windows 1.19.5.0.7c6c, ETH 44, 1936-01-01 12:00, hour tick 60759371, official pause `CInGameIdler+0x6c1=1`, speed index 0 (1x notch, not started). Same `CGameState 0x26c259d0ff0` / `CCountry 0x26c4b672530`. Unit 1829 still had `CArmy+0x200 = [8036]` and was still physically in 5010. After both Posts the clock, pause bit, and speed notch were unchanged; the process stayed alive (exit 259). Post gate was re-opened only for this block and closed again (`allow_post()=false`, `research/safe_land_tool_gate.OPEN` removed).

## Command choice

Both targets could be done safely and still minimally in one paused checkpoint, so they were done in order:

1. Create one `COrdersGroup` (army) first — the ABI was already bound (writer `0xc4d030`, factory/IsValid/Execute rebound on 1.19.5).
2. Appoint one unassigned ETH general to that new army — `CSetArmyLeaderCommand` requires an existing orders_group handle at `+0x30`.

`CArmyGroupCommand` was not used (not the first-choice “create army” command). No field-marshal / army-group object was created. Unit 1829 was left untouched as the t191 path contrast. The member unit was **1838** in ETH-controlled rear province **7980** (alone, not ITA-adjacent). Theatre handle type 67 / id 43 was unchanged. All 20 generals still had `deployed=0` before the appoint.

## Post machinery (reused)

No new Post pipeline. Same `move_order._remote` / `_game_malloc` / `FN_CMD_QUEUE_POST=0x22C4250` / ucrt malloc / one-shot gate as t191. 1.19.5 command binds (read-only before Post):

- `COrderGroupCommand`: factory idx 2983, factory `0x18d0140` (size `0x60`), VT `0x2A84560`, IsValid `0x18DF050`, Execute `0x18D6560` (pdata is truncated; body continues at `0x18d65d4` and calls create `0xc417a0`).
  Packing: flag `+0x28=0`; ucrt vector of one unit handle `{type=0x33, id=1838}` at `+0x30` (data/cap/size); theatre handle `{67, 43}` at `+0x48`; theater_group `+0x50` and army_group `+0x58` left zero.
- `CSetArmyLeaderCommand`: factory idx 3369, factory `0x18d0c10` (size `0x40`), VT `0x2A85E20`, IsValid `0x18E0540`, Execute `0x18DB330`.
  Packing: leader handle `{4713, 312}` at `+0x28`; orders_group handle `{53, 1}` at `+0x30`; `deploy_army_hq +0x38=0`. The old `army_subjects.set_army_leader_recipe` omitted the required `+0x30` group handle; packing followed IsValid/Execute, and the recipe was corrected (still `posting: DISABLED`).

Dry-run IsValid was 1 for the create command before the gate opened. The appoint IsValid was also 1 after the group existed. Each Post was issued once; no retry loop; speed was never raised.

## Commands and readback

1. Dry-run `COrderGroupCommand` → `isvalid=1`. One live Post, `post_rax=1`, `wait=0`, stub freed. Stayed paused.
   Immediate readback: theatre 43 `+0x80` gained one `.?AVCOrdersGroup@@` at `0x26d2b077020`, handle type **53**, id **1**, name **第1集团军**. Leader pointer `+0x88` was still null (create does not auto-assign a general). Own unit count stayed 21 (no HQ unit; `deploy_hq` was not involved here).
2. Dry-run `CSetArmyLeaderCommand` (leader 312 `ETH_haile_selassie` / 海尔·塞拉西, group `{53,1}`) → `isvalid=1`. One live Post, `post_rax=1`. Stayed paused.
   Final readback: `COrdersGroup+0x88` → `CArmyLeader` 312. `CArmyLeader+0x1048 = {53, 1}`. The other 19 generals still have `{0,0}` at `+0x1048`. **`deployed` at `+0x1068` is still 0 for all 20**, including 312. `deploy_army_hq +0x1058` stayed 0. No new division appeared.

Member ABI: `COrdersGroup+0x50` is a pointer array. The official writer `0xc4d030` loads each pointer, calls `vt+0x20`, then writes the unit handle at `+0x18` (token `0x28a3`). Live this-adjust from the member interface pointer back to `CArmy` is **`0xB8`**, recovering handle `{51, 1838}`. `CArmy+0xC0` on unit 1838 (and only 1838) is the new `COrdersGroup*`. A raw scan hit of the group pointer at unit 1837 `+0x750` is a false overlap: `CA_OBJECT_SIZE=0x690` and `0x750-0xC0=0x690`. Do not treat `+0x750` as a formation slot. Theatre 43’s 21-division array is still not `formation.army_id`.

Unit 1829 path remains `[8036]`. Unit 1838 is still in 7980 with an empty path.

## Promoted

Live reader confirmation (`input_loaded_fields.own_armies`, `unit_formation_army_id`, `own_leaders`):

- `world.armies.army_id` — `CTheatre+0x80` `COrdersGroup` handle id; type 53. Official writer `0xc4d030` via `0x22858a0`.
- `world.armies.name` — `COrdersGroup+0x160`; live default name `第1集团军`.
- `world.armies.leader_id` — `COrdersGroup+0x88` → leader handle id; official token `0x28b7`, omitted when the pointer is null (observed null after create, 312 after appoint).
- `world.armies.unit_ids` — members at `+0x50`, official `vt+0x20` then handle at `+0x18`; live this-adjust `0xB8` cross-checked against `CArmy+0xC0`. Live value `[1838]`.
- `world.own_units.formation.army_id` — `CArmy+0xC0` `COrdersGroup*` id; only 1838 is 1, the other 20 own divisions are unaffiliated. Not the theatre unit list.
- `world.leaders.assigned_to` — live handle at `CArmyLeader+0x1048` as `{kind,id}`. Type 53 maps to `kind=army`. Leader 312 is `{kind: army, id: 1}`; 19 others omit the key. This is **not** the `deployed` boolean at `+0x1068` (token `0x41c7`, still 0) and **not** `CArmy+0x564` officer ids. The official `CArmyLeader` writer `0xc7e8c0` does not emit `+0x1048`; the slot is the live assignment handle and is the inverse of official `COrdersGroup.leader`. Only the army kind has been observed.

Official inventory (D: 14 tables, 116 fields, 3 columns): **54 verified / 62 unverified**. SHA256 `0633ed5dd85b17bd13dfff0150edf721b32d9fc961a4aa916311799b5aaf39d5`. `complete_input` remains false. t191’s inventory test was frozen to its recorded SHA `e38f089d…` so it no longer pins live D. t183/t184 live asserts that those fields were still 未验证 were relaxed the same way; their recorded hashes are unchanged.

## Not promoted (honest)

- `world.own_units.formation.army_group_id` and all `world.army_groups.*` — no `CArmyGroup` was created; field-marshal / theater-group arrays stay empty.
- `world.armies.plan_id` — `COrdersGroup` `order_instance` at `+0x98/+0xa4` size 0. Empty is not a proven plan id.
- `assigned_to` kinds `army_group` and `unit` — not observed. Unknown handle types must not be guessed.
- `CArmyLeader.deployed` / `deploy_army_hq` — not `assigned_to`. A successful appoint left both at 0.
- t191 leftovers remain unverified: `order.type` (commandlist still empty), `target_province_ids`, `eta` (progress still 0 while paused).

## Post / output lessons (this block)

- Create-army and appoint-leader both execute while officially paused; do not unpause into the ITA–ETH war for these commands.
- Creating an orders_group does **not** auto-assign a leader (`+0x88` stayed 0 until `CSetArmyLeaderCommand`).
- The new army’s default localized name appeared immediately (`第1集团军`); handle type for `COrdersGroup` is **53**; `CArmyLeader` handle type is **4713**.
- Destination/unit vectors must still be ucrt malloc, not `VirtualAllocEx`.
- On `WAIT=0` the stub was freed safely; the t191 rule still holds: on timeout do not free the remote stub, and do not free live posted buffers.
- `set_army_leader_recipe` must include the orders_group handle at `+0x30`. Leave `deploy_army_hq=0` unless an HQ spawn is an explicit goal (this Post created no extra unit).
- Member pointers are an interface (`vt+0x20` this-adjust `0xB8`), not a raw `CArmy+0x1C` read at the member address (that incorrectly yields 0).
- Do not scan a full `0x800` window on a `0x690` `CArmy` and treat a neighbor’s `+0xC0` as this unit’s field.
- Reversibility exists as `CDeleteOrderGroupCommand` (RTTI VT `0x2A84620`) but was **not** used: the new army is the contrast sample and should be kept.
- Combat / supply / building-damage / crises were not touched.

## Stop state (saveable; no save I/O performed)

- pid 26976, ETH, 1936-01-01 12:00, hour tick 60759371, pause=1, speed index 0, gate closed.
- Unit 1829 path still `[8036]` (t191 contrast).
- One own army: id 1, name 第1集团军, leader 312, member 1838 at 7980.
- 20 ETH generals: only 312 assigned to army 1; all `deployed=0`.
- Do not commit/push unless asked.
