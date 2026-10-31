# Findings — Windows Phase 1

**Date:** 2026-10-30 ~ 2026-10-31 (Asia/Shanghai)  
**Machine:** LAPTOP-6FQIF6OJ (Windows 11 家庭版 25H2, build 26200)  
**Game:** `D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe`  
**Launcher version string:** 1.19.4.1 (pin: 1.19.4.x Operation Postern)  
**Exe size:** 56530040 bytes  
**Preferred PE ImageBase:** `0x140000000`  
**SizeOfImage:** `0x38a3000` (~56 MB)  
**Sections:** `.text` `.rdata` `.data` `.pdata` `.rsrc` `.reloc`

## Proven on PC

- `python clausewitz_win.py peinfo` — OK
- `python clausewitz_win.py doctor` — OK (RESULT: ready Phase 1); game was not running at first check
- Install path: `Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win`
- GitHub: https://github.com/lily-880/hoi4-clausewitz-win

## Not proven yet

- Live `status` string scans (need running `hoi4.exe`)
- Any `G_*` / `FN_*` Windows RVAs
- Command queue posting

## Safety

Read-only default. Vision Channel / Auto Kessel untouched.


## Phase 2 — static RTTI + attach (2026-10-31 Asia/Shanghai)

### Works
- PE parse, doctor, attach when `hoi4.exe` running (MZ + region walk + string scan in image)
- MSVC RTTI recovery for `CGameState` / `CInGameIdler` / `CCommand` / `CLandCombat` / `CArmy` / `CCountry`
- Primary `CGameState` vtable RVA **`0x279f0f0`** (safely static-proven)
- `live-gs` path: scan image `.data` for global slot → heap object with that vptr; heuristic countries/@player

### Stubbed / refused
- `G_GAMESTATE` global RVA — only after live-gs verifies (not committed as verified yet)
- **Command-queue Post** — no `CCommandQueue` RTTI; SDL GL strings are red herrings; **read-only**
- Full MCP tool parity with Linux Clausewitz-MCP

### Safety
Command posting remains disabled until `FN_CMD_QUEUE_POST` is independently verified.

## Phase 2e — Post graph + dead ends (2026-10-31 Asia/Shanghai)

### Works
- Static decode: CInGameIdler vt+0x90 = RVA 0xe34e90 loads [this+0x530] then jmp [rax+0x90] (Linux-analog queue/Post shape)
- Tools: scripts/phase2e_post_graph.py, scripts/phase2e_live_scan.py
- Status: date_aux_0x47c exposed as hypothesis; CArmy/CUnit RTTI vtables recorded
- CO_STATES @ country+0x460 matches Linux

### Stubbed / refused
- FN_CMD_QUEUE_POST still null (no live idler; no typed Post)
- divisions_count stubbed (no live CArmy* arrays; CO_ARMIES@0x290 empty)
- full date Y-M-D not proven (year@+0x478 only)

### Safety
Command posting remains DISABLED.

## Phase 2ap (2026-10-31 Asia/Shanghai)

### Works
- Army/order command RTTI + type_id catalog (Move/Cancel/StrategicRedeploy/Orders/...)
- Formal `safe_enable_checklist.json`
- 1x midflight attempts (heap + pending poll); identified `CHourlyTickCommand` traffic

### Stubbed / refused
- Mid-flight `CMoveCommand` capture still open (destroyed inside SP tick)
- Posting **DISABLED**; no WriteProcessMemory enqueue

### Safety
pause/1x only; never 5x; FN_CMD_QUEUE_POST known `0x22c41e0` but writes gated.

## Phase 2aq (Strategic redeploy serialize)

- Mapped `CStrategicRedeploymentCommand` (size `0x50`, type `0x35b9`) embedding `CUnitStrategicMoveAction` at `+0x28`.
- Action RTTI confirmed; serialize layout live-verified (army handle, single province, clear, move_priority).
- Execute/serialize thunks shared with `CMoveCommand` — dispatch into embedded action.
- **Posting still DISABLED**; safe-enable not proven.

## Phase 2ar (Order* sizes + serialize)

- Documented sizes for 10 Order*/ArmyGroup/SetLeader commands via Clone alloc immediates.
- Field layouts for Assign/Execute/Unassign/Delete/NewFront/SetArmyLeader (token-backed).
- **Posting still DISABLED**.

## Phase 2as (handles / provinces)

- Live HAI: 17 `CArmy` handles type `0x33`, indices 1037..1053 sequential; country tag @`+0x1e0` = player 15.
- `CProvince+0xa4` province-id hypothesis (15 unique / 17 armies).
- `FN_HANDLE_RESOLVE` left unverified. **Posting DISABLED**.

## Phase 2at (ring embed / resolve)

- Confirmed `CDummyServer` sink embeds ring at `+0xa0` (`add rbx,0xa0`).
- `CLAUSEWITZ_ALLOW_POST` tooling gate stubbed (always False).
- Handle resolve still open; `0x6e4800` rejected; `0xc5a9e0` is GS thunk candidate.
- **Posting DISABLED**.

## Phase 2au (province resolve)

- `0xc5a9e0` → `0x1e07f0` is **province** resolve (GS+`0x2b0` / size `0x2bc`), not unit.
- `CArmy+0x28` province id; `CProvince+0xa4` proven 17/17 on HAI.
- Unit/army `FN_HANDLE_RESOLVE` still open. **Posting DISABLED**.

## Phase 2av (handle resolve)

- `FN_HANDLE_RESOLVE = 0x2284800` proven (Strategic Apply path + live hash sim 17/17).
- `calling/handle.py` RO helper added.
- Safe-enable still open (no Post proof / midflight Move). **Posting DISABLED**.

## Phase 2aw (helpers / ABI)

- Live roster: handle + province helpers 17/17.
- Post ABI documented; `allow_post()` still hard-denies. **Posting DISABLED**.


## Phase 2ax / 2ay / 2az (2026-10-31 Asia/Shanghai)

### Works
- Live SP pipeline: `FN_CMD_QUEUE_POST 0x22c41e0` → DummyServer sink `0x23f5cd0` (ring `+0xa0`) → drain `0x23f64e0` (pending `+0x58`) → SessionUpdate `0x22c6410` Execute site A `0x22c6c9d` (`cmd.vt+0x50`) + loop B `0x22c4710` (execlist `+0x40`).
- `G_SESSION` / `G_COMMAND_QUEUE` = `0x34FFBE8` live-matches `App+0x380` (Haiti SP, pid 2880).
- `calling/post_abi.py` documents ABI; `post_command()` hard-denies.
- Full-heap command VT census (paused): no live Move/Strategic/Cancel (expected); drain counter advances on ticks.
- Scripts: `phase2ax_drain_execute.py`, `phase2ay_pipeline.py`, `phase2az_midflight_poll.py`.

### Stubbed / refused
- Mid-flight `CMoveCommand` sample still open (lists empty at 50ms poll; SP frees inside tick).
- **Posting DISABLED** — checklist gaps `no_tooling_post` + `midflight_move_sample` remain.

### Safety
pause/1x only; never 5x; no WriteProcessMemory enqueue.


## Phase 2ba (2026-10-31 Asia/Shanghai)

### Works
- `calling/cmd_layout.py` — Move / Strategic / Cancel field maps (RO).
- `scripts/phase2ba_status_pipeline.py` — live session/server counters + army handle/province sample.
- Posting remains **DISABLED**.

## Phase 2bb–2bl (2026-10-31 Asia/Shanghai) — overnight continue

- **Post ABI tooling proof (2bc): WORKS** — `calling/post_abi.py` + `calling/cmd_layout.py`; `scripts/phase2bc_post_abi_proof.py` **18/18** live RO checks (G_SESSION, Dummy VT/sink/drain, Post prologue, Move/Strategic VT slots, handle+province 17/17 HAI, `allow_post` False, `post_command` raises). **NO Post / NO write.**
- Checklist gap `no_tooling_post` → **closed**.
- **Midflight CMoveCommand (2bb–2bk): STUBBED** — pause heap empty (2bd 8GB/2GB scans 0 Move/MoveAction). Drain rises on empty ring; DummyServer **seq stuck 15 / exec 13** across SendInput Space, UI click, PostMessage, `SetCursorPos`+`mouse_event` (DX11 gameplay input ignored by tooling). Game stayed **paused** (never 5x).
- **Equivalent live CCommand (2bl): WORKS (RO)** — sticky `CStartGameCommand` vt `0x2A5F448` at wrapper `sess+0xF8` → cmd ptr; VT slots IsValid/Execute/PostExec/Clone readable. Not a Move sample.
- Checklist gap `midflight_move_sample` → **stubbed** (needs real user right-click / hardware input).
- **Posting DISABLED**; `command_queue_tool_gate` still open.
- Scripts: `phase2bb_midflight_ring.py` … `phase2bk_mouse_event.py`, `phase2bl_sticky_equivalent.py`.
- Reports: `phase2bb`…`phase2bl` JSON under `reports/`.


## Phase 2bm (2026-10-31 Asia/Shanghai) — layout / alternate entry RO

### Works
- Expanded `calling/cmd_layout.py`: `BASE`, `POST_GATES`, `MOVE`(+serialize tokens), `STRATEGIC`, `CANCEL`, `STARTGAME`, `CHAT`, `ORDERS` (10), `ARMY_MOVE_SUBJECTS`, `PIPELINE`.
- `scripts/phase2bm_cmd_catalog_live.py` — live VT slot verify **16/16**: Move/Strategic/Cancel/StartGame/Chat; `CUnitMoveAction` Execute/IsValid/serialize; **10/10 Order* Execute** slots; Dummy sink/drain; `session+0x725==1`; sticky StartGame; army handles; `allow_post` False.
- Move early gates both **FALSE** (needs `+0x725` or `r8b`) — documented, not an enable.
- `scripts/phase2bm_midflight_ready.py` — RO watcher armed (no input injection); smoke polls empty while paused (expected).

### Stubbed
- `midflight_move_sample` still stubbed (no user right-click overnight).

### Blocks enabling Post (checklist)
1. Midflight `CMoveCommand` sample
2. Explicit `CLAUSEWITZ_ALLOW_POST=1` (hard-deny now)
3. No guess writes; never speed/HourlyTick Post
4. `command_queue_tool_gate` open

