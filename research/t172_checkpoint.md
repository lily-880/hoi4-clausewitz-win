# t172 checkpoint — why only 1835 was stamped by 15aa9c0

Saved 2026-11-19 about 01:30 Asia/Shanghai (UTC+8). Continued under t169u after t171. Official inventory unchanged.

## Session recheck

- Machine `a849f760-4114-424f-af9c-d10eef8ca3e8`. HOI4 1.19.5.0.7c6c, exe SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`.
- Live pid **26976**, still in-game `CInGameIdler`, ETH index 44, 1x, date 1936-01-01 hour 12, hour progress 0, hour tick **60759371**. Pause bit still omitted. Read-only: no Post, no memory write, no speed/pause/campaign change, no save I/O.

## Official inventory (unchanged this batch)

- Path: `D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md`
- 116 fields, 14 tables, 3 columns. **41 verified / 75 unverified**.
- SHA256 `4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f`.
- No D overwrite. `complete_input` remains false. Schema still 54 errors (expected).
- Tests: **96 passed** (previous 92 plus 4 new `research/test_t172_input_request_stagger.py`).
- Capture code was not changed. t171 live captures remain the current observation evidence.

## Why only 1835 has the current 15aa9c0 stamp

`ce4fc0` is a **CArmy virtual method** (vtable +0x90, slot 18). It has no direct E8 callers. For each army it does:

```
hour_residue = (GS+0x468 hour_tick - 0x29C55C0) % 24    ; 0x29C55C0 = 43800000
unit_residue = (CArmy+0x1c unit_id) % 24
if hour_residue == unit_residue:
    15ab390(CArmy+0x478 CArmyRequests)
15a96e0(CArmy+0x478)   ; always, not residue-gated
```

The signed 0x2AAAAAAB / 24 and unsigned 0xAAAAAAAB / 24 sequences were checked against the same modulo. Live values:

- hour_tick 60759371 → residue **11**
- Among ETH units 1829–1849, **only 1835** has unit_id % 24 == 11
- Only 1835 has `CArmyRequests+0xE0 == 60759371`; the other 20 still have 43791240

That is why only 1835 ran the 15aa9c0 non-empty work path this hour. It is a **24-hour staggered per-unit schedule**, not a unique flag on 1835 and not a missing `CArmyRequests` object (all 21 units have one).

`15ab390` still applies its own date gate (`+0xE0 + 24*setting` vs current tick) after the residue match. `15aa9c0` may create/update requests via `15a26f0`, then `140b9c0` allocates (this scene: produced 3 toward need 80) and stamps `+0xE0` only on the non-empty work path.

`ce82d0` (callers 74c330, 758a10, 75e480) and `ceb320` (many callers) can also reach 15aa9c0, but in this scene the stamped set equals exactly the residue-matching set, so the virtual hourly stagger accounts for the current stamp.

`15a26f0` is the creator once a unit is selected. 15aa9c0 passes `CReferencedDivisionTemplate+0x108` as the r8 work-list object into `c44c40` (a 16-byte {ptr, amount} range helper). Live bytes at +0x108 did not look like a populated {begin, count at +0x14} array; that inner layout is **not** claimed this batch. Selection, not a special 1835-only equipment flag, is what limited the live request set.

## What must not be promoted

`world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` stay unverified. The stagger explains the single live request at 1936-01-01 hour 12; later hours will select other `unit_id % 24` slots, so `[1835]` is not the complete shortage-affected set. 77 remains this hour's official 1409810 infantry sum, still without a stored-value cross-check.

## Next independent block

If the shortage fields are to be promoted, either (a) find a stored official 1409810 total to cross-check 77, and define `affected_unit_ids` as official contributors-this-tick vs all short fielded units; or (b) finish the 15a26f0 / template+0x108 work-list layout and 140b9c0 allocation so request need/produced can be predicted for a unit when its hour slot arrives. Do not advance the campaign to test later slots. Building damaged/overlay states remain restricted. 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at resume, report and stop; do not start or change a campaign. Keep CLAUSEWITZ_ALLOW_POST=0 / WRITE=0, no save I/O, no commit/push, pause/1x not 5x.

Technical proof: `research/t172_stagger_semantics.json`. Live table: `research/t172_stagger_live.json`. Offsets note: `calling/tables/offsets_input_windows_1.19.5.json` key `reinforcement_hour_stagger_t172`.
