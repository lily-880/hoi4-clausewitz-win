# Windows offset recovery — HOI4 1.19.4 PE

Target: `hoi4.exe` PE32+ · ImageBase `0x140000000` · SizeOfImage `0x38a3000`  
SHA256: `CF781ED178CD801643B233B7E3FCD1C0EFD19BD01AECD24BF07A35F69F10476F`  
Launcher: 1.19.4.1 (Operation Postern)

Upstream Clausewitz-MCP RVAs are **Linux ELF 1.19.2** — do not copy.

## Session requirement (lobby vs in-campaign)

| Session | Signal | live-gs / status |
|---------|--------|------------------|
| Lobby / menu / unloaded | No GS / CCurrentGameState / CInGameIdler heap vptrs | 0 hits — expected |
| Campaign object live | `CCurrentGameState` (and often large WS) | `live-gs` / `status` return fields |

```text
python clausewitz_win.py session-probe
python clausewitz_win.py live-gs
python clausewitz_win.py status
```

## Proven static (safe to cite)

| Symbol | RVA | Notes |
|--------|-----|-------|
| CGameState vtable | `0x279f0f0` | COL live MATCH |
| CGameState vtable (2nd) | `0x279f148` | |
| CCurrentGameState vtable | `0x279f168` | live object vptr |
| CCurrentGameState vtable (2nd) | `0x279f1c0` | MI @ object+8 |
| CInGameIdler vtable | `0x29e5838` | |
| CGameIdler vtable | `0x27b4158` | |
| CCommand vtable | `0x279f4a0` | |
| CArmy vtables | `0x29d6d68` (+ MI `0x29d6f48`, `0x29d6fb8`, `0x29d7000`) | RTTI COL; live army arrays **not** yet proven |
| CUnit vtables | `0x29cfac0` (+ MI) | RTTI COL; no live hits this campaign sample |
| CDate | TypeDescriptor only | **no vtable** (POD); not used for status yet |
| CGameState ctor LEAs | `0x1d78ae`, `0x1da5a6` | |

## G_GAMESTATE — promoted (Phase 2d)

| Field | Value |
|-------|-------|
| RVA | **`0x33dd6b0`** |
| File | `calling/offsets_verified.json` |
| How | `.data` slot → `CCurrentGameState` (`0x279f168`) |
| Re-verify | Same slot/object after full campaign load (WS ~4.4 GB); countries **440**, player_tag **15**, majors **3** |
| Caveat | Re-check after **new PID** / game patch before trusting blindly |

### Campaign fields (read-only status)

| Field | Offset hyp | Status |
|-------|------------|--------|
| countries_count | GS+`0x310` CPdxArray.size | **verified** (440) |
| majors_count | GS+`0x328` | **verified** (3) |
| player_tag | GS+`0x518` | **verified** (15) |
| date_year | GS+`0x478` i32 | **hypothesis** (1936); exposed in status with note |
| date_aux | GS+`0x47c` i32 | **hypothesis** (seen 31) — possible day-of-year; **not** full Y-M-D |
| divisions_count | — | **stubbed** — see dead ends |
| GS_PAUSE_HOURS `0x908` | Linux | **invalid** on Windows (pointer-looking) |
| CO_STATES | Country+`0x460` | **matches Linux** (CState* arrays; vptr `0x29b4d38`) |
| CO_ARMIES `0x290` | Country+`0x290` | **verified in-game** (`CArmy*`; see Phase 2h) |

## Command queue — FN known (Phase 2p); writes still DISABLED

Linux path (Clausewitz-MCP FINDINGS): `CCommandQueue::Post` @ ELF `img+0x2DC1C40`; queue from `CInGameIdler`, reached via **idler vtable+0x90**.

### Windows decode (static, proven as code shape — not as Post RVA)

| Item | Value |
|------|-------|
| CInGameIdler vt+`0x90` method | RVA **`0xe34e90`** |
| Shape | Optional `CFileLogger` global `0x33dd090` → load **`[this+0x530]`** → **`jmp [rax+0x90]`** |
| Hypothesis | Queue-like object at **Idler+`0x530`**; Post-analog = that object's **vtable+0x90** |
| FN_CMD_QUEUE_POST | **null** — need live idler + typed queue + callee proof |

### Dead ends (do not promote)

| Lead | Result |
|------|--------|
| `.?AVCCommandQueue@@` / `CGameCommandQueue` / `CPdxCommandQueue` | Absent |
| `PostCommand` / mangled `?Post@` | 0 hits |
| `CommandQueue` ASCII | SDL2 GL red herring |
| `QueueCommand` / `ExecuteCommand` strings | RTTI name fragments of command *subclasses*, not a Post API; LEA soft-call targets (e.g. `0x25a009c`) are ctor-neighborhood helpers — **not** Post |
| Copy Linux `0x2DC1C40` | Invalid on PE |
| Live `CInGameIdler` heap vptr | **0 hits** in ≤512 MB heap sample while `G_GAMESTATE` live — cannot read `+0x530` yet |
| Live `CArmy` / `CUnit` heap vptrs | **0 hits** in large samples; country array hunt found **no** `CArmy*` CPdxArray (player + 3 majors); divisions stay stubbed |
| DATE float sig `0x3D2AAAAB` | 0 hits in GS blob this sample |

See `scripts/phase2e_post_graph.py` → `research/re-dumps/phase2e_post_graph.json`  
Live follow-up: `scripts/phase2e_live_scan.py` (idler / `+0x530` / army arrays).  
Do not invent Post. `CLAUSEWITZ_ALLOW_WRITE` does not enable posting.

### Next proof steps (still read-only until done)

1. Catch live `CInGameIdler` while map UI is active (re-run `phase2e_live_scan.py`).
2. Read `idler+0x530` → RTTI-identify queue object vtable.
3. Characterize that object's `vtable+0x90` (must take `CCommand*`, enqueue).
4. Only then set `FN_CMD_QUEUE_POST` (writes still gated).


## Phase 2f — live idler Post-path (read-only) + army hunt

Session under test: **frontend / lobby** (pid 30600, WS ~6.5 GB heap scanned).  
`G_GAMESTATE` live with countries=440 / player_tag=15 / date_year≈1936, but **no map UI**.

### G_IDLER — promoted (session-typed)

| Field | Value |
|-------|-------|
| RVA | **`0x33ddb08`** |
| File | `calling/offsets_verified.json` |
| Live type (this session) | **`CFrontEndIdler`** (`0x29c6d30`) |
| Expect in-game | `CInGameIdler` (`0x29e5838`) in the **same slot** (re-verify on map) |

### Post-path exercised READ-ONLY (no Post / no write)

