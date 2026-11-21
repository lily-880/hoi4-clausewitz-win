# t193 checkpoint — create one ETH army group, appoint its commander, draw a root plan; promote army_groups / plan_id / assigned_army_ids

Authorization: [pt180u] still valid. Continue from delivered t192; issue minimal write/Post commands to auto-validate remaining input fields and learn Post/output. Pause/1x only; no save I/O; no commit/push; no combat/supply/building-damage/crisis work. Fog rule unchanged. Do not cancel the t191 path on unit 1829 or delete the t192 第1集团军 contrast.

## Session

Confirmed immediately before the first t193 write: pid 26976, HOI4 Windows 1.19.5.0.7c6c, ETH 44, 1936-01-01 12:00, hour tick 60759371, official pause `CInGameIdler+0x6c1=1`, speed index 0. Same `CGameState 0x26c259d0ff0` / `CCountry 0x26c4b672530`. Unit 1829 still had `CArmy+0x200=[8036]`. Army 1 (`COrdersGroup` handle type 53 / id 1, name 第1集团军, member 1838, leader 312) was intact. After all three Posts the clock, pause bit, and speed notch were unchanged; the process stayed alive (exit 259). The Post gate was opened only around each live Post and closed again (`allow_post()=false`).

A preexisting `CTheaterGroup` handle `{68, 32}` was already in `CTheatre+0xC8` before any t193 Post. It was not created here, is not a `CArmyGroup`, and was not promoted.

## Commands

Both target families could be done safely and still minimally while paused, so they were finished in one checkpoint.

### 1. Create army group + appoint commander

`CArmyGroupCommand` (factory idx 5433, factory `0x18cf780`, size `0x80`, VT `0x2A846E0`, IsValid `0x18DDFE0`, Execute `0x18D2640`, create `0xf70110`).

Packing: theatre handle `{67, 43}` at `+0x28`; ucrt vector of one `COrdersGroup` handle `{53, 1}` at `+0x30`; the stride-24 array at `+0x48` and the optional handle at `+0x60` left empty. Dry-run `isvalid=1`. One Post, `post_rax=1`, `wait=0`, stub freed. Stayed paused.

Immediate readback: `CTheatre+0x98` gained one `.?AVCArmyGroup@@` at `0x26d3e6baa50`, handle type **53** (same as `COrdersGroup`), id **2**, name **第1集团军群**, `+0x39=1`. Official child array `+0x230` held army 1. Leader `+0x88` was still null (create does not auto-assign a marshal). Unit count stayed 21; 1829 path unchanged.

Then `CSetArmyLeaderCommand` with a different general: leader `{4713, 313}` (ETH_haile_selassie_gugsa / 海尔·塞拉西·古格萨), group `{53, 2}`, `deploy_hq=0`. IsValid=1, one Post, `post_rax=1`. `CArmyGroup+0x88` → 313. `CArmyLeader+0x1048={53, 2}` resolves to **CArmyGroup**, not army 1. Leader 312 remains `{53, 1}` / army. All 20 `deployed` bits stayed 0.

Live backlink: `COrdersGroup+0x1B8` on army 1 is the `CArmyGroup*`. No `CArmy` slot holds `{53, 2}` (scanned the official `0x690` object size). `formation.army_group_id` is army → `CArmy+0xC0` → `COrdersGroup+0x1B8`, cross-checked against `CArmyGroup+0x230`. Do not treat the theatre 21-division list as either formation id.

Because handle type 53 is shared, `leaders.assigned_to` must resolve RTTI: `{53,1}` → `{kind: army, id: 1}`, `{53,2}` → `{kind: army_group, id: 2}`. The already-promoted `assigned_to` inventory line was clarified; the field was not re-promoted.

### 2. Minimal player plan

`COrderNewFrontCommand` is **not** the first-plan command. Its IsValid requires a nonempty official path at `+0x5c` and a nonzero attach id at `+0x68`; `0xc402a0(group, attach_id)` walks existing `COrderInstance` arrays (`+0x98`, `+0xb0`, `+0xc8`) and then the parent at `+0x1B8`. With no instance yet, that call returns 0 and IsValid fails. It was not posted.

`COrderNewRootCommand` is the root-plan command (factory idx 4096, factory `0x18d0440`, size `0x70`, VT `0x2A856A0`, IsValid `0x18DF5E0`, Execute `0x18D9A30`). IsValid: handle gate `0xbbb250` on `+0x28`, and `+0x48/+0x4c` must not be the empty sentinel pair. Execute resolves the group, calls `0xc41720(group, edx=2)` to allocate a `COrderInstance`, copies `+0x48` to instance `+0x258`, and hangs the object on the group via `0xc40500`.