**Posting DISABLED.** pause/1x only; never 5x.


## Phase 2bn (2026-10-31 Asia/Shanghai) — Order serialize / army wiring / drain edges / Post-gate analysis

### Works
- `scripts/phase2bn_live_re.py` **12/12** RO: Order* **10/10** Execute + `vt+0xa0` serialize + `vt+0xa8` deserialize + clone sizes + typeid factory probes; Move/Cancel/Chat serialize RVAs; HAI army wiring **17+** handle+province; drain edges (`+0x6CC`/`+0x726`/`+0x725`/empty-ring drain); speed/HourlyTick banlist live.
- `calling/army_subjects.py` — RO recipes for Move/Strategic subjects from `CArmy+0x18` / `+0x28`.
- `calling/cmd_layout.py` — factories, serialize/deserialize, `FACTORY_TABLE`, `DRAIN_EDGES`, `NEVER_POST`.
- Safer Post-gate analysis: `session+0x725==1` necessary **not** sufficient; serialize/recreate + `ALLOW_POST` + midflight still block.
- Midflight watcher re-armed background RO (`phase2bm_midflight_ready.py`, no input).
- 2bc still **18/18**; `allow_post` False.

### Stubbed
- `midflight_move_sample` unchanged.

### Posting
**DISABLED.** Never 5x. No guess writes.


## Phase 2bo (overnight RO continue, no midflight Move)

- Factory table deepened: lookup `0x22d8d20` (`tid>=0x2710 → idx=tid-0x2328`), table `0x35011e0`, max `0x2AF7`, live non-null **456**. Catalog factory→fn **36/36** (Move/Strategic/Cancel/StartGame/Chat + Orders×10 + NEVER_POST×6 + REMAINING×15).
- `ISVALID_PATHS`: wrap `0x22d8ea0`; Move thunk `0x14002f0`→action `0x12c2ca0`; Strategic `0x1402260`; Cancel `0x13fed40`; OEC `0x18def40`; Pause `0x188d90` **TRUE** (NEVER_POST).
- `army_subjects`: Strategic redeploy + Cancel (one/all HAI) recipes; live HAI armies **22**.
- `CPauseGame` type_id `0x29ec` factory `0xe53990` size `0x50` added to NEVER_POST with Inc/Dec/Set/Hourly/Ping type_ids.
- Remaining army/order stubs (15): MassMove/MassCancel/ToggleStrategicDeploy/OrderSetPath/DeleteOrderGroup/… — factory+vt+IsValid kind live; serialize/clone **stubbed**.
- Tool gate: safer analysis only; **CLOSED_NOT_OPENED**. `allow_post` False. Midflight Move still stubbed; watcher armed; no input injection.
- Posting DISABLED. Speed rule: pause/1x only.


## Phase 2bp (overnight RO — serialize/clone full proof + Dummy RT wiring)

### Works
- `GetTypeId` imm proof **36/36**; factory→fn **36/36**; shared bin ser/des `vt+8/10/18/20` **36/36**.
- Move / Strategic / Cancel: serialize + deserialize + clone + GetTypeId **full proof** (token thunks Move≡Strategic `0x1404590`/`0x1403570`).
- `REMAINING_ARMY_ORDERS` **15/15**: size + serialize + deserialize + clone + gettypeid + factory + IsValid live-matched.
- `DUMMY_ROUNDTRIP` documented in `cmd_layout`: sink `0x23F5CD0` → `serialize_with_typeid 0x2545780` → shared `vt+8` → recreate `0x22D8AD0` → factory_lookup → `vt+18` des → ring@+0xa0. **Wiring closed RO.**
- STARTGAME factory/serdes/clone filled (`0x16DD5A0`).
- Tool-gate **analysis only** — `CLOSED_NOT_OPENED`. `allow_post` False. Midflight watcher pid **29656** still armed; no input.
- Tick=1 (paused), session+0x725=1. Posting DISABLED. Never 5x.

### Stubbed
- `midflight_CMoveCommand` sample (DX11).
- Live-buffer serialize→recreate Dummy ring round-trip (needs midflight sample or Post — blocked).
- `command_queue_tool_gate` enable.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.


## Phase 2bq (overnight RO — live-buffer Dummy RT structural + remaining subtypes)

### Works
- **Live-buffer Dummy RT (structural, no Post):** sticky CStartGameCommand at sess+0xF8 live; GetTypeId/factory/size 0x28 match; shared bin ser/des token 0x1F3 packs/unpacks +0xc/+0x18/+0x1a/+0x1c/+0x20 (proven inverse); StartGame token-ser is NOP; recreate calls factory_lookup; ring empty (safe observe). Status STRUCTURAL_LIVE_OK.
- Extra land subtypes deepened **6/6**: MoveArmiesInTheater / MoveArmyGroupInTheater / CancelRunningAway / RailwayGunManualOrder / SetQuickDeployPreference / SetCountryGarrisonPriority (mem GetTypeId).
- Extra naval/air catalogued **6/6** RO (NavalMove/MoveShips/MissionMove/MissionMassMove/DeployAirWing/NavyCancelActivity); all share bin ser/des.
- NEVER_POST clone sizes filled; STARTGAME size=0x28.
- Tool-gate predicates deepened; **CLOSED_NOT_OPENED**. allow_post False. Watcher **29656** armed; tick=1; no input.

### Stubbed
- In-process serialize->recreate->ring embed (needs Post or midflight buffer).
- midflight_CMoveCommand sample (DX11).
- command_queue_tool_gate enable.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.


## Phase 2br (overnight RO — layouts / IsValid / Execute / drain+session / hygiene)

### Works
- `EXTRA_ARMY_COMMANDS` **8/8**: field maps + `isvalid_kind=FN` + live vt+0x48/0x50 kinds; all documented in `ISVALID_PATHS`.
- `ORDERS` **10/10**: `isvalid` RVAs + kinds FN; `ISVALID_PATHS` notes for each.
- `REMAINING_ARMY_ORDERS` **15/15** IsValid/Execute kinds reconfirmed FN.
- `SESSION_EDGES` + deepened `DRAIN_EDGES` + `EXECUTE_EDGES`: Post prologue 725/3c/6cc/726; SessionUpdate set/clear 6cc, inc 6c8, write sticky F8; Dummy drain ring lock/idx/pending + clone-via-vt+0x68.
- Sticky StartGame still **live** via `sess+0xF8` wrapper → `wrapper+0` cmd (vt `0x2a5f448`, tid `0x359e`); durable while paused.
- `ISVALID_PATHS` expanded **24** entries (was core Move/Strategic/Cancel/OEC/Pause).
- Tool-gate **CLOSED_NOT_OPENED**. `allow_post` False. Watcher **29656** armed; tick=1; no input.
- Checklist hygiene: `remaining_army_orders` → closed (serdes 2bp + kinds 2br).

### Stubbed
- In-process serialize→recreate→ring embed (needs Post/midflight).
- midflight_CMoveCommand sample (DX11).
- command_queue_tool_gate enable.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.


## Phase 2bs (overnight RO — remaining subtypes + REMAINING fields + tool-gate analysis)

### Works
- `EXTRA_ARMY_COMMANDS` **18/18** (was 8): promoted naval/air MissionMove/MissionMassMove/DeployAirWing/NavyCancelActivity + fleet SetNavalDeploymentTarget/CreateFleet/SetFleetHomeBase/NavalMissionSetTarget + land SetArmyTemplate/SetCountryReinforcementPriority. All factory-matched, shared bin, IsValid/Execute FN, fields + `ISVALID_PATHS`.
- `REMAINING_ARMY_ORDERS` **15/15**: fields + isvalid RVAs/kinds + `ISVALID_PATHS` notes.
- `TOOL_GATE_PREDICATES` documented in `cmd_layout` — safer analysis only; **CLOSED_NOT_OPENED**; no predicate flipped to allow enable.
- `ISVALID_PATHS` **49**. Sticky StartGame still live. Watcher **29656** armed; tick=1; `allow_post` False.
- Checklist hygiene: tool-gate analysis note; EXTRA naval/air gap closed.

### Stubbed
- In-process serialize→recreate→ring embed (needs Post/midflight).
- midflight_CMoveCommand sample (DX11).
- command_queue_tool_gate enable.
- Broader naval/production Command RTTI (~50+) left uncatalogued (out of army-move scope).

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2bt (overnight RO — land army attack/retreat/move/strategic redeploy)

### Works
- **LAND_ARMY_FOCUS** for user army agent: priority move → strategic_redeploy → attack_support → retreat_fallback. Posting DISABLED. Naval/production left out of scope.
- **CSupportAttackCommand** layout complete: tid `0x314c` size `0x38` factory `0x13fb5e0`; fields handle@+0x28 / province@+0x30; ser tokens `0x28a3`/`0x286d`; IsValid/Execute FN; gates 60/80 FALSE. `army_subjects.support_attack_recipe`.
- **CUnitStrategicMoveAction** ser tokens proven: `0x289D`/`0x2840`/`0x29F1`/`0x37BC` at +0x10/+0x18/+0x1C/+0x20; live IsValid `0x12c2c20` / Execute `0x12c3190` (FN).
- Retreat group deepened: NewFallback / ReplaceFallback / SetSelectedArmyGroupFallback / CancelRunningAway / WithdrawArmyHq — recipes + `ISVALID_PATHS` (ReplaceFallback + ArmyGroupFallback new).
- Land focus live verify **10/10**. Core MOVE/STRATEGIC/CANCEL still FN. HAI sample recipes ×3 (move/strategic/support_attack/cancel/fallback).
- `ISVALID_PATHS` **52** (was 49). Tool-gate **CLOSED_NOT_OPENED**. `allow_post` False. Watcher **29656** armed; tick=1; no input.

### Stubbed
- In-process serialize→recreate→ring embed (needs Post/midflight).
- midflight_CMoveCommand sample (DX11).
- command_queue_tool_gate enable.
- Broader naval/production Commands remain out of scope.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2bu (overnight RO — land cancel/abort + frontline/plan + theater)