| Step | Result |
|------|--------|
| FE vt+`0x90` | RVA **`0xb8dca0`** — `mov rcx,[rcx+0x530]; jmp [rax+0x90]` |
| IG vt+`0x90` | RVA **`0xe34e90`** — optional logger → same `[this+0x530]` → `jmp [rax+0x90]` |
| Live FE+`0x530` | **`CGameApplication`** (`0x2796308`) |
| App vt+`0x90` | RVA **`0x1b14f0`** — **setter** of `this+0x380` (`CSession*`); **NOT Post** |
| `FN_CMD_QUEUE_POST` | **still null** — need live `CInGameIdler` + typed queue object's vt+`0x90` |

Shape is proven; **callee identity is session-dependent**. FrontEnd's `+0x530` is Application, not a command queue.

### Armies / divisions — still stubbed

| Lead | Result |
|------|--------|
| Full-heap `CArmy` / MI | **0** hits (~6.5 GB, 12k+ regions) |
| Full-heap `CUnit` | **0** |
| Full-heap `CArmyGroup` (`0x29cee28` / `0x29ceea0`) | **0** (RTTI exists; no live objects) |
| Player `CCountry` arrays | `CO_STATES@0x460` live; **no** `CArmy*` CPdxArray; `CNavyTheater` @ `+0x160` |
| Linux `CO_ARMIES@0x290` | empty / not army ptrs on Windows this sample |

Frontend GS has countries/states but **no military units spawned** — expected until map/in-campaign.

### Dead ends (Phase 2f)

| Lead | Result |
|------|--------|
| Treat App vt+`0x90` (`0x1b14f0`) as Post | **Rejected** — setter(+0x380), 0 E8 callers, absent from CCommand soft-call neighborhood |
| `.?AVCCommandQueue@@` | Still **NONE** |
| Soft tops `0x25a009c` / `0x25a00d8` / `0x11f6f0` | ctor-neighborhood helpers, not Post-shaped |
| `CSession` / `CNavyTheater` as queue stand-ins | No command-queue RTTI behind them |
| Promote Post from FrontEnd path | **Forbidden** — wrong object at `+0x530` |

Tooling: `scripts/phase2f_idler_postpath.py` (RO resolve + optional heap counts).

### Next proof steps (still read-only until done)

1. Load a campaign map so `G_IDLER` → **`CInGameIdler`** (re-run `phase2f_idler_postpath.py`).
2. RTTI-identify live `idler+0x530`; decode that object's **vt+`0x90`** (must take `CCommand*`, enqueue).
3. Re-scan heap for `CArmy` / `CArmyGroup` once map is up; wire `divisions_count` only if proven.
4. Only then set `FN_CMD_QUEUE_POST` (writes still gated).



## Phase 2g — session gate (frontend vs in-game)

**One-shot check (no polling):** this process was still **`CFrontEndIdler`** after Phase 2f.

### Classification rule (promoted)

| Signal | Meaning |
|--------|---------|
| `G_IDLER` → `CFrontEndIdler` | **frontend / lobby** — even if `G_GAMESTATE` live |
| `G_IDLER` → `CInGameIdler` | **in_game / map** — unlock Post-path + army scans |
| `G_IDLER` null | menu / unloaded |

Do **not** treat `CCurrentGameState` alone as in-campaign (2f counterexample).

### CLI

```text
python clausewitz_win.py status          # stderr banner if LOAD_CAMPAIGN_MAP
python clausewitz_win.py session-probe   # exit 3 frontend, 0 in_game
python scripts/phase2g_session_postpath.py [--heap] [--out research/re-dumps/phase2g.json]
```

When frontend: scanners record the known Application-setter dead end and exit 3.
When in-game: resolve `idler+0x530` RTTI + vt+`0x90` **READ-ONLY**; optional heap army counts; try player-country `CArmy*` arrays for `divisions_count` (hypothesis only until second sample).
`FN_CMD_QUEUE_POST` stays **null**; posting **DISABLED**.

### USER ACTION

Agent path: `python scripts/phase2n_cmd_heap_hunt.py [--live]  # full-heap CCommand owners; no writes
python scripts/launch_into_map.py` (paused HAI). Avoid old saves / `-hands_off` for long RE. Then `status` / `phase2g_session_postpath.py` once (no `--heap` by default).


﻿## Phase 2h — map reached (paused Haiti 1.19.4) + armies promoted

### How we got onto the map (no user click)

| Attempt | Result |
|---------|--------|
| `-start_save=POL_1943_04_01_03` | **Failed** — save incompatible with 1.19.4; stayed FrontEnd |
| `-hands_off` | **Map OK** but forced **max speed** (CPU delta ~25/3s; fans) — do not leave running |
| Space / `-` hotkeys while hands_off | Did **not** stick (still fast) |
| `-start_tag=HAI -start_speed=0 -noai` | **Map OK**, cool (CPU delta ~2/3s) — **preferred for RE** |

Tool: `python scripts/launch_into_map.py` (default = paused Haiti). Avoid `-hands_off` for long sessions.

### In-game Post-path (READ-ONLY) — still DISABLED

| Step | Result |
|------|--------|
| `G_IDLER` | **`CInGameIdler`** (`0x29e5838`) — session gate proven |
| Idler+`0x530` | Still **`CGameApplication`** (`0x2796308`) |
| App vt+`0x90` | `0x1b14f0` setter — **REJECT as Post** (frontend **and** in-game) |
| `FN_CMD_QUEUE_POST` | **null** — `+0x530` queue hypothesis **dead**; need new lead |
| command_queue | **DISABLED** |

### Armies — promoted

| Field | Value |
|-------|-------|
| Country+`0x290` | **`CPdxArray<CArmy*>`** — first_rtti `.?AVCArmy@@` |
| Sizes seen | 17 (paused HAI), 17→50 (hands_off while simming) |
| status | `campaign.armies_count` via `probe_player_armies` |
| divisions_count | **promoted in 2i** — see below |
| Country+`0x1b8` | `CReferencedDivisionTemplate*` array (live) |

### RE throttle

- Prefer paused game (`-start_speed=0` / Space).
- Do **not** default to `phase2g --heap` / full-heap scans; batch light probes; pause between heavy work.
- `phase2f` full-heap can hang — use `--skip-heap` or kill if stuck.

### Next proof steps (still read-only)

1. Find real command-queue object (not App at `+0x530`) — scan InGameIdler other fields / CCommand soft-call graph.
2. Characterize a callee that takes `CCommand*` and enqueues — only then set `FN_CMD_QUEUE_POST`.
3. ~~Walk `CArmy` → units~~ — nested empty; CArmy itself is division-level (2i).
4. Keep posting **DISABLED** until independent proof.



