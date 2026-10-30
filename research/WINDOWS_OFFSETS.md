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

## Command queue — DISABLED (Phase 2e stronger RE)

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
python scripts/launch_into_map.py   # paused HAI map; avoid --hands-off
```