### Works
- **LAND_ARMY_FOCUS** expanded to **25/25** live: added cancel_abort / frontline / theater groups alongside move/strategic/attack/retreat.
- **Cancel/abort:** `CMassCancelMovementCommand` Execute FN proof (iterate count@+0x34 over vec@+0x28) + `mass_cancel_movement_recipe`; CancelMovement / CancelRunningAway wired in group.
- **Frontline/plan:** NewFront / InsertFront / SetPath / Reshape / Connect / Reconnect + new **COrderSetCollapseCommand** (0x3a2f size 0x38) + **COrderAddNewCompletePlanCommand** (0x365e size 0x80) + OrderExecute; Capstone subject offs; recipes for new_front / set_path / set_collapse / order_execute.
- **Theater (land):** AssignToTheaterGroup / Disband / ReorderTheaters / SetTheaterGroupName / SetTheaterGroupPriority catalogued + assign_theater recipe; MoveArmies/GroupInTheater remain in group.
- **LAND_EXE_PROOFS** **11/11** Execute+IsValid FN (SupportAttack, MassCancel, Cancel, NewFront, SetPath, SetCollapse, AddNewCompletePlan, Move, Strategic, OrderExecute, AssignTheater).
- `ISVALID_PATHS` **59**. HAI×3 full verb recipes. Tool-gate **CLOSED_NOT_OPENED**. `allow_post` False. Watcher **29656**; tick=1; no input. Naval/production out of scope.

### Stubbed
- In-process serialize→recreate→ring embed (needs Post/midflight).
- midflight_CMoveCommand sample (DX11).
- command_queue_tool_gate enable.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2bv (overnight RO — full land EXE proofs + order-group/offensive-line)

### Works
- **LAND_EXE_PROOFS** expanded **11 → 37/37**: every LAND_ARMY_FOCUS command + cores + order-group execution helpers; live vt+0x48/0x50 FN match.
- **LAND_ARMY_FOCUS** **37/37**: new **order_group_group** (12) for encirclement/offensive-line agent — `CSetOrderGroupExecutionTypeCommand` (tid 0x36a8), Cohesion/Motorization/Name, CollapseConveyor, OrderGroup/NewRoot/Assign/Unassign/Delete, AssignTo/RemoveFromArmyGroup.
- Capstone field maps on remaining retreat/move/theater edges previously missing from EXE proofs.
- Recipes: `set_order_group_execution_type_recipe`, cohesion, `assign_to_army_group_recipe`, `order_assign_recipe`, `collapse_conveyor_recipe`.
- `ISVALID_PATHS` **64**. HAI×3 recipes include exec_type/cohesion/army-group. Tool-gate **CLOSED_NOT_OPENED**. `allow_post` False. Watcher **29656**; tick=1; no input.

### Stubbed
- In-process serialize→recreate→ring embed (needs Post/midflight).
- midflight_CMoveCommand sample (DX11).
- command_queue_tool_gate enable.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2bw (overnight RO — remaining land EXE/IsValid + Icon/delete/merge)

### Works
- **LAND_EXE_PROOFS** **54/54** (was 37): filled OrderDelete/Unassign/Name proofs + IconAndColor / LeaderProximity / OrdersInstanceNames + AutoMerge / DeleteOrderGroup / OrderDeleteAll / ArmyGroup / DeployArmyHq / SetArmyLeader / SetArmyTemplate / RailwayGunManual / Garrison+Reinforcement priority / QuickDeploy.
- **LAND_ARMY_FOCUS** **54/54**: cores Move/Strategic/Cancel promoted into `commands`; order_group_group **20**; retreat6 / move6 / strategic2 / attack2 / theater9.
- **ISVALID_PATHS** **67**. Recipes: delete_order_group / order_delete(_all) / auto_merge / icon / set_army_leader / set_army_template / railway_gun / deploy_hq. HAI×3.
- Live: allow_post False; tick=1; watcher **29656**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed
- midflight_CMoveCommand; in-process ring embed; command_queue_tool_gate enable; ALLOW_POST.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2bx (overnight RO — frontline/order/conveyor RTTI + Capstone thin + recipes)

### Works
- **LAND_EXE_PROOFS / LAND_ARMY_FOCUS** **86/86** (was 54): +32 live RTTI→COL→vt land cmds (Order edit/merge/split/block/invasion/paradrop/training, OrdersLink, ArmyLeaderPreferredTactic, ArmyFakeTemplate, full Conveyor family, Garrison templates, RailwayGunSetName, DeploymentLineName). All IsValid/Execute FN + factory-matched.
- Capstone **thin deepen 19/19** (MassMove, theater moves, ToggleStrategic, front Connect/Insert/Reshape/Reconnect/CompletePlan, NewRoot, ReorderTheaters, garrison/reinforce priority, QuickDeploy, fallback/withdraw/collapse).
- **ISVALID_PATHS** **99**. Groups: order_group **41**, frontline **15**, theater **12**, move7, attack3.
- Recipes: mass_move / toggle_strategic / edit_root / merge_roots / block_sections / invasion_source / create+deploy_conveyor / orders_link / leader_tactic / insert+reshape+connect front / complete_plan / garrison_template. HAI×3.
- Live: allow_post False; tick=1; watcher **29656**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed
- midflight_CMoveCommand; in-process ring embed; command_queue_tool_gate enable; ALLOW_POST.
- Remaining RTTI landish names (navy/air/division-template/production) intentionally out of land Post scope.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2by (overnight RO — land leftovers + Capstone thin + recipe completeness)

### Works
- **LAND_EXE_PROOFS / LAND_ARMY_FOCUS** **93/93** (was 86): +7 land RTTI cmds — `CSetRepairOrderCommand`, `CUpgradeDivisionOfficerCommand`, `CSetDivisionNameCommand`, `CSetObsoleteDivisionTemplateCommand`, `CBuildRailwayCommand`, `CLearnTraitCommand`, `CUpdateLeaderSeenTraitsCountCommand`. All IsValid/Execute FN.
- Capstone **thin deepen 37/37** on conveyor/front/order-group/theater/core edges; field maps filled for recipe-gap cmds.
- **ISVALID_PATHS** **106**. Groups: order_group **44**, move **11**, frontline15, theater12.
- Recipes: motorization/name/proximity, unassign, paradrop, training, remove_army_group, disband/reorder theaters, conveyor set/remove, learn_trait, repair_order, division_name, upgrade_officer, build_railway. HAI×3.
- Live: allow_post False; tick=1; watcher **29656**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST.
- Navy theater cmds + pinned strategic region (no vt) + division-template create/update/remove/symbol (tid unresolved / out of land Post scope).

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2bz (overnight RO — land merge/transport/area-defense/pinned-strategic)

### Works
- **LAND_EXE_PROOFS / LAND_ARMY_FOCUS** **115/115** (was 93): +22 land-army RTTI cmds with live IsValid/Execute FN + factory-matched type_ids (C7 02 imm_rdx GetTypeId).
  - Move: MergeArmies, DeleteUnit, TransportUnit, SetPendingReassignTarget
  - Strategic: Toggle/ReorderPinnedStrategicRegion (previously no_vt; now vt+factory)
  - Theater: SetTheatre
  - Attack/AI-land: AiOnFailedInvasion, Ai ForceConcentration store/discard, AiStoreTotalWantedNrDivisions
  - Front/garrison-adjacent: Create/Edit/Set AreaDefense*
  - Order-group/leader: SelectionGroup, QueueUnitAction, Promote/Create UnitLeader, SetUnitName, SetPreferredTactic, ClearRepairPins, UpdateLeaderSeenAdvisorRolesCount
- Capstone **thin deepen 88/88** field offs refreshed on sparse land layouts.
- **ISVALID_PATHS** **128**. Groups: order_group **52**, move **15**, frontline **18**, theater **13**, attack **7**, strategic **4**.
- Recipes for merge/delete/transport/theatre/unit-name/tactic/area-defense/pinned-strategic/selection/queue/promote/create-leader/reassign/clear-repair-pins. HAI×3.
- Live: allow_post False; tick=1; watcher **36128** re-armed RO 86400s; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand sample; ring embed; command_queue_tool_gate enable; ALLOW_POST.
- Division-template create/update/remove/symbol + navy/air/production/industrial/politics/GameSpeed intentionally out of land Post scope.
- SetGameSpeed never touched.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2ca (overnight RO — offensive-line/frontline Execute Capstone field naming)

### Works
- Capstone field naming deepen on **50** offensive-line / frontline / attack / order-group Execute paths (subject_lo/hi, arg0_or_type, arg1_or_count, shared offs).
- **LAND_EXE_PROOFS / LAND_ARMY_FOCUS** still **115/115**; **ISVALID_PATHS** **128** — no new RTTI (prior 2bz filled remaining land-army set).
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed
- midflight_CMoveCommand; ring embed; tool-gate enable; ALLOW_POST; navy/air/division-template/production.

### Posting
**DISABLED.** pause/1x only; never 5x.

## Phase 2cb (overnight RO — land-adjacent expeditionary/medal/ability + Capstone deepen)

### Works
- **LAND_EXE_PROOFS / LAND_ARMY_FOCUS** **121/121** (was 115): +6 land-adjacent RTTI with live IsValid/Execute FN + factory type_ids —
  `CRequestExpeditionariesCommand`, `CGiveMedalCommand`, `CTriggerAbilityCommand`, `CRetireCharacterCommand`, `CReinstateExileCommand`, `CAmendForeignManpowerActionCommand`.
- Capstone **thin deepen 57/57** on retreat/move/strategic/cancel/attack/frontline + sparse field maps.
- **ISVALID_PATHS** **134**. Groups: order_group **56**, move **17**, frontline18, theater13, attack7, strategic4.
- Recipes: expeditionaries/medal/ability/retire/exile/foreign-manpower + ai_wanted_divs / country_reinforce_prio / ai_force_conc. HAI×3.
- Remaining soft-miss Commands are chat/sync/science/navy/production/HourlyTick — out of land Post scope (no further in-scope RTTI).
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; tool-gate enable; ALLOW_POST.
- MergeNavies / PromoteToCountryLeader / MaxAllowedRepairFactories / GameSpeed / division-template / navy/air/production.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2cc (overnight RO — IsValid/Execute callgraph deepen)

