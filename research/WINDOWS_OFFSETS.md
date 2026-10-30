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
| date_year | GS+`0x478` i32 | **hypothesis** (1936); full Y-M-D TBD |
| divisions_count | — | **stubbed** (need CCountry army offset) |
| GS_PAUSE_HOURS `0x908` | Linux | **invalid** on Windows (pointer-looking) |

## Command queue — DISABLED

| Lead | Result |
|------|--------|
| `.?AVCCommandQueue@@` | Absent |
| `PostCommand` strings | 0 |
| `QueueCommand` strings | 8 (no LEA xrefs / soft call targets) |
| `FN_CMD_QUEUE_POST` | **null** — posting **DISABLED** |

See `scripts/phase2d_post_hunt.py` → `phase2d_post_hunt.json` (gitignored dumps dir). Do not invent Post. `CLAUSEWITZ_ALLOW_WRITE` does not enable posting.

## Write gate

Command **writes** stay off until `FN_CMD_QUEUE_POST` is independently proven.  
`G_GAMESTATE` promotion enables **reads** only.

## Tools

```text
python clausewitz_win.py doctor|status|peinfo|scan|session-probe|live-gs
python scripts/phase2c_recover.py
python scripts/phase2d_post_hunt.py
python scripts/session_probe.py
```