## Phase 2i — Post hunt dead-ends + divisions_count from CArmy markers

Live: paused Haiti (`-start_tag=HAI -start_speed=0 -noai`), pid cool (CPU Δ ~2s/3s). Tool: `scripts/phase2h_light_post_army.py` (no `--heap`).

### FN_CMD_QUEUE_POST — still null (posting DISABLED)

| Probe | Result |
|-------|--------|
| Idler+`0x530` | **REJECTED** (still `CGameApplication` / setter `0x1b14f0`) |
| Idler typed fields `0..0x900` | UI/gfx only (`CFixedWindow`, `CTextBox`, `CGameGui`, `CPdxMouse`, …) — **no** Command/Queue |
| Idler vt `0x78`/`0x80`/`0x88` | Also forward via `+0x530` |
| Idler+`0x6b8` | Untyped ptr (vt slot `0xb8` getter) — not a queue |
| `CGameApplication+0x380` | `CSession` — typed child **`CDummyServer` only**; no Command* arrays in `0..0x800` |
| GS / idler Command* arrays | **none** |
| RTTI `CCommandQueue` | **absent**; `QueueCommand` ASCII = `C*IndustrialOrgTrait*QueueCommand` subclasses |
| `FN_CMD_QUEUE_POST` | **null** |

Next (still RO, not promoted): soft-call / callee graph around `CCommand` virtuals — do **not** enable writes.

### divisions_count — enriched (no heavy heap)

| Evidence | Value |
|----------|-------|
| Country+`0x290` | `CPdxArray<CArmy*>` size **17** (paused HAI) |
| Nested unit arrays inside CArmy | **empty** (sampled) |
| CArmy+`0x138` | `CSubUnitDefinition*` — **17/17** |
| CArmy+`0x1f0` | `CProvince*` — **17/17** |
| CArmy+`0x3b8` | `CReferencedDivisionTemplate*` — **17/17** |
| status | `campaign.divisions_count := armies_count` when all sampled armies carry the three markers |

Windows `CArmy` is the division-level unit object (name ≠ Linux army-group). `probe_player_armies` fills both counts.

### RE throttle (unchanged)

Paused / 1x only; no default full-heap; posting **DISABLED**.



## Phase 2j — CCommand Execute/soft-call graph + fleets/templates

Tool: `python scripts/phase2j_cmd_execute_graph.py --live` (no full-heap). Live paused HAI.

### FN_CMD_QUEUE_POST — still null (posting DISABLED)

| Probe | Result |
|-------|--------|
| Soft E8 near `CCommand` LEAs | Top `0x25a009c` / `0x25a00d8` / `0x25c7c74` — destroy/refcount/CRT helpers, **not** Post |
| Soft E8 near Execute-like `call [reg+slot]` | Top `0x12ad90` / `0x1db710` — small SSO/string-growth helpers (`new_like`), **not** Post |
| `COrderExecuteCommand` vs `CCommand` | Many overrides; callees include **type-id registry** path `0x2284800` → `0x2282810` via global `0x34ffbf0` (live untyped hash map) — factory/lookup, **not** enqueue |
| `CCommandHelper<T>` RTTI | Present; **no** recoverable vtables (static helpers only) |
| `CConsoleCmdManager` / mangled `?Post@` | **Absent** |
| Live globals near GS/IDLER | `0x33dd090`=`CFileLogger`; `0x33ddb10` duplicate `CInGameIdler`; no Command* arrays on GS |
| Prior dead-ends | Still hold: idler+`0x530` App, `CSession`=`CDummyServer`, no `CCommandQueue` |

**Do not promote** multi-hit soft helpers or the type-id registry as `FN_CMD_QUEUE_POST`.

### Newly proven status fields

| Field | Source | Sample (paused HAI) |
|-------|--------|---------------------|
| `fleets_count` | Country+`0x278` `CFleet*` | 3 |
| `div_templates_count` | Country+`0x1b8` `CReferencedDivisionTemplate*` | 4 |
| `divisions_count` | (2i) CArmy markers | 17 |

### Next (still RO)

1. Find a callee that **stores** a live `CCommand*` into a container (not type-id lookup).
2. Or recover non-RTTI queue object via a single-player command path (e.g. pause) under a debugger — out of scope for RPM light probes.
3. Keep posting **DISABLED**.




## Phase 2k — store/2-hop Execute graph + theatres/states

Tool: `python scripts/phase2k_cmd_store_graph.py --live` (no full-heap). Live paused HAI (+ light major sweeps).

### FN_CMD_QUEUE_POST — still null (posting DISABLED)

| Probe | Result |
|-------|--------|
| 2-hop soft from CCommand LEAs | Hop1 tops still destroy/refcount (`0x25a00d8`/`0x25a009c`); new mid-hits characterized; **not** Post |
| Store-near-LEA / store+context soft fns | 10 candidates documented (field stores + calls/vt) — **unproven**; several call type-id registry `0x2284800` or bad-disasm outsides |
| OEC override deep | Slot `0x48`/`0x50` hit registry + helpers; no container enqueue of live `CCommand*` |
| `Failed to execute` LEAs | Near string/CRT helpers (`0x254aa00` …) — **not** Post |
| Idler Command* arrays | **none** |
| Managerish RTTI | Still only `*IndustrialOrgTrait*QueueCommand` / `CCommandHelper` |
| Prior dead-ends | Hold: idler+`0x530`, `CDummyServer`, no `CCommandQueue`, type-id registry ≠ queue |

**Do not promote** store+context soft helpers as `FN_CMD_QUEUE_POST`.

### Newly proven status fields

| Field | Source | Sample (paused HAI) |
|-------|--------|---------------------|
| `theatres_count` | Country+`0x168` `CTheatre*` | 1 (also 1 on sampled majors) |
| `states_count` | Country+`0x460` `CState*` | 26 (majors vary; twin@`0x478` same size peacetime — left unpromoted) |

Air wings / characters: RTTI present (`CAirWing`, `CCharacter`, `CUnitLeader`) but **no** typed ptr array in country `0x100..0x480` on HAI or 3 majors — not promoted.

### Next (still RO)

1. Narrow any single store-candidate with a live before/after command under debugger (out of RPM-light scope).
2. Hunt air/character containers outside country object or via nested theatre.
3. Keep posting **DISABLED**.




## Phase 2l — theatre nest + Chat/Ping LEAs + candidate globals

Tool: `python scripts/phase2l_post_leads.py --live`. Live paused HAI.

