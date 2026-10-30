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
