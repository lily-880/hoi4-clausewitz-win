# t171 checkpoint — 1409890 / 1409810 country need and F70+0x60

Saved 2026-11-19 about 01:20 Asia/Shanghai (UTC+8). Session continued under t169u after t170. Official inventory unchanged.

## Session recheck

- Machine `a849f760-4114-424f-af9c-d10eef8ca3e8`. HOI4 1.19.5.0.7c6c, exe SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`.
- Live pid **26976**, still in-game `CInGameIdler`, ETH index 44, GS+0x4BC=0 (1x), date 1936-01-01 hour 12, hour progress 0, hour tick 60759371. Pause bit still omitted. Read-only: no Post, no memory write, no speed/pause/campaign change, no save I/O.

## Official inventory (unchanged this batch)

- Path: `D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md`
- 116 fields, 14 tables, 3 columns. **41 verified / 75 unverified**.
- SHA256 `4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f`.
- No D overwrite. `complete_input` remains false. Schema still 54 errors (expected).
- Tests: **92 passed** (previous 87 plus 5 new `research/test_t171_input_country_need.py`).
- Live captures: `research/t171_live_capture.json` and `_repeat.json`, observations equal. 21 units, 4 templates, 12 provinces, train stockpile 5, 1082 dependent reads rechecked.

## Official country-need path (1409810 / 1409890)

1409810 = 1409890(this, out, type, r9=null) + 14080c0, then cap.

1409890, with `[this+0x20]` = country:

1. **Deployment (F70).** `b2cb40(CDeploymentStatus)` returns **status+0x60**, not +0x20. Each item: need via `d498a0` (item+0xB8 → +0x38 → +0x20 `CReferencedDivisionTemplate+0x120`), current via `31f8b0` = item+0x20 `CEquipmentVariantPool`; add `max(0, need-current)` (default FIXED weight 1.0).
2. **Reinforcement (F78).** `717400(country)` is `[country+0xf78]`. For each request: add **need − produced** (`10948a0` at request+0x78, `1094900` at +0x38, `2574ba0` is `neg rdx`).
3. **Type-gated specials** `cf5620` / `cf5660` via `7362c0`. For live `infantry_equipment`: +0x5a0=0x20 so `100f620` returns 0x20 (bit 31 clear); +0x44b=0. Both branches skipped. This is type-specific, not a general rule.
4. Then `140a400` occupation (FD0+0x28), `1409e50` logistics (F98+0x28), `140a600` operations (15A8+0x10).
5. **14080c0** walks `country+0x11f8` **CCountryResources** array +0x758 / count +0x764 (pools at item+0x198 and +0x1d8). It is **not** a request-deficit summer (t169 hypothesis corrected).

Live scene:

- F70+0x60 is empty (cap 0, size 0). The previously noted +0x20 104/141 array is a **CSubUnitDefinition catalog**, not the official need source.
- One request: need 80, produced 3, official contribution **77**.
- Resources / occupation / logistics / operations arrays are empty (scene fact).
- Official 1409810 infantry total in this scene = **77**, not 80, not the 2520 fielded deficit sum.
- Official contributors from these components: **[1835]** only.

`world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` are **not** promoted. 77 is a disassembly-faithful reimplementation; no stored `77*100000` was found in bounded status objects, and affected_unit_ids in the contract may still mean all shortage-affected units (18 other short fielded divisions are real deficits but are not in this official sum).

The collector is evidence-only: `evidence.official_country_need_collection`. Observation still emits only the already-verified train `stockpile` (5).

## Why 19 short units have only one live request (partial)

- Every one of the 21 own `CArmy` objects has `CArmyRequests` at **+0x478** (backlink +8 is that army). `CArmyReinforcementRequests` sits at `CArmyRequests+0x10`.
- Only unit 1835 has a `CReinforcementRequest` in the country F78 list.
- `CArmyRequests+0xE0` equals the current GS+0x468 hour tick **60759371 only for 1835**. The other 20 still have **43791240**.
- `15aa9c0` processes one `CArmyRequests`, may create/update requests via `15a26f0`, and stamps +0xE0 only on the non-empty work path.
- `15ab390` is a date gate (`[this+0xE0] + 24*setting` vs current tick). It does **not** by itself explain the other 20 remaining unprocessed, because their stamps are in the past.

## Next independent block

Finish why `15aa9c0` has only stamped 1835 this campaign: callers `ce82d0` / `ceb320` / `15ab390` (which armies are selected), and/or the first-loop work-list / stockpile allocation gate inside `15a26f0`. Do not treat 77 or [1835] as promoted demanded/affected_unit_ids without a stored-value cross-check and a confirmed contract meaning. Building damaged/overlay states remain restricted. 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at resume, report and stop; do not start or change a campaign. Keep CLAUSEWITZ_ALLOW_POST=0 / WRITE=0, no save I/O, no commit/push, pause/1x not 5x.

Technical proof: `research/t171_country_need_semantics.json`. Offsets note: `calling/tables/offsets_input_windows_1.19.5.json` key `country_need_1409810_t171`.