### FN_CMD_QUEUE_POST — still null (posting DISABLED)

| Probe | Result |
|-------|--------|
| Priority store cands (2k) re-filtered | `0x1f7640`→SSO `0x2607890`; `0xddcff0`→registry; others ctor/destroy — **not** Post |
| RIP `0x33dea38` (cand `0x6b8880`) | Live **untyped** ptr — not queue |
| `CClientPingCommand` / `CChatCommand` LEA softs | SSO/ctor/destroy tops — **not** Post |
| Theatre nest / country extra | Fronts/armies/areas/modifiers — **no** `Command*` arrays |
| Air / Character arrays | Still absent on country & theatre (HAI + major0) |

### Newly proven status fields

| Field | Source | Sample (paused HAI) |
|-------|--------|---------------------|
| `fronts_count` | primary `CTheatre`+`0x50` `CFront*` | 6 |
| `controller_areas_count` | Country+`0x548` `CControllerArea*` | 9 |
| `owner_areas_count` | Country+`0x560` `COwnerArea*` | 9 |
| `modifiers_count` | Country+`0x5D0` `CModifier*` | 36 |

`CTheatre`+`0x68` `CArmy*` size matches `CO_ARMIES` (not double-counted in status).

### Next (still RO)

1. Air/character containers likely off country object — try equipment DB / GS-level (light, bounded).
2. Keep posting **DISABLED**.




## Phase 2m — idler/App/GS vtable Post-slot hyps + GS air/character managers

Tool: `python scripts/phase2m_vt_post_slots.py --live` (+ manager sweep). Live paused HAI.

### FN_CMD_QUEUE_POST — still null (posting DISABLED)

| Probe | Result |
|-------|--------|
| Idler/App/GS/CGS vtable slot scoring | Interesting slots found; **none** independently proven as Post |
| Idler slots `0x78`/`0x80`/`0x88` | Still load `[this+0x530]` → App — **REJECTED** |
| GS vt `0x78` / CGS vt `0x0` | Soft `0x6b8880` + RIP `G_IDLER` — not typed queue |
| Entity LEAs (`CCharacter`/`CUnitLeader`/`CEquipmentVariant`) | Soft tops SSO/registry/destroy — **not** Post |
| `CAirWing` LEA | Not found in image |

### Newly proven status fields

| Field | Source | Sample (paused HAI world) |
|-------|--------|---------------------------|
| `strategic_air_manager` | GS+`0x690` `CStrategicAirManager*` | live RTTI |
| `strategic_airs_count` | SAM+`0x30` `CStrategicAir*` | 440 |
| `air_bases_count` | SAM+`0x90` `CAirBase*` | 1082 |
| `character_manager` | GS+`0x6a8` `CCharacterManager*` | live RTTI |
| `characters_count` | CM+`0x10` `CCharacter*` | 9661 |
| `characters_active_count` | CM+`0x28` `CCharacter*` | 2361 (role TBD) |

SAM+`0xd8` also `CAirBase*` (size 14) — not promoted to status (role unproven).

### Next (still RO)

1. Country-scoped air wings / leaders (filter world arrays by tag) — light, bounded.
2. Keep posting **DISABLED**.




## Phase 2n — full-heap CCommand owners + ctor-caller softs

Tools: `python scripts/phase2n_cmd_heap_hunt.py --live` (+ detail/static/ctor-caller follow-ups).
Live paused HAI. Full-heap allowed (t37u); game kept paused/1x.

### FN_CMD_QUEUE_POST — still null (posting DISABLED)

| Probe | Result |
|-------|--------|
| RTTI `*Queue*` / `*Command*` catalog | 166 names; **no** `CCommandQueue`. Queueish = industrial/naval/speech/UI only |
| Heap vptr `CCommand` | **27** live base instances (clustered free-list-like); **0** live subclass instances while paused |
| Backrefs to sample `CCommand*` | No `CPdxArray` owner; owner hyps mostly untyped / `CModifier` noise |
| Subclass vtables resolved | `CSetGameSpeed`/`Increase`/`Decrease`/`HourlyTick`/`Chat`/`Ping`/… |
| Vtable diffs vs `CCommand` | Slot `0x48` commonly overridden (Execute-shaped); shared stub `0x188d90` |
| Ctor LEA softs | Tops still `0x25a009c` / `0x25a00d8` (prior SSO/destroy) |
| Ctor **caller** softs (new) | Shared non-dead hyps: `0x25c3770`, `0x22c41e0`, `0x254aa00`, `0x25a0390`, `0x216e50` — **unproven**, not promoted |

### Status fields

No new status offsets this slice (air/character already in 2m).

### Next (still RO)

1. Disasm/prove or reject ctor-caller hyps `0x254aa00` / `0x22c41e0` / `0x25c3770` independently.
2. Optional: catch a live subclass vptr by observing a UI speed toggle at **1x** (never 5x) without writing from tooling.
3. Keep posting **DISABLED**.




## Phase 2o — string/soft Post hunt + session post gate (read-only)

Session: paused/in-game `CInGameIdler` (pid 31364, HAI). **Never 5x.** Posting **DISABLED**.

### Works

| Item | Result |
|------|--------|
| String LEA + nearby E8 catalog | `scripts/phase2o_string_hunt.py` → `research/re-dumps/phase2o_strings.json` |
| 2n ctor-caller hyp dig | `0x254aa00` fmt; `0x25a0390` getter; `0xbbb080` registry; `0x25c3770` untyped — **not Post** |
| AI post wrappers | `0x2b5f10` / `0x2b6050` / `0x2b80c0` — strings *IsCommandsAllowed* / *post AI command* / *invalid command* |
| **App+`0x380`** | **`CSession*`** (live RTTI) |
| **Idler vt+`0x88`** | Forwards via `+0x530` → **App vt+`0x88`** = getter `[App+0x380]` → `CSession*` |
| **Session post gate hyp** | RVA **`0x22c41e0`** — 625 E8 callers; drop strings *Dropped command* / *posted during command execution* / *sender not authorized* |
| Gate success sink | `server = [session+0x40]`; **`call [server.vt+0x28](cmd)`** — live `CDummyServer`, method **`0x23f5cd0`** |

### Stubbed / not promoted

| Item | Status |
|------|--------|
| `FN_CMD_QUEUE_POST` | **null** — gate+sink call chain is strong, but **enqueue write** into a typed queue is not yet proven (`CDummyServer` may execute-in-place) |
| Posting | **DISABLED** |
| `RunCommandQueue` string | SDL/GL render — dead |
| `Failed to post order!` | Military *order* path — not CCommand queue |
| `posted_commands` | Telemetry field name |

