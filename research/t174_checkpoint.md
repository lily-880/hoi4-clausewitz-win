# t174 checkpoint — 15b1da0 is a logistics add, not produced; 15a92f0 accepts offered into produced

Saved 2026-11-19 about 01:35 Asia/Shanghai (UTC+8). Continued under t169u after t173. Official inventory unchanged.

## Session recheck

- Machine `a849f760-4114-424f-af9c-d10eef8ca3e8`. HOI4 1.19.5.0.7c6c, exe SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`.
- Live pid **26976**, still in-game `CInGameIdler`, ETH index 44, 1x, date 1936-01-01 hour 12, hour tick **60759371**. Pause bit still omitted. Read-only: no Post, no memory write, no speed/pause/campaign change, no save I/O.

## Official inventory (unchanged this batch)

- Path: `D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md`
- 116 fields, 14 tables, 3 columns. **41 verified / 75 unverified**.
- SHA256 `4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f`.
- No D overwrite. `complete_input` remains false.
- Tests: **106 passed** (previous 100 plus 6 new `research/test_t174_input_produced_alloc.py`).
- Capture code was not changed. t171 live captures remain the current observation evidence.

## Correction: 14075c0 / 15b1da0 do not write produced

t173 left produced as "the allocated amount after 140b9c0", not a formula. This batch fully reduced that path:

- `14075c0(logistics+8, mode, work_list)` takes `pool = 15b1d90([logistics+8][mode])`.
- `15b1d90` is `return [obj+0x10]+0x30`. Live: `[CLogisticsStatus+8][mode]` is **CLoopHistory**; `+0x10` is **CLoopHistoryContainer**; `+0x30` is an untyped dense qword array (this scene count 81).
- `15b1da0(pool, amount, type+0x598)` does `array[index] += amount`, capped to the same limits as 1409810: `[0xffffac1d29df04c0, 0x53e2d620fb40]`. It stores in place and does not return a produced quantity.
- `140b9c0` uses modes **1, 0, 6**. Sibling `140b810` (the 15a2a20 path) uses modes **4, 0, 6**.
- Live `infantry_equipment+0x598 = 15`. After this already-completed hour, observed mode slots at that index are 0.

So 140b9c0 is a logistics accumulator update for the work-list amounts, not the request produced writer.

## Produced path: empty init, return-to-stock, accept-offered

- `15a26f0` initializes `request+0x38` with `10925a0` (empty produced pool) and only writes need at `+0x78`.
- Helpers: `1092b70` adds a capped amount to a variant-pool row; `1098700` / `1098540` subtract (via `2574ba0` neg); `10928b0` adds a stride-0x18 list into a variant pool.
- `ee1250(production, type, &amount, dest)` moves equipment **from dest to** `CProductionStatus+0x200` (subtract dest, add stock). It is return-to-stock, not allocate-from-stock.
- `15a5c80` (called from 15aa9c0 after 140b9c0) can reduce request need (`1098540`) and return excess produced via `ee1250`. It does **not** add to produced.
- `15a55e0` only registers `CArmyRequests+0x70` in a parent list and sets a flag at `+0x60`.

The function that **adds** to produced is `15a92f0`:

`give = min(max(0, need − produced), offered); 1092b70(request+0x38, type, give); remaining = offered − give`.

This batch found no E8/E9 or absolute-RVA callers of `15a92f0`, so the source of `offered` is not yet bound to national stock. **produced is not a claimed prediction formula.** Do not write `produced = min(need, stock)`.

Live stock at `production+0x200` this scene: only present type is `train_equipment=5`. `infantry_equipment` is absent from the present stockpile (t170/t171 remain the evidence that request produced is 3). That is consistent with infantry already having left stock after the completed hour allocation, but it is not a stored-value cross-check of 77 or 3.

## What must not be promoted

`world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` stay unverified. 77 still has no campaign-stored cross-check. `[1835]` is still this hour's official contributor set, not the complete short-fielded set.

## Next independent block

Bind the caller of `15a92f0` (likely a vtable or RIP-relative path; no E8 found) and reduce the `offered` source, so `produced` can be predicted from stock plus `give = min(max(0, need−produced), offered)` without advancing the campaign. Or continue looking for a non-UI stored 1409810 total to cross-check 77. `affected_unit_ids` still needs a contract decision (this-hour official contributors vs all short fielded units). Do not advance the campaign to test later hour slots. Building damaged/overlay states remain restricted. 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at resume, report and stop; do not start or change a campaign. Keep CLAUSEWITZ_ALLOW_POST=0 / WRITE=0, no save I/O, no commit/push, pause/1x not 5x.

Technical proof: `research/t174_alloc_semantics.json`. Live: `research/t174_alloc_and_stock_live.json`. Offsets: `reinforcement_alloc_t174`. Tests: `research/test_t174_input_produced_alloc.py`. Listings: `research/_t174_clip_15b1da0.txt`, `_t174_clip_14075c0.txt`, `_t174_clip_15a92f0.txt`, `_t174_clip_ee1250.txt`, `_t174_clip_15a5c80.txt`.
