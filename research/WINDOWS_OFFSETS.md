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
| CO_ARMIES `0x290` | Linux | **empty / not CArmy*** on Windows live majors+player this sample |

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
python scripts/session_probe.py
```