### Proven struct (safe to cite; not a Post RVA)

| Symbol | Value |
|--------|-------|
| `CGameApplication_SESSION` | `+0x380` → `CSession*` |
| `CGameApplication_vt88_session_getter` | `0x17f880` |
| `CSession_SERVER` | `+0x40` → `CServer*` (`CDummyServer` in SP) |
| `CInGameIdler_vt88_session_forward` | `0xb8e390` |
| `HYP_SESSION_POST_GATE` | `0x22c41e0` (hyp only) |
| `HYP_DUMMYSERVER_VT28_SINK` | `0x23f5cd0` (hyp only) |

### Next (still RO)

1. Prove `CDummyServer`/`CServer` vt+`0x28` either enqueues into a typed buffer or executes in-place (disasm `0x23f5cd0` callees `0x22d8ad0` / `0x6d01e0`).
2. If a real queue buffer is found, only then set `FN_CMD_QUEUE_POST` (likely the gate `0x22c41e0` or the server method).
3. Keep posting **DISABLED**; game pause/1x only.

Tools: `scripts/phase2o_post_hyps.py`, `scripts/phase2o_string_hunt.py`.



## Phase 2p — CDummyServer enqueue PROVEN (writes still DISABLED)

Capstone disasm of live SP sink `CDummyServer` vt+`0x28` @ **`0x23f5cd0`**.

### Proof chain

1. AI/UI → **`0x22c41e0(session, cmd)`** (drop strings + auth; 625 E8 callers).
2. Success: `server=[session+0x40]`; **`call [server.vt+0x28](cmd)`**.
3. Live server = `CDummyServer`; method **`0x23f5cd0`**.
4. Inside sink: null-check cmd; stamp token from `[server+0x18]` session; `lock xadd [server+0xd0]`.
5. Fan-out loop over **`G_POST_LISTENERS` `0x3667be8`** / count **`0x3667bf4`** (live count=1 → DummyServer self).
6. Per listener **`+0xa0` ring**: spinlock dword`[rbx]`; optional grow **`0x6d01e0`**; **`mov [rcx+r13*8], rax` @ `0x23f5ec6`** — **enqueue write**; `inc [rbx+0x28]`; unlock.
7. Then `call cmd.vt+0` with `edx=1` (release after fan-out).

### Promoted

| Symbol | RVA / off | Notes |
|--------|-----------|-------|
| **`FN_CMD_QUEUE_POST`** | **`0x22c41e0`** | Session gate (public Post entry) |
| `FN_CMD_QUEUE_POST_SINK_DUMMY` | `0x23f5cd0` | SP enqueue sink |
| `G_POST_LISTENERS` | `0x3667be8` | Listener ptr array |
| `G_POST_LISTENER_COUNT` | `0x3667bf4` | |

### Still DISABLED

Tooling **must not call** Post / must not write memory to enqueue. `command_queue=DISABLED` until an explicit write-enable step. Game **pause or 1x only**.

### Compare

| Class | vt+`0x28` | Role |
|-------|-----------|------|
| CDummyServer | `0x23f5cd0` | SP enqueue — **proven** |
| CServer | `0x25c21e0` | abort/stub |
| CNetworkServer | `0x23fa830` | MP path (not live) |



## Phase 2q — DummyServer drain / clear path (read-only)

After Post enqueue (2p), SP `CDummyServer` pipeline:

| Slot | RVA | Role |
|------|-----|------|
| vt+`0x28` | `0x23f5cd0` | **Post/enqueue** into `this+0xa0` ring |
| vt+`0x30` | `0x23f64e0` | **Drain**: pop ring → `token.vt+0x68` clone → link at `this+0x58`/`+0x60` |
| vt+`0x48` | `0x23f5ad0` | **Clear**: destroy pending list (`0x23f5bf0`) + discard ring |

Ring layout (`CDummyServer+0xa0`): lock dword, growable ptr buffer, capacity, indices (`+0x28` count).

`CCommand` **IsValid** is subclass vt+`0x48`; **Execute** is vt+`0x50` (base both abort `0x25c21e0`). Tick **pinned in Phase 2r** (`0x22c6410` / `0x22c4710`). *(2q text originally mislabeled +0x48 as Execute.)*

Writes/posting remain **DISABLED**. pause/1x only.

## Phase 2r — Execute tick PINNED (writes still DISABLED)

Read-only Capstone + live counters on paused HAI (`CInGameIdler`, session state+`0x30`=`2`).

### Corrected CCommand slots

| Slot | Role | Notes |
|------|------|-------|
| vt+`0x48` | **IsValid** | via wrap `0x22d8ea0`; base abort `0x25c21e0` |
| vt+`0x50` | **Execute** | site A `0x22c6c9d`, site B `0x22c47dd`; base abort |
| vt+`0x58` | post-Execute | base abort |

*(Phase 2q wrongly called vt+`0x48` Execute.)*

### SP state==2 pipeline

1. `FN_SESSION_UPDATE` **`0x22c6410`**
2. `server = [session+0x40]` live `CDummyServer` vt `0x2bcb040`
3. `server.vt+0x30` **`0x23f64e0`** drain ring `+0xa0` → list `+0x58`/`+0x60` count `+0x68`
4. `server.vt+0x40` **`0x2e9e50`** = `&this+0x58` (pending header)
5. Stage into `session+0x48` (count `session+0x54`)
6. Per cmd: IsValid `0x22d8ea0` → fail path `"Discarding command: "` xref **`0x22c6e31`**
7. Execute site A **`0x22c6c9d`**: `cmd.vt+0x50`; `inc session+0x6c8`; `cmd.vt+0x58`
8. `FN_EXECUTE_LOOP` **`0x22c4710`**: via `server.vt+0x78` **`0x247620`** = `&this+0x40` (exec-list); Execute site B **`0x22c47dd`**

### Server list headers

| Off | Getter | Role |
|-----|--------|------|
| `+0x58` | vt+`0x40` @ `0x2e9e50` | drain-pending |
| `+0x40` | vt+`0x78` @ `0x247620` | exec-list |

### Live proof (pid 31364, paused)

- `session+0x60` drain counter ≈ 327700
- `session+0x6c8` exec counter = 13
- both list heads `0` while paused (queues drained)

### Still DISABLED

`command_queue=DISABLED`. Do **not** call `FN_CMD_QUEUE_POST` / do **not** write enqueue. Game **pause or 1x only** (never 5x).

Tool: `scripts/phase2r_execute_tick.py [--live]`

## Phase 2s — drain-list vs exe-list; Execute catalog (writes still DISABLED)

### Two server command lists

