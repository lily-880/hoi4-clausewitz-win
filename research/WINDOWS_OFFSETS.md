# Windows offset recovery — HOI4 1.19.4 PE

Target: `hoi4.exe` PE32+ · ImageBase `0x140000000` · SizeOfImage `0x38a3000`  
SHA256: `CF781ED178CD801643B233B7E3FCD1C0EFD19BD01AECD24BF07A35F69F10476F`  
Launcher: 1.19.4.1 (Operation Postern)

Upstream Clausewitz-MCP RVAs are **Linux ELF 1.19.2** — do not copy.

## Proven static (safe to cite)

| Symbol | Kind | RVA | Notes |
|--------|------|-----|-------|
| `.?AVCGameState@@` | RTTI name | `0x31e75a0` | TD `0x31e7590` |
| CGameState vtable | vftable | **`0x279f0f0`** | COL `0x2c2fa08`; live COL slot MATCH under ASLR |
| CGameState vtable (2nd) | vftable | `0x279f148` | MI secondary |
| CGameState ctor LEA sites | code | `0x1d78ae`, `0x1da5a6` | `lea reg, [CGameState::vftable]` |
| `.?AVCCurrentGameState@@` | RTTI name | `0x31e78b8` | likely heap leaf type |
| CCurrentGameState vtable | vftable | `0x279f168` | |
| `.?AVCInGameIdler@@` | RTTI | `0x32e31b0` | vtables `0x29e5838`… |
| `.?AVCGameIdler@@` | RTTI | `0x31ee078` | vtables `0x27b4158`, `0x27b4510` |
| `.?AVCCommand@@` | RTTI | `0x31e74b8` | base of `C*Command` hierarchy; vtable `0x279f4a0` |

Method: MSVC RTTI → COL (sig 0/1, typeDescriptorRva @+0x0C) → `.rdata` qword `ImageBase+COL` → vtable @ slot+8.  
Live check: `ReadProcessMemory` at `image_base+0x279f0e8` equals `image_base+0x2c2fa08`.

## Not safely recovered — stay read-only

| Symbol | Status |
|--------|--------|
| `G_GAMESTATE` | No committed RVA. Live heap scans (menu / session) found **no** objects whose `[0]` equals `CGameState`/`CCurrentGameState` primary vptr. Need in-campaign session + `live-gs`. |
| `G_IDLER` | Same |
| `FN_CMD_QUEUE_POST` | **No** `.?AVCCommandQueue@@`. Plain `CommandQueue` strings are SDL `GL_RunCommandQueue`. Do not invent Post. |
| Console execute | Stubbed |

## Write gate

Commit `calling/offsets_verified.json` only after:

1. `G_GAMESTATE` live-gs heuristic OK (countries size 50–2000, player tag plausible)
2. Independent Post-path verification

Until then MCP/tools stay read-only even if `CLAUSEWITZ_ALLOW_WRITE=1`.

## Tools

```text
python clausewitz_win.py doctor|status|peinfo|scan|live-gs
```

Artifacts (gitignored exe): `research/re-dumps/static_scan.json`, `vtables_focused.json`, `live_vt_hits.json`
