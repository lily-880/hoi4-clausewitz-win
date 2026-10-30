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

## What works now (Phase 2d)

- Find `hoi4.exe` install; PE parse; `OpenProcess` + `ReadProcessMemory` (read-only)
- MSVC RTTI → COL → vtable recovery for `CGameState` / `CCurrentGameState` / idlers / `CCommand` (live COL MATCH)
- `session-probe` — lobby vs in-campaign via heap vptrs
- `live-gs` — `.data` slot + heap scan; heuristic **`G_GAMESTATE` RVA `0x33dd6b0`** when campaign object live (→ gitignored `offsets_verified.json`)
- `status` returns real campaign probe fields once runtime/verified offset loaded (countries size, player tag)
- MCP stdio stub: `hoi4_win_doctor`, `hoi4_win_status`

```powershell
python clausewitz_win.py session-probe
python clausewitz_win.py live-gs
python clausewitz_win.py status
```

**Must have a live campaign object** (not pure empty menu). See `research/WINDOWS_OFFSETS.md`.

## What is stubbed

- **`G_GAMESTATE` in `offsets_verified.json`** — heuristic only until re-verified on fresh load
- **`FN_CMD_QUEUE_POST` / command posting** — **DISABLED**; no `CCommandQueue` RTTI; do not invent Post
- `G_IDLER`, console execute, combat planner / 107 tools — later

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