| Off | Shape | Filled by | Consumed by |
|-----|-------|-----------|-------------|
| **`+0x58`** | linked list head/tail/count (`+0x60`/`+0x68`) | Dummy drain `0x23f64e0` **and** Network drain `0x23fb470` | `FN_SESSION_UPDATE` stage → `session+0x48` → Execute site A `0x22c6c9d` |
| **`+0x40`** | secondary channel (head ptr) | **UNPINNED** | `FN_EXECUTE_LOOP` `0x22c4710` → Execute site B `0x22c47dd` |

Getters are **shared lea thunks**: vt+`0x40` → `0x2e9e50` (`&this+0x58`); vt+`0x78` → `0x247620` (`&this+0x40`). E8 callers of those RVAs are not DummyServer-specific.

SP paused HAI: `+0x40` and `+0x58` both empty; drain counter climbs; exec counter=13. **SP army path = `+0x58` staging**, not `+0x40`.

### Post-during-Execute

`session+0x6cc` set around Execute. `FN_CMD_QUEUE_POST` sees it and **drops** (`"Dropped (posted during command execution)"` LEA `0x22c4371`) — does **not** defer into `+0x40`.

### CCommand Execute catalog (vt+`0x50` ≠ abort `0x25c21e0`)

- ~382 Command RTTI with real Execute; **174** army/unit/naval/air/order-ish names
- Examples: `CMoveCommand` Exec `0x13fc990`; `CCancelMovementCommand` `0x13fbbd0`; `COrderExecuteCommand` `0x18d6430`; `CChatCommand` `0x13caee0`

### NetworkServer slots (not live in SP)

| Slot | RVA |
|------|-----|
| vt+`0x28` Post | `0x23fa830` |
| vt+`0x30` Drain | `0x23fb470` (fills `+0x58` only, same shape as Dummy) |
| vt+`0x48` Clear | `0x23f79f0` |

### Still DISABLED

No Post calls / no enqueue writes. pause or 1x only (never 5x).

Tools: `scripts/phase2s_execlist_fill.py [--live]`, `scripts/phase2s_network.py` (army catalog dump).

## Phase 2t — CMoveCommand→CUnitMoveAction; session post-exec list (writes DISABLED)

### CMoveCommand (army move)

| Item | Value |
|------|-------|
| vt | `0x2a2c790` |
| size | `0x88` (factory `0x13fb000`; **2w corrects** prior `0x58` mislabel) |
| IsValid vt+`0x48` | thunk `0x14002f0` → **`CUnitMoveAction.vt+0x50`** `0x12c2ca0` |
| Execute vt+`0x50` | thunk `0x13fc990` → **`CUnitMoveAction.vt+0x48`** `0x12c2670` |
| embedded @`+0x28` | `.?AVCUnitMoveAction@@` vt `0x2a1f648`; sub-ctor `0x12c1770`; type-id `+8=0x3648` |

Ctor LEA-vt sites: `0x13f6bef`, `0x13f939c`, `0x13fb039`.

### Session staging (from drain-pending)

| Off | Role |
|-----|------|
| `+0x48` | `CCommand*` array |
| `+0x50` | capacity |
| `+0x54` | count |

### Session post-Execute list (NOT server+`0x40`)

After Execute, if `cmd.vt+0x60` and flags allow: clone via `cmd.vt+0x68`, link **`session+0xf8`/`+0x100`/`+0x108`** (0x20 nodes). Server `+0x40` filler remains **UNPINNED**.

### Still DISABLED

Posting off. pause/1x only.

Tool: `scripts/phase2t_move_staging.py [--live]`

## Phase 2u — server+0x40 execlist filler PINNED (writes DISABLED)

### Rule

On **NetworkServer** post insert (`0x23fa510`):

| `cmd+0x1a` | List |
|------------|------|
| `== 0` | drain-pending `+0x58` / tail `+0x60` / count `+0x68` |
| `!= 0` | **execlist** `+0x40` / tail `+0x48` / count `+0x50` |

Same 0x20 node shape (`cmd@[0]`, `next@[0x10]`).

**CDummyServer** drain `0x23f64e0` fills **`+0x58` only** (no `+0x1a` branch) — SP sessions normally leave `+0x40` empty; `FN_EXECUTE_LOOP` still walks it when non-empty.

`cmd+0x1a` also gates session post-exec clone list (`session+0xf8`).

### Still DISABLED

Posting off. pause/1x only.

Tool: `scripts/phase2u_plus40_fill.py [--live]`

## Phase 2v — FN_CMD_QUEUE_POST drop gates + delivery; CCancelMovement (writes DISABLED)

### Delivery (success)

`FN_CMD_QUEUE_POST` (`0x22c41e0`) → stamps `cmd+0xc` / `cmd+0x18` → **`call [server.vt+0x28](cmd)`** at `0x22c46a0` (`server = session+0x40`). Dummy sink = `0x23f5cd0` → ring → drain → `+0x58`.

### Drop gates (log strings in binary)

| Log | Condition |
|-----|-----------|
| `Dropped command:` | early `cmd.vt+0x80` / `vt+0x60` when `r8b==0` and `session+0x725==0` |
| `Dropped (posted during command execution):` | `session+0x6cc!=0` (and related flags) |
| `Dropped (sender not authorized):` | `cmd.vt+0x90` auth fails |

### CCancelMovement

| Item | Value |
|------|-------|
| vt | `0x2a2c9b8` |
| size | `0x48` |
| IsValid / Execute | `0x13fed40` / `0x13fbbd0` |

### Safe-enable checklist — NOT DONE

Posting remains **DISABLED** until independent paused-SP proof. Checklist only in `phase2v_post_gates.py` report.

Tool: `scripts/phase2v_post_gates.py [--live]`

## Phase 2w — CMoveCommand size 0x88 field map; CChatCommand (writes DISABLED)

### Correction

**CMoveCommand size = `0x88`** (factory `0x13fb000` → `CUnitMoveAction` sub_ctor `0x12c1770` at `+0x28`). The `0x58` factory nearby is a different object; 2t mislabeled.

### CCommand base (common)

| Off | Role |
|-----|------|
| `+8` | flag |
| `+0xc` | tick (Post stamps from session+`0x84`) |
| `+0x18` | word (Post stamps) |
| `+0x1a` | execlist select (see 2u) |
| `+0x1c` | sink seq |

### CUnitMoveAction `@ cmd+0x28`

| Off | Role |
|-----|------|
| `+8` | type-id `0x3648` |
| `+0x10` | unit/handle |
| `+0x18`, `+0x30` | vectors (path / unit ids) |
| `+0x58` | dword `1` default |

### CChatCommand

