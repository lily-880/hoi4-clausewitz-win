# Regenerating offsets for Windows `hoi4.exe` 1.19.4

## Why Linux tables do not work

Upstream Clausewitz-MCP recovered:

- **Global RVAs** (e.g. `G_GAMESTATE = 0x43F2648`) against a **Linux ELF** build of ~1.19.2
- **Function addresses** the same way
- **Struct field offsets** largely from the game’s own serializers (often layout-similar, still verify)

Windows ships a different binary (`hoi4.exe`, PE32+). ASLR gives a runtime `image_base`;
we store **RVAs** (`runtime_addr - image_base`). Those RVAs almost always differ from ELF.

## Phase 1 goal (done in code)

1. Attach with `OpenProcess` + `ReadProcessMemory`
2. Resolve `image_base` / `SizeOfImage` via `EnumProcessModulesEx`
3. Prove reads (`MZ` at base)
4. Keep `WINDOWS_GLOBALS` as `None` until proven (fail-closed)

## Phase 2 research recipe

### A. Static PE footholds

```powershell
python clausewitz_win.py peinfo
```

Collect:

- Preferred `ImageBase` (usually `0x140000000` for modern PE64)
- Section RVAs (`.text`, `.rdata`, `.data`)
- Rich string table in `.rdata`

Useful strings to xref (IDA/Ghidra/Binary Ninja):

- `CGameState`, `CInGameIdler`, `CCommandQueue`, `CLandCombat`, `CArmy`, `CDivision`
- Serialize / token names from save pipeline
- Console command names

### B. RTTI on MSVC

Linux upstream used Itanium RTTI. MSVC uses a different RTTI layout (`TypeDescriptor`,
`CompleteObjectLocator`). Porting the class→vtable index means an MSVC RTTI walker,
not reusing `calling/rtti.py` from upstream unchanged.

### C. Serializer field names (best lever)

Same idea as upstream §14: when the game serializes, it emits **field names next to offsets**.
Recovering that table on Windows yields developer field names for structs. Field offsets
*inside* a class are the most likely to match Linux if the class layout is shared;
globals still will not.

### D. Live validation

For a candidate `G_GAMESTATE` RVA `R`:

1. `ptr = read_u64(image_base + R)`
2. Check pointer is in a committed region
3. Walk known struct fields (e.g. country array size ≈ number of tags)
4. Cross-check against Vision Channel / UI (player tag, date)

Never write or `CreateRemoteThread` until this is green on **this exact** `hoi4.exe` build.

### E. Command queue (Phase 2+)

Upstream posts through `CCommandQueue::Post` (same legality as mouse clicks).
On Windows you need:

1. Address of the queue object / Post method (RVA)
2. A safe call primitive (`CreateRemoteThread` / hijack) — **never in a tight loop**
3. Constructor + `CanExecute` for each command type you care about (move / attack / retreat / strategic redeploy)

Until then, keep `CLAUSEWITZ_ALLOW_WRITE` unset.

## Tooling suggestions

- Ghidra / IDA / Binary Ninja on a **copy** of `hoi4.exe`
- `python calling/mem.py` while the game is paused for live reads
- Keep dumps under `research/re-dumps/` (gitignored)

## Version pinning

Re-run this document when Paradox ships a new Windows build. Record:

- File size / SHA256 of `hoi4.exe`
- Steam build id if available
- Date (Asia/Shanghai)