Packing: group `{53, 1}` at `+0x28`; ETH-controlled, ITA-adjacent land-neighbor pair **13237 / 13238** at `+0x48/+0x4c`. Dry-run `isvalid=1`. One Post, `post_rax=1`. Stayed paused. `COrderExecuteCommand` was **not** issued.

Readback: army 1 `+0x98` has one `.?AVCOrderInstance@@`, `instance_id +0x244 = 1`, `type +0x30 = 2`. Official path array `+0x70` (token `0x174`) is **empty**; the two provinces were stored at `+0x258` (`0x33b6000033b5`). `states +0xe0` empty. `can_execute +0x248` (token `0x30b2`, written iff nonzero) is 0. The six theatre `CFront` objects (ids 420–425, type 66) were left untouched and are still not player plans.

Factory leftover lesson: unused NewRoot fields were not explicitly zeroed; packed `+0x60` was 100000 and `+0x6c` was 1. The Post still succeeded. Future packs should zero the rest of the `0x70` object after the factory returns.

## Promoted

Live readers `own_army_groups`, `unit_formation_army_group_id`, `own_plans`, and `own_armies` (now also `plan_id`):

- `world.army_groups.army_group_id` / `name` / `leader_id` / `army_ids`
- `world.own_units.formation.army_group_id` (only unit 1838 is 2)
- `world.plans.plan_id` (COrderInstance+0x244 = 1, not a CFront)
- `world.plans.assigned_army_ids` ([1], from the hanging COrdersGroup)
- `world.armies.plan_id` (army 1 → instance 1)

Official inventory (D: 14 tables, 116 fields, 3 columns): **62 verified / 54 unverified**. SHA256 `e4b7db714556524ac084c55367414e5f3ac55feb4b904bbb2fdec8ea866b75f0`. `complete_input` remains false. t192’s inventory test was frozen to its recorded SHA `0633ed5d…`. t188 no longer requires live `world.plans.plan_id` to stay 未验证.

## Not promoted (honest)

- `world.plans.type` — live value is 2 (what `COrderNewRootCommand` always creates). GetOrderType is still only named for **1=ORDER_MOVE** and **3=ORDER_INVASION**. Schema names `frontline` / `offensive_line` / `garrison` / `area_defense` are not numerically bound. Type 2 is a recorded candidate only.
- `world.plans.vertex_province_ids` — official path `+0x70` stayed empty. Do not treat `+0x258` as the path token.
- `world.plans.assigned_unit_ids` — no unit vector was packed; member arrays used by `scheduled_member` stayed empty.
- `world.plans.executing` — `can_execute` at `+0x248` is 0 and is **not** this field. The plan was not executed.
- `world.plans.axis_province_ids`, `world.plans.status` — not observed on this object.
- `assigned_to` kind `unit` — still unseen.

t191 leftovers (`order.type` / `target` / `eta`) remain unverified.

## Post / output lessons

- Army-group create and marshal appoint both run while officially paused; so does NewRoot. Do not unpause into the ITA–ETH war for these.
- Creating a `CArmyGroup` does not auto-assign a leader. `CSetArmyLeaderCommand` accepts the army-group handle at `+0x30` (same command as army appointment).
- `COrdersGroup` and `CArmyGroup` share handle type 53; distinguish by RTTI, `+0x39`, and theatre array (`+0x80` vs `+0x98`).
- Default localized names appear immediately (第1集团军群).
- Buffers still go through ucrt malloc. `WAIT=0` stubs were freed; on timeout still do not free the remote stub.
- First player plan = `COrderNewRootCommand`, not `COrderNewFrontCommand` and not a border `CFront`.
- NewRoot creates type 2 and can succeed without a filled official path array.
- Explicitly zero unused factory bytes.
- Reversibility (`CDeleteOrderGroupCommand`, order-delete) was not used: the army group, appointment, and plan are contrast samples and should be kept.

## Stop state (saveable; no save I/O performed)

- pid 26976, ETH, 1936-01-01 12:00, hour tick 60759371, pause=1, speed index 0, gate closed.
- Unit 1829 path still `[8036]`.
- Army 1: 第1集团军, leader 312, member 1838, plan_id 1, parent army group 2.
- Army group 2: 第1集团军群, leader 313, army_ids [1].
- Plan 1: type 2 (unnamed), official path empty, not executing, assigned to army 1.
- 20 ETH generals: 312 → army 1, 313 → army_group 2, all `deployed=0`.
- Do not commit/push unless asked.