vt `0x2a27f28`, size `0x98`, Execute `0x13caee0` — noted as future simpler candidate; **not enabled**.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2w_fieldmap.py [--live]`

## Phase 2x — Chat fields; Move early-drop gate; OEC (writes DISABLED)

### Critical: Move early-drop

`FN_CMD_QUEUE_POST` when `r8b==0` and `session+0x725==0` requires `cmd.vt+0x80` **or** `vt+0x60` true. **CMoveCommand** both stub to `0x11d530` (`xor al,al; ret`) → **always** `"Dropped command:"` unless caller passes `r8b=1` or `session+0x725!=0`.

### CChatCommand fields (size `0x98`, factory `0x13ca430`)

| Off | Role |
|-----|------|
| `+0x28` | SSO message string |
| `+0x48` | vector-like |
| `+0x60` | byte |
| `+0x64` | country/player (`-1` default) |
| `+0x78` | SSO string |

### COrderExecuteCommand

vt `0x2a85468`, Execute `0x18d6430`.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2x_chat_auth.py [--live]`

## Phase 2y — full-heap scan for live commands (writes DISABLED)

Writable scan (~7.6 GiB): **0** live `CMoveCommand` / `CChatCommand` / `CUnitMoveAction`; **1** `CDummyServer` (matches `session+0x40`).

Paused SP destroys commands after Execute — mid-flight capture needs brief 1x with player activity (never 5x). `session+0x725==1` on this save bypasses Move early-drop.

Posting **DISABLED**.

Tool: `scripts/phase2y_heap_scan.py [--live]`

## Phase 2z — CStartGameCommand live post-exec; early-gate TRUE (writes DISABLED)

Sticky `session+0xf8` node while paused: **`.?AVCStartGameCommand@@`**

| Item | Value |
|------|-------|
| vt | `0x2a5f448` |
| size | `0x28` |
| Execute | `0x16de180` |
| `vt+0x60` / `+0x80` | `0x188d90` (`mov al,1; ret`) **TRUE** |
| contrast | `CMoveCommand` uses `0x11d530` (`xor al,al; ret`) **FALSE** |

Explains sticky post-exec list (`vt+0x60` also gates clone after Execute). Live sample: tick `+0xc=1`, seq `+0x1c=14`, `+0x1a=0`.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2z_startgame.py [--live]`

## Phase 2aa — CCommand early-gate catalog (writes DISABLED)

| Command | vt+0x60 | vt+0x80 | notes |
|---------|---------|---------|-------|
| CMoveCommand | FALSE | FALSE | needs session+0x725 or r8b |
| CCancelMovementCommand | FALSE | FALSE | |
| COrderExecuteCommand | FALSE | FALSE | |
| CChatCommand | FALSE | TRUE | mixed |
| CStartGameCommand | TRUE | TRUE | sticky post-exec |
| C*GameSpeed* / HourlyTick | FALSE | TRUE | **NEVER Post** (5x ban) |

Live `session+0x725==1` bypasses FALSE `vt+0x60` in Post. Stub TRUE=`0x188d90`, FALSE=`0x11d530`.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2aa_early_gates.py [--live]`

## Phase 2ab — Post early-gate order pinned (writes DISABLED)

`FN_CMD_QUEUE_POST` (`0x22c41e0`) early path — bypass stamp/delivery if **any**:

1. `r8b != 0` (caller force)
2. `session+0x725 != 0` (live **1**)
3. `cmd.vt+0x80` returns TRUE
4. `cmd.vt+0x60` returns TRUE

Else DROP `"Dropped command:"`.

After bypass: stamp `cmd+0xc=session+0x84`, `cmd+0x18=min(session+0x60,0x7fff)`; if `+0x6cc && !+0x726` DROP during-exec; auth may DROP `"sender not authorized"`; success → `server.vt+0x28(cmd)`.

`+0x725` writers set 1 via Idler→App `vt+0x88` session getter. Chat `vt+0x90` (`0x13cc9a0`) multi-path; `mov al,1` @ `0x13ccc20`.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2ab_post_gates.py [--live]`

## Phase 2ac — DummyServer Post destroys; Execute list empty (writes DISABLED)

Live server is **`.?AVCDummyServer@@`** (`vt 0x2bcb040`).

| Slot | RVA | Role |
|------|-----|------|
| `vt+0x28` Post | `0x23f5cd0` | stamp seq `+0xd0`; worker-ring log; **`cmd.vt+0(edx=1)` destroy** |
| `vt+0x30` drain | `0x23f64e0` | pops `server+0xc8` |
| `vt+0x78` | `0x247620` | `lea rax,[rcx+0x40]; ret` — Execute list head |

`FN_EXECUTE_LOOP` (`0x22c4710`) walks `*[server.vt+0x78()]` i.e. `server+0x40`. Live heads `+0x40/+0x58/+0xc8` are **0**; `exec` stuck at 13.

`CNetworkServer` (`vt 0x2bcb330`, Post `0x23fa830`, insert `0x23fa510`) inserts by `cmd+0x1a` into `+0x40` or `+0x58` — **not live in SP**.

Auth: live `session+0x3c==1` skips `vt+0x90`.

### Safe-enable checklist (NOT enabled)

1. Do **not** Post via live DummyServer (destroy, no Execute).
2. Need NetworkServer or equivalent insert into `server+0x40/+0x58`.
3. Prove Execute increments on that cmd before enabling queue.
4. Never Post speed cmds. pause/1x only.

Posting **DISABLED**.

Tool: `scripts/phase2ac_dummy_execute.py [--live]`

## Phase 2ad — SP pipeline: ring → +0x58 → Execute (writes DISABLED)

**Correction to 2ac:** live `worker0 == CDummyServer`. Post writes the **server ring** (`+0xa0` lock, `+0xb0` data, `+0xc8` count) via serialize→`FN_RING_RECREATE` (`0x22d8ad0`), then **destroys** the original cmd.

| Step | Mechanism |
|------|-----------|
| Post | serialize + recreate into ring; destroy original |
| Drain `vt+0x30` | pop ring → `cmd.vt+0x68` Clone → list **`server+0x58`** |
| Pending getter `vt+0x40` | `lea rax,[rcx+0x58]` |
| Session state=2 | stage into `session+0x48`; **`cmd.vt+0x50` @ `0x22c6c9d`** |
| Exec list `vt+0x78` | `lea rax,[rcx+0x40]` (state4 / ExecuteLoop) |

Safe-enable still **NOT** proven: hand-built objects must survive serialize/recreate. Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2ad_sp_pipeline.py [--live]`

## Phase 2ae — Command type ids + shared serialize slots (writes DISABLED)