### Works
- Capstone **callgraph deepen on all 121** land focus cmds (frontline/attack/retreat/move/strategic/theater/order-group/cancel): `execute_calls` / `isvalid_calls` RVAs + field merge.
- Catalogued **40** shared helpers with ≥3 hits (top: `0x2284800`×185, `0x254aa00`×74, `0x2607890`×65) for future Post-gate IsValid path analysis.
- **LAND 121/121**, **ISVALID_PATHS 134** unchanged counts; live FN proofs green.
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed
- midflight_CMoveCommand; ring embed; tool-gate enable; ALLOW_POST; navy/air/division-template/production/GameSpeed.

### Posting
**DISABLED.** pause/1x only; never 5x.

## Phase 2cd (overnight RO — shared helper mine + land Post readiness catalog)

### Works
- Mined all **40** shared land helpers (≥3 callgraph hits from 2cc) into `SHARED_LAND_HELPERS` + `LAND_POST_READINESS` (docs only; never enables Post).
- Helper classes: field_predicate **14**, dispatcher_or_composite **16**, inline_predicate **4**, wide_object_walk **3**, string_annotated **2**, flag_gate **1**.
- Post-readiness signals: **39** IsValid-gate-looking helpers; **22** Execute-body helpers.
- Named helpers Capstone-deepened: gamestate_instance_guard×5, ThreadIsMainThread, GetOrderInstance, deployment_train_gate, division_subunit_type_check; top hitters `0x2284800`×185 (field_predicate), `0x254aa00`×74 (flag_gate), `0x2607890`×65 (inline_predicate).
- Wired `shared_helpers` / `post_gate_candidates` / `execute_body_helpers` / `named` onto LAND focus + EXE proofs + ISVALID_PATHS.
- Recipe: `land_post_readiness_recipe()` RO snapshot.
- **LAND 121/121**, **ISVALID_PATHS 134** unchanged; live FN proofs green.
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST / CLAUSEWITZ_ALLOW_POST.
- Navy/air/division-template/production/GameSpeed/HourlyTick out of land Post scope.
- No helper patching, no inject, no Post attempt.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2ce (overnight RO — second-order helpers + role Post paths + offensive Execute deepen)

### Works
- Expanded `SHARED_LAND_HELPERS` with **14** second-order hot callees of the primary 40 (total helpers catalogued **54** = 40 primary + 14 second-order). Classes: field_predicate 6, dispatcher 5, inline 2, wide_walk 1.
- Capstone **offensive-line Execute deepen on 22** attack/retreat/move/strategic/frontline/cancel cmds: field `shared_offs_2ce`, known40 / unknown Execute callees wired.
- Built `LAND_POST_READINESS.role_post_paths` with per-role union gates + **min_gates_intersection** (move/frontline/cancel/strategic documented); Capstone heads for **7** intersection gates.
- Gate/body catalogs grew: IsValid-gate helpers **47**, Execute-body helpers **34**.
- Recipes: `move_command_recipe`, `order_reconnect_recipe`, `replace_fallback_recipe`, `land_role_post_path_recipe`; `land_post_readiness_recipe` enriched for 2ce.
- **LAND 121/121**, **ISVALID_PATHS 134** unchanged; live FN proofs green.
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST / CLAUSEWITZ_ALLOW_POST.
- Helper patch / Post inject; navy/air/division-template/production/GameSpeed/HourlyTick.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2cf (overnight RO — Execute-shared unknowns + theater/order_group/garrison role paths)

### Works
- Mined **47** Execute-shared unknown helpers (≥3 hits across land Execute bodies) into `SHARED_LAND_HELPERS` tier `execute_shared_unknown` → helpers total **101** (40 primary + 14 second_order + 47 exe-unknown).
- Classes: field_predicate 19, dispatcher 16, inline 8, leaf 2, wide_walk 1, string 1. Top: `0xd4b440`×7, `0x25a0448/310/3dc`×6, `0x10b4fa0`×6.
- Capstone deepen **28** cmds (thin Execute + unk-heavy offensive + theater/order_group/garrison samples); wired `execute_unknown_2cf` / `execute_hot_unknown` / `isvalid_calls_2cf`.
- Expanded `role_post_paths` to **all roles** including theater/order_group/garrison; added **soft_gates_majority** (≥50% of gated cmds) where hard intersection is empty.
- Gate/body catalogs: IsValid-gate **75**, Execute-body **81**.
- Recipes: `land_execute_shared_unknown_recipe`, `theater_role_post_path_recipe`, `order_group_role_post_path_recipe`, `garrison_role_post_path_recipe`; role/readiness recipes enriched with soft gates + by_tier.
- **LAND 121/121**, **ISVALID_PATHS 134** unchanged; live FN proofs green.
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST / CLAUSEWITZ_ALLOW_POST.
- Helper patch / Post inject; navy/air/division-template/production/GameSpeed/HourlyTick.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2cg (overnight RO — preferred role cores soft→hard + unknown_second_order)

### Works
- Capstone deepen **79** land cmds (near-miss soft gates + attack/retreat/move/strategic/frontline + thin); fresh IsValid calls **6**, fresh Execute calls **49**.
- Mined **6** `unknown_second_order` helpers (≥3 hits from execute_shared_unknown parents) → helpers total **107** (40+14+47+6).
- Gate/body catalogs: IsValid-gate **76**, Execute-body **86**.
- **Preferred role cores** close soft_gates_majority into hard intersections on coherent subsets (full-role hard may stay empty when outliers differ):
  - attack_core 5/7 → `{0x1e1510, 0x2607890}` (exclude RailwayGun*)
  - retreat_fallback_core → `{0x2284800, 0xbbb1e0}`
  - frontline_core → `{0x2284800, 0xbbb1e0, 0xc40230}` (soft bbb/c402 closed)
  - garrison_core → same triple
  - move_army_core 10/17 → `{0x1e1510, 0x2607890}`
  - strategic_redeploy_core → `{0x254aa00, 0x25a0390}`; strategic_pin_core → `{0x2607890}`
  - order_group_core → `{0x2284800}`; theater_core → `{0x18dde70}`
- Recipes: `land_preferred_core_recipe`, `land_unknown_second_order_recipe`, attack/move/frontline/retreat core wrappers; readiness + role recipes enriched.
- **LAND 121/121**, **ISVALID_PATHS 134**; live FN proofs green.
- Live: allow_post False; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST / CLAUSEWITZ_ALLOW_POST.
- Helper patch / Post inject; navy/air/division-template/production/GameSpeed/HourlyTick.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2ch (overnight RO — expanded preferred cores + cross_land_fresh)

### Works
- Capstone deepen **83** land cmds (near-miss excluded + offensive-line + primary roles); fresh IsValid **1**, fresh Execute **17**. Near-miss soft gates remain absent after wider windows — genuine IsValid divergence, not disasm artifact.
- Mined **30** `cross_land_fresh` helpers (≥3 land hits from deepen) → helpers total **137** (40+14+47+6+30).
- Gate/body catalogs: IsValid-gate **90**, Execute-body **103**.
- Expanded preferred cores **9 → 21**, covering prior exclusions via alternate gate families:
  - garrison_bbb_core **3/3** `{0x2284800,0xbbb1e0}` (closes CreateAreaDefense into hard)
  - frontline_bbb_core **14/15** `{0xbbb1e0}`; retreat_bbb_only_core **5/6**
  - move_theater_core `{0x2284800,0xbbb1e0}`; move_c07b80_core `{0xc07b80}`
  - strategic_unit_redeploy_core `{0x1e1510,0x2607890,0x57f7b0}` (true CStrategicRedeploymentCommand family)
  - order_group_bbb / leader `{0x11ecb20}` / conveyor `{0x1c31490}`
  - theater_garrison_prio `{0x3b65a0,0xac1e20}`; theater_reorder `{0xd73540}`
  - cancel_abort_core full-role hard `{0x2284800,0x2348bf0,0x25c3770}`
- Recipes: land_cross_fresh_helper_recipe; garrison/frontline/move_theater/strategic_unit_redeploy/cancel_abort/theater_garrison_prio wrappers; readiness enriched.
- **LAND 121/121**, **ISVALID_PATHS 134**; live FN proofs green.
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST / CLAUSEWITZ_ALLOW_POST.
- Helper patch / Post inject; navy/air/division-template/production/GameSpeed/HourlyTick.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2ci (overnight RO — named IsValid gates + divergence cores + land_execute_unknown_shared)

### Works
- Capstone deepen **71** land cmds (offensive-line + uncovered + primary roles); fresh IsValid **0**, fresh Execute **9**.
- Mined **58** `land_execute_unknown_shared` helpers (≥2 land Execute hits) → helpers total **195**.
- Gate/body catalogs: IsValid-gate **105**, Execute-body **144**.
- **Named 19 new IsValid gate labels** (28 total incl prior gamestate guards): e.g. `isvalid_field_gate_primary`@0x2284800, `isvalid_army_subject_gate_a/b`@0x1e1510/0x2607890, `isvalid_order_fallback_gate`@0xbbb1e0, strategic/theater/conveyor/leader labels.
- Preferred cores **21→34** with **121/121 coverage**; documented **17 genuine divergences** (RailwayGun manual/name, frontline collapse, move armygroup-theater, amend-manpower, theater template outliers, order_group singleton outliers, plus full-role soft-without-hard notes).
- Recipes: `land_named_gate_recipe`, `land_genuine_divergence_recipe`, `land_execute_unknown_shared_recipe`, `railwaygun_divergence_recipe`.
- **LAND 121/121**, **ISVALID_PATHS 134**; live FN proofs green.
- Live: allow_post False; tick=1; watcher **36128**; tool-gate **CLOSED_NOT_OPENED**; no input.

### Stubbed / skipped
- midflight_CMoveCommand; ring embed; command_queue_tool_gate enable; ALLOW_POST / CLAUSEWITZ_ALLOW_POST.
- Helper patch / Post inject; navy/air/division-template/production/GameSpeed/HourlyTick.

### Posting
**DISABLED.** pause/1x only; never 5x. No guess writes / HourlyTick / speed.

## Phase 2cj (overnight RO) — named helpers + OL unique execute + divergence gate deltas

