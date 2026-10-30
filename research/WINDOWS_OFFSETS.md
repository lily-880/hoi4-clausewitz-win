# Windows offset recovery — HOI4 1.19.4 PE

Target: `hoi4.exe` PE32+ · ImageBase `0x140000000` · SizeOfImage `0x38a3000`  
SHA256: `CF781ED178CD801643B233B7E3FCD1C0EFD19BD01AECD24BF07A35F69F10476F`  
Launcher: 1.19.4.1 (Operation Postern)

Upstream Clausewitz-MCP RVAs are **Linux ELF 1.19.2** — do not copy.

## Session requirement (lobby vs in-campaign)

| Session | How to tell | What live-gs / session-probe do |
|---------|-------------|----------------------------------|
| **Lobby / main menu / unloaded** | Heap has **no** `CGameState` / `CCurrentGameState` / `CInGameIdler` vptrs | **0 hits expected**. Not a bug. |
| **In-campaign / campaign object live** | Heap shows `CCurrentGameState` and/or `CInGameIdler` (map usually visible; WS may still be modest) | `session-probe` → `in_campaign`; then `live-gs` |

**You need a live campaign object** before `G_GAMESTATE` recovers. Pure menu with no GS heap object yields empty results by design.

```text
python clausewitz_win.py session-probe   # lobby vs in_campaign (once)
python clausewitz_win.py live-gs         # .data slot + heap; writes offsets_runtime.json
python clausewitz_win.py status          # uses runtime/verified G_GAMESTATE if present
```

## Proven static (safe to cite)

| Symbol | Kind | RVA | Notes |
|--------|------|-----|-------|
| `.?AVCGameState@@` | RTTI name | `0x31e75a0` | TD `0x31e7590` |
| CGameState vtable | vftable | **`0x279f0f0`** | COL live MATCH under ASLR |
| CGameState vtable (2nd) | vftable | `0x279f148` | MI secondary |
| CGameState ctor LEA sites | code | `0x1d78ae`, `0x1da5a6` | `lea reg, [vftable]` |
| `.?AVCCurrentGameState@@` | RTTI | `0x31e78b8` | vtables `0x279f168`, `0x279f1c0` |
| `.?AVCInGameIdler@@` | RTTI | — | vtable **`0x29e5838`** (strong in-map signal) |
| `.?AVCGameIdler@@` | RTTI | `0x31ee078` | vtables `0x27b4158`, `0x27b4510` |
| `.?AVCCommand@@` | RTTI | `0x31e74b8` | vtable `0x279f4a0` |

## G_GAMESTATE — live heuristic (not yet offsets_verified)

| Field | Value |
|-------|-------|
| Candidate RVA | **`0x33dd6b0`** |
| How | `.data` slot → ptr → object `[0]` = `CCurrentGameState` vtable `0x279f168` |
| Probe | countries size/cap **440**, player_tag **15** (`looks_like_gamestate` ok) |
| Status | Written to **gitignored** `calling/offsets_runtime.json` by `live-gs` |
| Promote? | Re-verify across a fresh load / new PID before `offsets_verified.json` |

Static RIP-store hunt near ctor found **0** candidates; live image `.data` scan found the slot above. Zero-init written-slot list (~117) did not include this RVA (slot was already non-zero in the dump, or outside that filter).

## Phase 2c static dead ends

| Attempt | Result |
|---------|--------|
| RIP stores near GS ctor LEAs | **0** G_* candidates |
| Widen window | still **0** |
| `.data` start `0x30fd000` | section base, not singleton |
| `QueueCommand` / `ExecuteCommand` strings | present; **0** Post code xrefs |

## Command queue — DISABLED

| Lead | Status |
|------|--------|
| `.?AVCCommandQueue@@` | **Absent** |
| Plain `CommandQueue` | SDL `GL_RunCommandQueue` red herring |
| `FN_CMD_QUEUE_POST` | **null**; posting **DISABLED** until independently proven |
| `CCommand` / `CCommandHelper@…` | RTTI only — not Post |

`CLAUSEWITZ_ALLOW_WRITE` does **not** enable command posting.

## Write gate

Commit `calling/offsets_verified.json` only after:

1. `G_GAMESTATE` re-verified on a fresh campaign load (same RVA + probe ok)
2. Independent Post-path verification

Until then tools stay read-only for writes even if `CLAUSEWITZ_ALLOW_WRITE=1`.

## Tools

```text
python clausewitz_win.py doctor|status|peinfo|scan|session-probe|live-gs
python scripts/phase2c_recover.py
python scripts/session_probe.py
```

Artifacts: `research/re-dumps/phase2c_recover.json`, `data_zero_ptr_slots.json`, `live_gs_hit.json`, `static_scan.json`.