| Command | `vt+0x58` type id |
|---------|-------------------|
| CMoveCommand | `0x28a2` |
| CCancelMovementCommand | `0x28af` |
| CChatCommand | `0x184` |
| CStartGameCommand | `0x359e` |

Shared header serialize: `vt+0x10` write `0x22d9390` / `vt+0x20` read `0x22d90f0` (tags `0x1f3` header, `0x41` payload). Write then calls `vt+0xa0` for subclass payload (Move → CUnitMoveAction fields).

Mid-flight poll: ring/lists empty; `exec=13` sticky; no UI cmds observed.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2ae_typeids.py [--live]`

## Phase 2af — CUnitMoveAction serialize + Dummy Post ring feed (writes DISABLED)

`CMoveCommand` (`vt 0x2a2c790`, size `0x88`, factory `0x13fb000`) embeds `CUnitMoveAction` at `+0x28` (ctor `0x12c1770`, **vt `0x2a1f648`**).

| Slot | RVA | Role |
|------|-----|------|
| Move `vt+0xa0` | `0x1404590` | thunk → `[this+0x28].vt+0xc0` |
| Action `vt+0xc0` | `0x12c3920` | payload serialize (tag `0x28a3` handle `+0x10`; tag `0x2840` vec `+0x18`) |
| Action `vt+0x48` | `0x12c2670` | Execute |
| Action `vt+0x50` | `0x12c2ca0` | IsValid |

DummyServer `Post 0x23f5cd0` → helper `0x22d8ad0` (typeid factory table `0x22d8d20`) recreates cmd from bitstream → push into listener ring `server+0xa0` → destroy original. **Can feed Execute** if serialize ok (corrects pure-destroy reading).

Posting **DISABLED**. pause/1x only (live: tick stuck, drain idler — `-start_speed=0`).

Tool: `scripts/phase2af_move_payload.py [--live]`

## Phase 2ag — Typeid→factory table + CUnitMoveAction serialize fields (writes DISABLED)

Factory lookup `0x22d8d20`: if `tid >= 0x2710` then `tid - 0x2328`; index max `0x2af7`; table **`0x35011e0`**.

| Type id | Factory | Size |
|---------|---------|------|
| Move `0x28a2` | `0x13fb000` | `0x88` |
| Cancel `0x28af` | `0x13face0` | `0x48` |
| Chat `0x184` | `0x13ca430` | `0x98` |
| StartGame `0x359e` | `0x16dd5a0` | `0x28` |

`CUnitMoveAction` serialize `0x12c3920` (`vt+0xc0`):

| Off | Tag | Kind |
|-----|-----|------|
| `+0x10` | `0x28a3` | handle (always) |
| `+0x18` / cnt `+0x24` | `0x2840` | vector if cnt>0 |
| `+0x30` / cnt `+0x3c` | `0x174` | vector if cnt>0 |
| `+0x50` | `0x29f1` | byte if nz |
| `+0x51` | `0x2c84` | byte if nz |
| `+0x53` | `0x38f1` | byte if nz |
| `+0x52` | `0x3a98` | byte if nz |
| `+0x55` | `0x2c85` | byte if nz |
| `+0x58` | `0x37bc` | dword if !=1 |
| `+0x5c` | `0x368f` | byte if nz |

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2ag_factory_table.py [--live]`

## Phase 2ah — Payload Read `vt+0xa8` + action deserialize (writes DISABLED)

Shared Write `0x22d9390` ends `call [rax+0xa0]`; shared Read `0x22d90f0` tag `0x41` path `call [rax+0xa8]`.

| Cmd | Write `vt+0xa0` | Read `vt+0xa8` |
|-----|-----------------|----------------|
| CMoveCommand | `0x1404590` → action `vt+0xc0` `0x12c3920` | `0x1403570` → action `vt+0xb8` `0x12c3340` |
| CCancelMovement | `0x1404130` (handles `+0x28`/`+0x34` tag `0x28a3`; byte `+0x40` tag `0x368f`) | (symmetric) |
| CChatCommand | `0x13d7fa0` (string `+0x28` tag `0xdd`) | (symmetric) |

Action deserialize `0x12c3340` is a tag-switch into the same fields as serialize (`+0x10/+0x18/+0x30/+0x50..`).

Round-trip RO chain: Write header → payload `0xa0` → Dummy Post `0x22d8ad0` recreate via factory table → Read header → payload `0xa8` → ring `server+0xa0` → drain → Execute.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2ah_deserialize.py [--live]`

## Phase 2ai — Ring drain → pending `+0x58` + heap probe (writes DISABLED)

DummyServer `vt+0x30` drain `0x23f64e0`: spinlock `server+0xa0`, pop ring, **`mov [rbx+0x58], rdx` @ `0x23f6629`** into pending list.

Pipeline: Post `vt+0x28` → serialize/recreate `0x22d8ad0` → ring `+0xa0` → drain `vt+0x30` → pending `+0x58` → stage → state2 Execute `0x22c6c9d` / loop pulls execlist `+0x40`.

Full-heap writable scan (paused SP): Move/Cancel/Chat **0**; StartGame **1** sticky (`postexec`); DummyServer **1**.

Posting **DISABLED**. pause/1x only.

Tool: `scripts/phase2ai_ring_drain.py [--live] [--heap]`

## Write gate

Command **writes** stay off until `FN_CMD_QUEUE_POST` is independently proven.  
`G_GAMESTATE` promotion enables **reads** only.

## Tools

```text
python clausewitz_win.py doctor|status|peinfo|scan|session-probe|live-gs
python scripts/phase2c_recover.py
python scripts/phase2d_post_hunt.py
python scripts/phase2e_post_graph.py
python scripts/phase2e_live_scan.py [--out research/re-dumps/phase2e_live.json]
python scripts/phase2f_idler_postpath.py [--out research/re-dumps/phase2f_idler.json] [--skip-heap]
python scripts/phase2g_session_postpath.py [--heap] [--out research/re-dumps/phase2g.json]
python scripts/session_probe.py
python scripts/phase2j_cmd_execute_graph.py [--live]  # CCommand Execute/soft-call graph; no heap
python scripts/phase2h_light_post_army.py  # RO Post hunt + army markers; no heap
python scripts/phase2r_execute_tick.py [--live]  # Execute tick pin; no writes
python scripts/phase2s_execlist_fill.py [--live]  # drain vs +0x40; army Execute catalog
python scripts/phase2t_move_staging.py [--live]  # CMoveCommand/CUnitMoveAction; post-exec list
python scripts/launch_into_map.py   # paused HAI map; avoid --hands-off
```