- **HEAD parent**: `2f6d8ff` (2ci). Focus: deepen remaining land Execute/IsValid edges, recipe gaps, offensive-line execute paths; mine Post readiness **without** enabling Post. **LAND 121/121 unchanged** (no new cmds).
- **Helpers**: 195 → **237** (`offensive_line_unique_execute` 28, `les_second_order` 14). Capstone deepened 106 helper RVAs RO.
- **Named helpers**: 28 → **75** (19 high-hit gate/body labels + 28 OL unique exe labels).
- **Gates / bodies**: IsValid-gate helpers 105→**107**; Execute-body 144→**183**.
- **Preferred cores**: still **34** with **121/121** coverage (no churn).
- **Genuine divergences**: 17 refined with `delta_vs_primary_hard_*` / `delta_vs_role_soft_*` and post_path_note (docs only).
- **Offensive-line Execute**: **25/25** cmds fully cataloged (unique unknowns → `offensive_line_unique_execute` tier + names).
- **Recipes**: `land_named_helper_expansion_recipe`, `offensive_line_execute_recipe`, `land_post_path_checklist_recipe`, `land_divergence_gate_delta_recipe`.
- **Live**: hoi4 pid 2880; midflight watcher **36128** alive RO; `allow_post` False; tool-gate **CLOSED_NOT_OPENED**; named/OL spot reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject. Naval/production out of scope.

## Phase 2ck (overnight RO) — role post-path matrix + selective naming (anti-inflation)

- **HEAD parent**: `ce6ceff` (2cj). Focus: checklist/post-path readiness artifacts over helper-count inflation. **LAND 121/121 unchanged**.
- **Helpers**: **237 unchanged** (shared≥2 missing execute edges: **0**; singletons documented only, not cataloged).
- **Named helpers**: 75 → **96** (+21 high-hit gate/body labels). Capstone deepen 21 named RVAs RO.
- **Preferred cores**: still **34** / **121/121** coverage (no churn).
- **Primary deliverable**: `role_post_path_matrix_2ck` for attack/retreat/move/strategic/frontline/theater/order_group — primary preferred core, soft advisory, named gates, divergence notes, observe-only post_path_steps.
- **Singleton execute edges**: **87** documented under `singleton_execute_edges_2ck` (retreat 10, move 30, strategic 2, theater 15, order_group 30; attack/frontline 0).
- **Checklist**: `post_readiness_checklist_2ck` consolidated readiness summary; allow_post False.
- **Recipes**: `land_role_post_path_matrix_recipe`, `land_singleton_execute_edge_recipe`, `land_post_readiness_checklist_2ck_recipe`.
- **Live**: hoi4 pid 2880; watcher **36128** RO alive; tool-gate **CLOSED_NOT_OPENED**; named spot reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cl (overnight RO) — per-cmd post-path index + core-gate naming

- **HEAD parent**: `196c4fe` (2ck). Focus: checklist/matrix/post-path readiness over count inflation. **LAND 121/121 unchanged**.
- **Helpers**: **237 unchanged**. `gate_label_only_2cl` (15) labels core/IsValid RVAs without helper catalog inflation.
- **Named helpers/labels**: 96 → **116** (+20: 6 preferred-core/divergence gates + high-hit IsValid gates).
- **Primary deliverable**: `cmd_post_path_index_2cl` — **116** in-scope cmds (attack/retreat/move/strategic/frontline/theater/order_group) each with recommended_core, required_gates fully named (116/116), divergence flag, singleton execute RVAs, observe_steps.
- **Matrix**: `role_post_path_matrix_2cl` enriched with gates_fully_named per preferred core + soft_unnamed_remaining.
- **Checklist**: `post_readiness_checklist_2cl` with how_to_use_cmd_index.
- **Recipes**: `land_cmd_post_path_index_recipe`, `land_role_post_path_matrix_2cl_recipe`, `land_post_readiness_checklist_2cl_recipe`.
- **Preferred cores**: still **34** / **121/121**.
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cm (overnight RO) — close gate_label_only + cmd index 121/121

- **HEAD parent**: `4a101a4` (2cl). Focus: close `gate_label_only_2cl` safely; extend cmd index; name high-hit exe. **LAND 121/121 unchanged**.
- **gate_label_only**: **CLOSED** — 15 Capstone-promoted into `SHARED_LAND_HELPERS` tier `gate_label_promoted` (observe-only). Remaining: **0**.
- **Helpers**: 237 → **252** (+15 promoted only; no singleton inflation).
- **Named**: 116 → **145** (+15 promoted + 29 high-hit execute helpers already in catalog).
- **IsValid-gate helpers**: → **122**; Execute-body still 183.
- **Primary**: `cmd_post_path_index_2cm` — **121/121** cmds (now includes garrison/cancel_abort), required gates **121/121 named**, avg `post_path_confidence` **0.911**.
- **Matrix**: `role_post_path_matrix_2cm` for 9 roles (added garrison, cancel_abort).
- **Checklist**: `post_readiness_checklist_2cm`.
- **Recipes**: `land_cmd_post_path_index_2cm_recipe`, `land_gate_label_promoted_recipe`, `land_post_readiness_checklist_2cm_recipe`.
- **Preferred cores**: still **34** / **121/121**.
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; promoted/named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cn (overnight RO) — confidence raise + soft unnamed closed

- **HEAD parent**: `0382205` (2cm). Focus: raise avg post_path_confidence / close soft unnamed with RO naming only. **LAND 121/121 unchanged**.
- **Helpers**: **252 unchanged** (naming only — no inflation).
- **Named**: 145 → **223** (+78 in-catalog shared exe/IsValid helpers, hits≥2).
- **Confidence**: avg **0.911 → 0.957**; cmds below 0.9: 43→**24**; below 0.95: 80→**36**. Required gates still **121/121 named**.
- **Soft unnamed**: all 9 roles **[]** (closed `0xc4f8e0` cancel_abort).
- **Artifacts**: `cmd_post_path_index_2cn`, `role_post_path_matrix_2cn`, `confidence_report_2cn`, `post_readiness_checklist_2cn`.
- **Recipes**: `land_cmd_post_path_index_2cn_recipe`, `land_confidence_report_2cn_recipe`, `land_post_readiness_checklist_2cn_recipe`.
- **Preferred cores**: still **34** / **121/121**.
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2co (overnight RO) — Capstone deep-resolve + shared second-order

- **HEAD parent**: `ff86670` (2cn). Focus: raise avg post_path_confidence / shrink below-0.9 with Capstone RO evidence. **LAND 121/121 unchanged**.
- **Helpers**: 252 → **308** (+56 second-order with hits≥2 only). Thin wrappers **not** added to SHARED catalog.
- **Named**: 223 → **370** (+147 = 31 leftover catalog + 56 SO + 60 Capstone thin wrappers via fully-named callees).
- **Confidence**: avg **0.957 → 0.977**; cmds below 0.9: 24→**6**; below 0.95 shrinks. Required gates still **121/121 named**. Soft unnamed all roles **[]**.
- **Remaining below 0.9**: CCancelRunningAwayCommand, COrderUnassignCommand, CSetQuickDeployPreferenceCommand, CMergeArmiesCommand, CTransportUnitCommand, CRetireCharacterCommand.
- **Artifacts**: `cmd_post_path_index_2co`, `role_post_path_matrix_2co`, `confidence_report_2co`, `post_readiness_checklist_2co`, `deep_resolved_execute_helpers_2co`.
- **Recipes**: `land_cmd_post_path_index_2co_recipe`, `land_confidence_report_2co_recipe`, `land_post_readiness_checklist_2co_recipe`.
- **Preferred cores**: still **34** / **121/121**. IsValid-gate **122**; Execute-body **183** (+SO tracked in body list).
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cp (overnight RO) — soft-6 Capstone structural close

- **HEAD parent**: `1c5a9a1` (2co). Focus: shrink below-0.9 (6 cmds) with Capstone RO structural/string/thunk/strong naming. **LAND 121/121 unchanged**.
- **Helpers**: **308 unchanged** (no SHARED inflation).
- **Named**: 370 → **476** (+106 leaf/string/thunk/strong; outside SHARED catalog).
- **Confidence**: avg **0.977 → 0.990**; cmds below 0.9: 6→**0**. Soft unnamed gates stay **[]**.
- **Soft-6 after**: CancelRunningAway/OrderUnassign/SetQuickDeployPreference/TransportUnit/RetireCharacter → **1.0**; MergeArmies → **0.94** (one execute still unnamed, above 0.9).
- **Artifacts**: `cmd_post_path_index_2cp`, `role_post_path_matrix_2cp`, `confidence_report_2cp`, `checklist_2cp`, `structural_named_2cp`, `naming_evidence_2cp`.
- **Recipes**: `land_cmd_post_path_index_2cp_recipe`, `land_confidence_report_2cp_recipe`, `land_post_readiness_checklist_2cp_recipe`.
- **Preferred cores**: still **34** / **121/121**. IsValid-gate **122**; Execute-body **183**.
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cq (overnight RO) — below-0.95 + MergeArmies Capstone close

- **HEAD parent**: `eec86a4` (2cp). Focus: lift MergeArmies above 0.95; shrink below-0.95. **LAND 121/121 unchanged**.
- **Helpers**: **308 unchanged** (no SHARED inflation).
- **Named**: 476 → **637** (+161 leaf/string/thunk/strong Capstone; outside SHARED).
- **Confidence**: avg **0.990 → 0.997**; below 0.9: **0**; below 0.95: 11→**0**.
- **MergeArmies**: 0.94 → **1.0** (`0x13f8740` → `execute_move_strong_resolved_3f8740`).
- **Artifacts**: `cmd_post_path_index_2cq`, `role_post_path_matrix_2cq`, `confidence_report_2cq`, `checklist_2cq`, `structural_named_2cq`, `naming_evidence_2cq`.
- **Recipes**: `land_cmd_post_path_index_2cq_recipe`, `land_confidence_report_2cq_recipe`, `land_post_readiness_checklist_2cq_recipe`.
- **Preferred cores**: still **34** / **121/121**. IsValid-gate **122**; Execute-body **183**.
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cr (overnight RO) — singleton unnamed execute + OL second-order Capstone close

