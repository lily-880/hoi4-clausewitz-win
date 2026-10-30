# hoi4-clausewitz-win

**Windows-oriented live bridge for Hearts of Iron IV**, inspired by
[smerss/Clausewitz-MCP](https://github.com/smerss/Clausewitz-MCP).

上游 Clausewitz-MCP 今天是 **Linux-only**（`process_vm_readv` + `CCommandQueue`）。
本仓库做的是：**Windows `ReadProcessMemory` 后端 + 1.19.4 偏移再生工作台**，
先做到「能挂上进程并安全读到能证明的东西」，再谈命令队列与包饺子规划器。

> Not a day-one 107-tool clone. Phase 1 is honest and read-only.

## Target pin

| Item | Value |
|------|--------|
| OS | Windows 11 (tested on 25H2) |
| Game | `hoi4.exe` **1.19.4.0** Operation Postern |
| Default Steam path (this machine) | `D:\STEAM\steam\steamapps\common\Hearts of Iron IV` |

Game updates will likely require regenerating RVAs. Windows OS updates usually will not.

## Quick start (Windows)

```powershell
cd "$env:USERPROFILE\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win"
$env:HOI4_PATH = "D:\STEAM\steam\steamapps\common\Hearts of Iron IV"
python clausewitz_win.py doctor
python clausewitz_win.py peinfo
# with the game running:
python clausewitz_win.py status
```

## What works now (Phase 1)

- Find `hoi4.exe` install (`HOI4_PATH` / Steam paths / `libraryfolders.vdf`)
- Parse PE32+ headers of `hoi4.exe` (image base, sections)
- `OpenProcess` + `ReadProcessMemory` attach (read-only)
- Prove `MZ` at runtime image base; list committed regions
- Optional string hits inside the main module (`CGameState`, `CCommandQueue`, …)
- Minimal MCP stdio stub: `hoi4_win_doctor`, `hoi4_win_status`

## What is stubbed

- **All game-state globals** (`G_GAMESTATE`, idler, tag DB, …) — Linux RVAs do not transfer
- **`CCommandQueue::Post` / Injector** — Phase 2 (gated behind `CLAUSEWITZ_ALLOW_WRITE=1` even then)
- Combat planner / encirclement search / 107 MCP tools — port later from upstream ideas

## Safety

- Read-only by default
- No remote-thread calls in Phase 1
- Never inject inside a per-tick loop until offsets are version-pinned and tested
- Does not touch Vision Channel / Auto Kessel mods

## Layout

```
clausewitz_win.py          CLI entry
calling/
  process/windows.py       ReadProcessMemory backend
  mem.py                   typed reads
  pe.py                    static PE parser
  config.py                paths / version pin
  offsets.py               Windows offset stubs (fail-closed)
mcp/server.py              Phase 1 MCP stub
research/WINDOWS_OFFSETS.md  how to regenerate offsets
```

## Upstream credit

Architecture and RE methodology inspired by **Clausewitz-MCP** (MIT, smerss).
See their [research/FINDINGS.md](https://github.com/smerss/Clausewitz-MCP/blob/main/research/FINDINGS.md).
This repo’s Windows PE backend and 1.19.4 tables are original work.

## License

MIT — see [LICENSE](LICENSE).
