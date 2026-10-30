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