- **HEAD parent**: `30cde9e` (2cq). Focus: remaining singleton unnamed execute edges + offensive-line deepen. **LAND 121/121 unchanged**.
- **Helpers**: **308 unchanged** (no SHARED inflation).
- **Named**: 637 → **658** (+21: 14 singleton leaf/string/strong + 7 OL second-order).
- **Confidence**: avg **0.997 → 1.000**; below 0.9: **0**; below 0.95: **0**; below 1.0: 12→**0**.
- **MergeArmies**: still **1.0**. Soft unnamed execute: **[]**.
- **Genuine remaining unnamed execute edges**: **none** after Capstone (documented empty `remaining_unnamed_execute_edges_2cr`).
- **Artifacts**: `cmd_post_path_index_2cr`, `role_post_path_matrix_2cr`, `confidence_report_2cr`, `checklist_2cr`, `remaining_unnamed_execute_edges_2cr`, `offensive_line_post_path_2cr`, `structural_named_2cr`, `naming_evidence_2cr`.
- **Recipes**: `land_cmd_post_path_index_2cr_recipe`, `land_confidence_report_2cr_recipe`, `land_post_readiness_checklist_2cr_recipe`, `land_remaining_unnamed_execute_edges_2cr_recipe`, `land_offensive_line_post_path_2cr_recipe`.
- **Preferred cores**: still **34** / **121/121**. IsValid-gate **122**; Execute-body list present.
- **Live**: hoi4 2880; watcher **36128** RO; tool-gate CLOSED; named reads OK.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject.

## Phase 2cs (overnight RO) — Post-readiness usability (live observe + OL/role/midflight docs)

- **HEAD parent**: `5aa04e7` (2cr). Focus: usability after confidence saturation. **LAND 121/121 unchanged**. No Capstone naming churn.
- **Helpers**: **308 unchanged**. **Named**: **658** unchanged.
- **Confidence**: avg **1.000** (unchanged); below 1.0: **0**.
- **Live Haiti army observe**: **22** armies (tag=15) with handle/province_id_ok; docs-only move/attack/strategic field recipes.
- **Focus FN verify**: move / strategic_redeploy / cancel_movement / attack_support — Execute/IsValid prologues + required gates readable.
- **Midflight Move watcher**: pid **36128** alive RO; session drain/exec counters read; CMove path stubbed; no inject.
- **OL post-path**: 25 cmds with observe playbooks (named execute/IsValid maps).
- **Role matrix**: 9 roles with observe playbooks + preferred-core links.
- **Operator checklist**: sequenced A–H usability steps; allow_post False.
- **Artifacts**: `cmd_post_path_index_2cs`, `role_post_path_matrix_2cs`, `confidence_report_2cs`, `checklist_2cs`, `offensive_line_post_path_2cs`, `midflight_move_watcher_readiness_2cs`, `live_army_subject_observe_2cs`, `live_focus_fn_verify_2cs`.
- **Recipes**: index/matrix/confidence/checklist/OL/midflight/live_army/live_fn_verify `_2cs_recipe`.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject / wake user.

## Phase 2ct (overnight RO) — deepen live army + retreat/frontline/theater observe

- **HEAD parent**: `12186b0` (2cs). Focus: deepen live army-subject observation + retreat/frontline/theater role recipes. **LAND 121/121 unchanged**. No Capstone naming churn.
- **Helpers**: **308 unchanged**. **Named**: **658** unchanged.
- **Confidence**: avg **1.000** (unchanged); below 1.0: **0**.
- **Live Haiti army deepen**: **22** armies; proven province_id/controller_tag_hyp(+0x58)/template name (`CReferencedDivisionTemplate+0x20`); org/str floats at `0x520`/`0x6ec` **hypothesis only** (5 nonzero); **movement_dest empty** while paused (do not invent).
- **Role observe**: retreat (6) / frontline (5) / theater (5) + move/attack/strategic/garrison/cancel_abort/order_group — live Execute/IsValid prologue + required gates readable.
- **OL post-path**: 25 cmds refreshed with army/role cross-links.
- **Midflight Move watcher**: pid **36128** alive RO; session counters read; CMove path stubbed; no inject.
- **Operator checklist**: sequenced A–H usability steps; allow_post False.
- **Artifacts**: `cmd_post_path_index_2ct`, `role_post_path_matrix_2ct`, `role_observe_2ct`, `confidence_report_2ct`, `checklist_2ct`, `offensive_line_post_path_2ct`, `midflight_move_watcher_readiness_2ct`, `live_army_subject_observe_2ct`.
- **Recipes**: index/matrix/role_observe/confidence/checklist/OL/midflight/live_army `_2ct_recipe`.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject / wake user / promote hyp org offsets.

## Phase 2cu (overnight RO) — CArmy vs CTaskForce classify; org hyp rejected

- **HEAD parent**: `42b360b` (2ct). Focus: stronger RO on org/str + movement_dest; deepen role/OL/midflight usability. **LAND 121/121 unchanged**. No Capstone naming churn.
- **Helpers**: **308 unchanged**. **Named**: **658** unchanged.
- **Confidence**: avg **1.000** (unchanged); below 1.0: **0**.
- **Live subject classify**: iterator hits = **17 CArmy** + **5 CTaskForce** (RTTI). VT RVAs: CArmy `0x29d6d68`, CTaskForce `0x29df8a0`.
- **Org/str REJECTED**: prior 0x520/0x6ec nonzero rows were **CTaskForce**, not CArmy. All CArmy divisions have those floats **0.0** while paused. Do not promote.
- **movement_dest**: still **empty** (paused; midflight captures=0 after 57k+ polls). Do not invent.
- **Role observe**: retreat/frontline/theater (+ move/attack/strategic/…) with field_map docs + live FN/gates.
- **OL post-path**: 25 cmds refreshed with field_map + cross-links.
- **Midflight Move watcher**: pid **36128** alive RO; captures=0; no inject.
- **Operator checklist**: A–H; allow_post False.
- **Artifacts**: `cmd_post_path_index_2cu`, `role_post_path_matrix_2cu`, `role_observe_2cu`, `confidence_report_2cu`, `checklist_2cu`, `offensive_line_post_path_2cu`, `midflight_move_watcher_readiness_2cu`, `live_army_subject_observe_2cu`.
- **Recipes**: index/matrix/role_observe/confidence/checklist/OL/midflight/live_army `_2cu_recipe` (live army defaults CArmy-only).
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject / wake user / promote rejected org offsets.

## Phase 2cv (overnight RO) — CArmy theatre/namegroup deepen

- **HEAD parent**: `4156493` (2cu). Focus: CArmy-only deepen (theatre/namegroup); org stays rejected; movement_dest not invented. **LAND 121/121 unchanged**. No Capstone naming churn.
- **Helpers**: **308 unchanged**. **Named**: **658** unchanged.
- **Confidence**: avg **1.000** (unchanged); below 1.0: **0**.
- **Live CArmy links (new)**: `CArmy+0x2a0` → **CTheatre** (17/17; 1 shared theatre); `CArmy+0x340` → **CNameGroupMember**; display name at `CNameGroupMember+0x60` (e.g. `1a División de Infantería`).
- **CTheatre fields**: country_tag `@0x0c`/`@0x48` (=15); province `@0xe8` → CProvince.
- **Also**: `CArmy+0x478` → CArmyRequests (RTTI noted).
- **Org/str**: still **REJECTED** (0/17 CArmy nonzero at 0x520/0x6ec). Do not revive.
- **movement_dest**: still **empty** (paused; midflight captures=0).
- **Role observe**: retreat/frontline/theater (+…) with theatre live crosslink + field_map docs.
- **OL / midflight / checklist**: refreshed; allow_post False.
- **Artifacts**: `cmd_post_path_index_2cv`, `role_post_path_matrix_2cv`, `role_observe_2cv`, `confidence_report_2cv`, `checklist_2cv`, `offensive_line_post_path_2cv`, `midflight_move_watcher_readiness_2cv`, `live_army_subject_observe_2cv`.
- **Recipes**: index/matrix/role_observe/confidence/checklist/OL/midflight/live_army `_2cv_recipe`.
- **Hard no**: posting / ALLOW_POST / guess writes / HourlyTick / GameSpeed / helper patch / Post inject / wake user / revive rejected org offsets.


## Phase 2cw (overnight RO) — CArmyRequests / theatre air-mgr / FrontSection observe

- **HEAD parent**: `03cfd23` (2cv). Focus: theatre/army crosslink deepen; org stays rejected; movement_dest not invented. **LAND 121/121 unchanged**. No Capstone naming / helper inflation.
- **CArmyRequests (new field-map, 17/17)**: owner CArmy `@+0x8/+0x30/+0x90`; `CReinforcementStatus` `@+0x50` (vt `0x2a4b158`, shared singleton); `CArmyUpgradesStatus` `@+0x98` (vt `0x2a4b308`, shared); peer CArmy hyp `@+0x108` (partial chain).
- **CArmy+0x418**: self-ref (17/17) — identity pointer, not peer chain.
- **CTheatre**: `CStrategicAirManager` `@+0x268` (vt `0x29d51e8`); repeats at `+0x448/+0x628/+0x808/+0x9e8/+0xbc8` (stride `0x1e0`). HAI unique theatres still **1**.
- **Front/order heap observe**: `CFrontSection` **1570** (`CFront` via `+0x10` vt `0x29f2280`; `SPerCountrySection` via `+0x18`); `COrdersGroup`/`COrdersGroupMember`/`COrderInstance`/`CArmyGroup` **0** (no player orders). `CTheatre` heap **90** (HAI=1).
- **Org/str**: still **REJECTED**. **movement_dest**: empty (paused).
- **Role observe**: theater/frontline/order_group crosslink notes; read_ok preserved; OL refreshed; midflight watcher RO.
- **Operator checklist**: A–H; allow_post False.
- **Artifacts**: `cmd_post_path_index_2cw`, `role_post_path_matrix_2cw`, `role_observe_2cw`, `confidence_report_2cw`, `checklist_2cw`, `offensive_line_post_path_2cw`, `midflight_move_watcher_readiness_2cw`, `live_army_subject_observe_2cw`.
- **Recipes**: index/matrix/role_observe/confidence/checklist/OL/midflight/live_army_2cw.
- **Stubbed**: midflight_CMoveCommand / ring_embed / ALLOW_POST / command_queue_tool_gate CLOSED_NOT_OPENED. Never Post / speed / input / wake user.


