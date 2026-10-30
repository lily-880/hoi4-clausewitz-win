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
