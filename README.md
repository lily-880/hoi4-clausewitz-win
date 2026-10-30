# hoi4-clausewitz-win

**Windows-oriented live bridge for Hearts of Iron IV**, inspired by
[smerss/Clausewitz-MCP](https://github.com/smerss/Clausewitz-MCP).

涓婃父 Clausewitz-MCP 浠婂ぉ鏄?**Linux-only**锛坄process_vm_readv` + `CCommandQueue`锛夈€?
鏈粨搴撳仛鐨勬槸锛?*Windows `ReadProcessMemory` 鍚庣 + 1.19.4 鍋忕Щ鍐嶇敓宸ヤ綔鍙?*锛?
鍏堝仛鍒般€岃兘鎸備笂杩涚▼骞跺畨鍏ㄨ鍒拌兘璇佹槑鐨勪笢瑗裤€嶏紝鍐嶈皥鍛戒护闃熷垪涓庡寘楗哄瓙瑙勫垝鍣ㄣ€?

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

## What works

- Phase 2aw: RO handle/province helpers + Post ABI notes; writes DISABLED
- Phase 2av: FN_HANDLE_RESOLVE proven (0x2284800); writes DISABLED
- Phase 2au: GS province resolve proven (CArmy+0x28 / CProvince+0xa4); writes DISABLED
- Phase 2at: DummyServer ring embed + ALLOW_POST stub; handle resolve open; writes DISABLED
- Phase 2as: CArmy CHandle (+0x18 type 0x33) + CProvince id hyp (+0xa4); writes DISABLED
- Phase 2ar: Order* sizes + serialize field layouts (Assign/Execute/NewFront/…); writes DISABLED
- Phase 2aq: StrategicRedeploy serialize (army/province/clear/priority); posting DISABLED now (Phase 2ap)

- **FN_CMD_QUEUE_POST** RVA `0x22c41e0` mapped (CSession post/drop gate) — **writes still DISABLED**
- Full Post→serialize→drain→Execute graph documented (see WINDOWS_OFFSETS)
- Army command catalog: Move/Cancel/StrategicRedeploy/Order* type ids
- Live campaign `status`: countries/armies/fleets/theatres/...

### Earlier Phase 2g notes

- Find `hoi4.exe` install; PE parse; `OpenProcess` + `ReadProcessMemory` (read-only)
- MSVC RTTI 鈫?COL 鈫?vtable recovery for `CGameState` / `CCurrentGameState` / idlers / `CCommand` (live COL MATCH)
- `session-probe` / `status` 鈥?**frontend vs in_game via G_IDLER** (CFrontEndIdler vs CInGameIdler); GS alone 鈮?in-game
- `scripts/phase2g_session_postpath.py` 鈥?one-shot Post-path RO + army scan when map is up; exit 3 + USER ACTION if still frontend
- `live-gs` 鈥?`.data` slot + heap scan; heuristic **`G_GAMESTATE` RVA `0x33dd6b0`** when campaign object live (鈫?gitignored `offsets_verified.json`)
- `status` returns real campaign probe fields once runtime/verified offset loaded (countries size, player tag)
- MCP stdio stub: `hoi4_win_doctor`, `hoi4_win_status`

```powershell
python clausewitz_win.py session-probe
python clausewitz_win.py live-gs
python clausewitz_win.py status
```

**Must have a live campaign object** (not pure empty menu). See `research/WINDOWS_OFFSETS.md`.

## What is stubbed

- **`G_GAMESTATE` in `offsets_verified.json`** 鈥?heuristic only until re-verified on fresh load
- **`FN_CMD_QUEUE_POST` / command posting** 鈥?**DISABLED**; no `CCommandQueue` RTTI; do not invent Post
- `G_IDLER`, console execute, combat planner / 107 tools 鈥?later

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
This repo鈥檚 Windows PE backend and 1.19.4 tables are original work.

## License

MIT 鈥?see [LICENSE](LICENSE).

## Phase 2e (Post graph / dead ends)

- Stronger READ-ONLY Post hunt: `scripts/phase2e_post_graph.py`, `scripts/phase2e_live_scan.py`
- Idler vt+0x90 @ `0xe34e90` wraps `[this+0x530]` then tail-calls vt+0x90 (Linux-analog shape)
- `FN_CMD_QUEUE_POST` still **null**; divisions still stubbed; date year+aux hypotheses only
- See `research/WINDOWS_OFFSETS.md`



## Phase 2g (session gate)

HOI4 was still in **frontend** (`G_IDLER` 鈫?`CFrontEndIdler`) with live GS but no armies.
**You must load a campaign/save until the map is visible**, then re-run `status` or `phase2g_session_postpath.py` once (no polling).
Posting stays DISABLED until `FN_CMD_QUEUE_POST` is proven on a live `CInGameIdler`.

### Phase 2ay note

`G_SESSION=0x34FFBE8` live-proven. Post→Execute SP pipeline documented in `calling/post_abi.py`. **Posting still DISABLED.**