## Phase 2cx (overnight RO) — CFront theatre/controller + reinf/upgrades country

- **HEAD parent**: `641f1b3` (2cw). Focus: FrontSection/CFront + army requests status deepen; org stays rejected; movement_dest not invented. **LAND 121/121 unchanged**.
- **CFront (new)**: `+0x18` → **CTheatre** (300/300 sampled); `+0x70` → **CControllerArea** (300/300). **6** sampled fronts reference HAI theatre.
- **CFrontSection**: still `+0x10`→CFront / `+0x18`→SPerCountrySection; heap **1570**; unique fronts ~**1199**.
- **SPerCountrySection**: `u32@+0x8` often country tag (hyp); backrefs to CFrontSection at `+0x60/+0x68` (sample).
- **CReinforcementStatus+0x38** → **CCountry** HAI (tag@country+0x8=15); shared with **CArmyUpgradesStatus+0x38**. Upgrades `+0x178` → **CLoopHistory**.
- **Peer@CArmyRequests+0x108**: remains partial multi-component hyp (not full 17-cycle).
- **Org/str REJECTED**; **movement_dest** empty; order-group heap still 0.
- **Artifacts/recipes**: `*_2cx`; checklist A–H; allow_post False; watcher 36128 RO.
- **Stubbed**: midflight_CMoveCommand / ring_embed / ALLOW_POST / tool-gate CLOSED_NOT_OPENED.

## Phase 2cy (overnight RO) — CFront slot-array + CControllerArea province

- **HEAD parent**: `98a4079` (2cx). Focus: CFront/theatre/controller deepen; org stays rejected; movement_dest not invented. **LAND 121/121 unchanged**.
- **CFront (new)**: embedded **8-slot** array — `CTheatre*` @ `+0x18+k*0x90`, `CControllerArea*` @ `+0x70+k*0x90` for `k=0..7`. Slot0 **1199/1199**; slot pairs remain **≥1143/1199**. Distinct theatres/front mean ~**4.34**.
- **HAI theatre fronts**: **30** fronts contain HAI theatre in any slot (slot0-only count was 6).
- **CControllerArea (new)**: `+0x28` → **CProvince** (**296/296**); `+0x148` → **CProvince** (**288/296**). Heap **296**.
- **SPerCountrySection**: `u32@+0x8` tag hyp (8 HAI); inline `CArmy*` at variable offs — **no** stable field/vector proven.
- **Heap**: FrontSection **1570** / fronts **1199** / theatres **90**; order-groups still 0.
- **Org/str REJECTED**; **movement_dest** empty; recipes `*_2cy`; allow_post False; watcher 36128 RO.
- **Stubbed**: midflight_CMoveCommand / ring_embed / ALLOW_POST / tool-gate CLOSED_NOT_OPENED.

## Phase 2cz (overnight RO) — CFront slots≥16 + FS slot-embed + prov+0x58 reject

- **HEAD parent**: `6b6c386` (2cy). Focus: extend CFront slot array; FrontSection↔slot; province tag hyp cleanup. **LAND 121/121 unchanged**.
- **CFront (new)**: slot array proven for **k=0..15** (at least) — `CTheatre*` @ `+0x18+k*0x90`, `CControllerArea*` @ `+0x70+k*0x90`. Slot0 **1199/1199**; slot15 **≥1114/1199**. 2cy's 8-slot bound raised.
- **HAI theatre fronts**: **44** any-slot (was 30 @8 / 6 @slot0).
- **CFrontSection (new)**: blob often embeds parent front slot `theatre*` / `controller*` (866 / 305 matches); no single stable slot-index field.
- **CProvince+0x58**: **REJECTED** as controller-country tag (does not track occupying `CArmy.country_tag`; often 15 on controller-linked provinces).
- **Org/str REJECTED**; **movement_dest** empty; recipes `*_2cz`; allow_post False; watcher 36128 RO.
- **Stubbed**: midflight_CMoveCommand / ring_embed / ALLOW_POST / tool-gate CLOSED_NOT_OPENED.

## Phase 2da (overnight RO) — CFront slots≥64 + FS theatre embeds + req peer

- **HEAD parent**: `a2c5246` (2cz). Focus: extend CFront slot bound; stabilize FrontSection theatre embeds; theatre↔army crosslink; CArmyRequests peer.
- **CFront (new)**: slot array proven for **k=0..63** (at least) — `CTheatre*` @ `+0x18+k×0x90`, `CControllerArea*` @ `+0x70+k×0x90`; slot0 1199/1199; slot63 947/1199. HAI theatre in **92** fronts any-slot (was 44@16). May extend further; no reliable slot-count header field.
- **CFrontSection (new)**: stable parent-slot **theatre*** embeds at `+0x28/+0x40/+0x58` (122/1570), repeating every `+0x70`. Controller* embeds weak/noisy this session (not same-k).
- **CArmyRequests (new)**: peer `CArmy*` hyp @ `+0x108/+0x130/+0x190` — 10/17 other HAI (not self).
- **Theatre→army direct**: unresolved (0 hits for CArmy*/req/handle in theatre blob); army→theatre @`+0x2a0` remains one-way.
- **Not revived**: org/str; CProvince+0x58. **movement_dest** empty (paused). Recipes `*_2da`; allow_post False; watcher 36128 RO.

## Phase 2db (overnight RO) — REJECT CFront multi-slot array (packed 0x90) + req peer alias

- **HEAD parent**: `54a9d87` (2da). Focus: bound-check CFront slots; strengthen req peer; theatre→army alt paths; FS stride.
- **CFront (correction)**: multi-slot array model from 2cy–2da **REJECTED**. 1171/1199 objects have another `CFront` at `+0x90`; `theatre` at former "slot k" equals `(F+k×0x90)+0x18`. Objects pack at stride **0x90** (max run 454). Per-object fields remain `CTheatre*` @ `+0x18` and `CControllerArea*` @ `+0x70` (1199/1199). HAI fronts via theatre@+0x18 = **6** (any-slot counts were neighbor-walk inflation).
- **CFrontSection**: theatre* embeds @ `+0x28/+0x40/+0x58` (+0x70 repeats) reinterpreted as packed-run neighbor theatres; not parent multi-slots.
- **CArmyRequests**: peer `CArmy*` at `+0x108/+0x130/+0x190` are an **aliased triple** (identical 16/17); chain not bidirectional.
- **Theatre→army direct**: still unresolved (0). Army→theatre @`+0x2a0` one-way.
- **Not revived**: org/str; CProvince+0x58. Recipes `*_2db`; allow_post False; watcher 36128 RO.


## Phase 2dc (overnight RO) — CFront kind/id + peer one-way chains

- **HEAD parent**: `5c51ac9` (2db). Focus: CFront intra-object under packed 0x90; peer graph; theatre→army alt; FS/SPer army embeds.
- **LAND 121/121 unchanged**. Helpers/named **308/658**. Confidence **1.000**.
- **CFront (new)**: `u32@+0x8 = 0x42` constant (**1199/1199**); `u32@+0xc` unique front id (**1199/1199**). Intra-object RTTI ptrs in `[0..0x90)` only theatre@+0x18 + controller@+0x70 (400/400 sample) — reinforces packed model / multi-slot REJECTED.
- **Packed runs**: mix many theatres (run454 → 41 unique) — allocator adjacency, not ownership.
- **HAI fronts**: still **6**; no army province match; no army ptr in front / FS / SPer; army→front reverse **0**.
- **CArmyRequests peer**: aliased triple forms **one-way chains** (in_deg max 1); 10 HAI + 5 DOM(`tag=16`) + null/garbage; not bidir / not owner list. Status `hypothesis_peer_chain_oneway_2dc`.
- **Theatre→army**: still **UNRESOLVED** (0 direct / 0 arrays / 0 handles).
- **SPerCountrySection**: `u32@+0x8` HAI tag proven (8); province-id-range hyp @+0x20..+0x34 remains **weak** (0 overlap with army provs).
- **Orders heap**: still 0. Org/str + prov+0x58 stay REJECTED. Recipes `*_2dc`; allow_post False; watcher 36128 RO.
- **Stubbed**: midflight_CMoveCommand / ring_embed / ALLOW_POST / tool-gate CLOSED_NOT_OPENED.

## Phase 2dd (overnight RO) — TH_ARMIES@+0x68 + TH_FRONTS@+0x50 CPdxArray proven

- **HEAD parent**: `b46f6be` (2dc). Focus: theatre↔army crosslink via documented CO_*/TH_* CPdxArray offsets (missed earlier due to wrong array layout assumption).
- **CPdxArray layout (Windows)**: `{T* data; i32 capacity; i32 size; void* alloc}` — not begin/end pair.
- **Proven live**:
  - `CCountry+0x290` **CO_ARMIES** → 17 CArmy* (HAI tag ok 17/17)
  - `CCountry+0x168` **CO_THEATRES** → 1 CTheatre*
  - `CTheatre+0x50` **TH_FRONTS** → 6 CFront* with ids **[173, 174, 175, 176, 177, 178]**; each front `+0x18` theatre embeds match owning theatre; kind `0x42`
  - `CTheatre+0x68` **TH_ARMIES** → 17 CArmy* — **identical set** to CO_ARMIES (distinct data buffers)
- **Theatre↔army**: now **bidirectional via arrays** (TH_ARMIES + army `+0x2a0`). Prior "theatre→army 0" was a false miss from begin/end scans.
- **CFront↔army**: still no direct CArmy* embed in front blob; link is theatre-mediated (resolved_indirect_2dd).
- **Unchanged**: peer `hypothesis_peer_chain_oneway_2dc`; packed 0x90 REJECT; org/str REJECT; prov+0x58 REJECT; movement_dest=0 (paused); orders heap 0; LAND **121/121**; confidence **1.000**; helpers 308 / named 658.
- **Not revived**: org/str; CProvince+0x58. Recipes `*_2dd`; allow_post False; watcher 36128 RO.

## Phase 2de (overnight RO) — CControllerArea provinces + REJECT CFront>0x90 bleed

