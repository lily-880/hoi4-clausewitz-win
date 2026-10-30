# Findings — Windows Phase 1

**Date:** 2026-10-30 (Asia/Shanghai)  
**Machine:** LAPTOP (Windows 11 家庭版 25H2, build 26200)  
**Game:** `D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe`  
**Version:** 1.19.4.0 Operation Postern (exe mtime 2026-10-29 22:51 Asia/Shanghai)  
**Exe size:** 56530040 bytes (~53.9 MiB)

## Proven

- Install path detection including `D:\STEAM\steam\...`
- PE32+ parse of `hoi4.exe` (see `python clausewitz_win.py peinfo` on the PC)
- Live attach via `ReadProcessMemory` when the game is running (doctor/status)
- Read-only default; write path hard-gated

## Not proven (blocked on RE)

- `G_GAMESTATE` / idler / country tag DB RVAs for this PE
- MSVC RTTI class index
- `CCommandQueue::Post` calling convention + address
- Any division organisation / province live fields on Windows heap

## Parallel track

Script-side Vision Channel mod still useful for coarse daily state while memory RE proceeds.
Do not disable Auto Kessel / Vision Channel when installing this tool.