- **HEAD parent**: `6e4460c` (2dd). Focus: army↔front via controller; peer locality; FrontSection/CFront extend check.
- **CControllerArea (new)**: `CPdxArray<CProvince*>` @ `+0x30` / `+0x60` / `+0xb0` (**6/6** HAI front controllers); `CPdxArray<CStrategicRegion*>` @ `+0xf8` (**6/6**).
- **CFront extended >0x90**: candidate arrays @ `+0xb0` (prov) / `+0xe8` (FS) / `+0x140` / `+0x178` **REJECTED_PACKED_NEIGHBOR_BLEED_2de** — valid-looking only when `+0x90` neighbor CFront exists; last-in-run garbage. Same failure mode as multi-slot (2db).
- **Army↔front via ctrl provinces**: **0/17** matches while paused (army province not in controller province sets).
- **Peer locality**: 10/17 HAI peers share theatre + sit in TH_ARMIES; still **0 bidir**; status remains `hypothesis_peer_chain_oneway_2dc`.
- **Unchanged**: TH_ARMIES/TH_FRONTS (2dd); packed 0x90 REJECT; org/str REJECT; movement_dest=0; orders 0; LAND **121/121**; confidence **1.000**.
- Recipes `*_2de`; allow_post False; watcher 36128 RO.

## Phase 2df (overnight RO) — COwnerArea mirrors ControllerArea

- **HEAD parent**: `9167685` (2de). Focus: owner-area structure; FrontSection local reverse (0 near HAI fronts this pass).
- **COwnerArea (new)**: `CPdxArray<CProvince*>` @ `+0x30` (**9/9**) / `+0xb0` (**9/9**); `+0x60` partial (**5/9**); `CPdxArray<CStrategicRegion*>` @ `+0xf8` (**9/9**).
- **CA∥OA**: `CO_OWNER_AREAS[i]+0x30` province set **identical** to `CO_CONTROLLER_AREAS[i]+0x30` for all **9** HAI pairs.
- **FrontSection**: local ±0x8000 scan around HAI fronts found **0** FS with `+0x10==front` (allocator not local); unresolved this pass.
- **Unchanged**: TH_ARMIES/TH_FRONTS; ctrl provinces (2de); CFront>0x90 REJECT; peer hyp; org/str REJECT; LAND **121/121**; confidence **1.000**.
- Recipes `*_2df`; allow_post False; watcher 36128 RO.


## Phase 2dg (overnight RO) — TH_CONTROLLER_AREAS + FS heap reverse

- **HEAD parent**: `4aa0ab6` (2df). Focus: deepen CO/TH array graph; FS reverse; CA population split; peer only with stronger proof.
- **LAND 121/121 unchanged**. Helpers/named **308/658**. Confidence **1.000**.
- **CTheatre (new)**: `+0x18` **TH_CONTROLLER_AREAS** — `CPdxArray<CControllerArea*>` size **9**, **identical ordered** to `CO_CONTROLLER_AREAS@CCountry+0x548`; **distinct data buffers** (not aliased).
- **CA population split**: 6 HAI front-linked controllers (`CFront+0x70`) are **DISJOINT** from the CO/TH CA set of 9 — frontline-local vs country/theatre area lists.
- **CFrontSection (new)**: full-heap reverse finds FS with `parent@+0x10` → HAI fronts **173–178** (8 FS; ≥1 per id). Prior local ±0x8000 miss was allocator non-locality. FS `CPdxArray<CProvince*>` @ `+0x30` / `+0x48`. Still **0** HAI `CArmy*` embeds in FS/SPer.
- **Peer**: OA `+0x30` co-membership **6/16** pairs; still **0 bidir** — status remains `hypothesis_peer_chain_oneway_2dc`.
- **Unchanged**: TH_ARMIES/TH_FRONTS (2dd); CA/OA provinces (2de/2df); CFront>0x90 REJECT; org/str REJECT; prov+0x58 REJECT; movement_dest=0; orders 0.
- Recipes `*_2dg`; allow_post False; watcher 36128 RO.
- **Stubbed**: midflight_CMoveCommand / ring_embed / ALLOW_POST / tool-gate CLOSED_NOT_OPENED.

## Phase 2ei (efficient low-burn) — Midflight CMove capture recipe + watcher RO harden

- **HEAD parent**: `eeb8043` (2dg). **ONE slice only** — no Capstone/helper/confidence churn (LAND 121/121 + conf 1.0 CLOSED).
- **Focus**: close shortest blocker docs toward land command readiness — midflight `CMoveCommand` sample path.
- **Docs**: `docs/MIDFLIGHT_CMOVE_CAPTURE.md` — exact capture recipe, VT table, human right-click steps, stub inventory.
- **Watcher RO harden** (`scripts/phase2bm_midflight_ready.py`):
  - Heartbeat → `reports/midflight_watcher_heartbeat.json`
  - Instant capture dump → `reports/midflight_cmove_capture.json`
  - Default `--heap-every 0` (no periodic heap scan on long arm; saves CPU)
  - Still **no** input inject / **no** Post / **no** speed change
- **Live**: watcher was pid **36128** RO armed; hoi4 **2880** Haiti. `movement_dest` empty while paused (not retested at 1x this slice — not cheap without user right-click).
- **Stubbed unchanged**: midflight sample itself; in-process Move ring embed; `command_queue_tool_gate` **CLOSED_NOT_OPENED**; `ALLOW_POST` / `CLAUSEWITZ_ALLOW_POST`.
- **Not revived**: org/str @0x520/0x6ec; prov+0x58; CFront multi-slot/>0x90 bleed; army↔front via ctrl/FS while paused.
- **Posting DISABLED**. Naval/production out of scope.

## Phase 2ej (2026-10-31 Asia/Shanghai) — 1x clock + MOVE attempt (Post still DISABLED)

- **1x works** via `scripts/launch_into_map.py --speed 1` (`-start_tag=HAI -start_speed=1 -noai`). Space/SendInput/mouse_event still ignored by DX11 (same as 2bf/2bg); drain-only is a false unpause signal (exec/seq can stay 13/15).
- **Clock proof**: after relaunch, DummyServer `exec`/`seq`/`drain` leave paused sticky values and keep increasing at 1x (e.g. exec 323→370 / seq 325→373 in ~12s). Status `date_year=1936`; full H:M still unproven; `date_aux_0x47c` hyp unchanged in probe.
- **Land MOVE stubbed**: synthetic LMB+RMB produced no `CMoveCommand`. Catalogued issue path is DummyServer Post / `move_command_recipe` — requires `ALLOW_POST` (still False). `G_CONSOLE_MANAGER` null. `-noai` ⇒ no autonomous army moves. No `reports/midflight_cmove_capture.json`.
- Watcher re-armed RO (`phase2bm_midflight_ready.py`, heap-every 0). Posting stays DISABLED. Never 5x.
- Report: `reports/phase2ej_1x_move.json`.


## Phase 2ek (2026-10-31 Asia/Shanghai) — MOVE issue-path audit (Post still DISABLED)

- **Cannot self-issue land MOVE/attack** without Post: all `move_command_recipe` / `order_execute` / offensive-line / frontline recipes are RO field maps; `config.allow_post()` **hard-returns False** (even if `CLAUSEWITZ_ALLOW_POST=1`). Console `G_CONSOLE_MANAGER` / `FN_CONSOLE_EXECUTE` still null. DX11 ignores synthetic input.
- **Clock**: sim running at 1x — `CHourlyTickCommand` seen in stage; DummyServer `exec`/`seq` keep rising (not paused sticky 13/15). `G_GAMESTATE+0x478` year=1936; `+0x480/+0x484` change over wall time (hour-like hyp). Full UI `Y-M-D H:M` pack still unproven — top-bar may still look near 1936-01-01 12:00 until mapped.
- **Shortest blocker**: ALLOW_POST hard-deny + tool-gate CLOSED + missing midflight `CMoveCommand` sample.
- **Next cheapest (RO)**: map UI-accurate date/hour from `G_GAMESTATE`; keep watcher armed. Do not open Post yet.
- Report: `reports/phase2ek_issue_path_audit.json`. Never 5x. `allow_post` False.

## Phase 2el — G_GAMESTATE UI datetime (RO) — 2026-10-31

**Goal:** Map UI-accurate date/year/month/day/hour from G_GAMESTATE so top-bar time is readable vs bookmark 1936-01-01 12:00. No Post / ALLOW_POST / inject / HourlyTick / speed hacks.

**Proven:**
- G_GAMESTATE+0x478 = i32 calendar year (1936)
- G_GAMESTATE+0x484 = i32 **hours since 1936-01-01 00:00** → decode to Y-M-D H
- Live confirmation: hours advanced (e.g. 68→71 while status re-ran); UI e.g. **1936-01-03 20:00** / later; past bookmark 12:00 by tens of hours at 1x
- Year@+0x478 matches decoded year from +0x484
- Minute: **not available** (hourly resolution only) — stubbed as :00

**Unproven / stubbed:**
- +0x47c aux (28/31) — not day-of-year
- +0x480 hour-like wraps oddly — not required for UI
- +0x488 ≠ day/month

**Wiring:** calling/offsets.py GS_DATE_HOURS; calling/gamestate.py date_full + verified; status surfaces UI string.

**Safety:** llow_post() remained False. Watcher RO stayed armed. No Post / move issue.

**Scripts:** scripts/phase2el_map_gs_date.py, phase2el_date_roll.py, phase2el_confirm_hours.py; report 
eports/phase2el_gs_datetime.json.

## Phase 2em — midflight edge-burst + sightline (RO) — 2026-10-31

**Choice:** A — strengthen midflight watcher (no Post).

**Works:**
- Edge-burst on drain/exec/seq delta (--burst-on-edge 12) + tighter --interval 0.02
- Sightline proved live at 1x: **CHourlyTickCommand ×289** in 25s smoke via stage[0]
- Heartbeat/sightline JSON updated; Move capture path unchanged (instant dump on army-move VT)

**Stubbed:** midflight CMoveCommand sample (still needs real gameplay right-click; agent does not ask / inject)

**Safety:** allow_post False; watcher RO re-armed; no ALLOW_POST / inject / HourlyTick abuse / 5x

**Next shortest blocker:** live midflight CMoveCommand (+ action embed) sample — then serialize/recreate + explicit ALLOW_POST before any tool-gate open.

