# t179 checkpoint — no stored official 77; need/produced formulas recorded; adjacency not promoted

Authorization: t169u still valid. Read-only live attach to HOI4 1.19.5.0.7c6c pid 26976 (ETH index 44, 1x, 1936-01-01 hour 12, hour tick 60759371). Process rechecked in-game before scanning. No memory write, no Post, no campaign or speed change, no save I/O, no commit/push, no game-method execution.

## Session

Same live scene as t171–t178. Observation evidence still t171 captures (collector unchanged). Official inventory not rewritten: 116 fields, 14 tables, 3 columns, 41/75, SHA256 4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f. complete_input=false.

## 1409810 stored-total scan (bounded, then stop)

1409810 has 11 E8 call sites in 10 functions. All are UI, lend-lease/production/logistics display, or a script ForEach:

- 2d5b40, 1ddf4e0, 1de0d60, 1df0130, 1df0810, 1e1f6a0, 1e208f0, 1fa1a50: UI strings such as PRODUCTION_EQUIPMENT_TOTAL_NEED, LOGISTICS_EQUIPMENT_VALUE, DIPLOMACY_LEND_LEASE_IN_STOCK_VALUE. 1e1f6a0 still writes the result to a UI object at +0x648 (already rejected as UI-only). 1e208f0 accumulates into a UI object at +0x668.
- 1453780: IsTradable(...) trade path; the difference is used transiently.
- **52df40** is the only `lock add` site. Its strings are `Infinite cycle in event FROM scope` and Parallel ForEach over `country`. It divides (stock − 1409810) by FIXED and lock-adds the integer into a script output dword. That is not a campaign-stored official total on country/status objects.

1409890’s extra caller **140ba10** is `logistics.postdailythreaded`. It computes the same capped 1409890+14080c0 sum, subtracts it from stock (1409630), and writes the difference through 15b1d90 / 15b3220 (logistics dense array indexed by type+0x598). That is a daily logistics balance, not a stored 77.

Bounded live scan of CCountry and the known status objects (including production+0x200 present rows and the reinforcement request list) found no i64 77 and no 77*100000. CLogisticsStatus+0xe48 holds i64 80 (the live request need), not 77. Production+0x200 still has only train_equipment qty=5.

**Conclusion:** no campaign-stored non-UI official 1409810 total was found. This shortage trail stops here this batch. demanded / deficit / affected_unit_ids stay unverified. Official contributors remain [1835] versus 19 short fielded units; that contract is still not confirmed.

## Formulas recorded (technical only)

Need:

- Selected unit remaining need = `CReferencedDivisionTemplate+0x120` − `CArmy+0x348` (t170: 1835 is 400−320=80).
- Official country total = `1409810 = cap(1409890 + 14080c0)`. 1409890 sums deployment F70+0x60 deficits and (request need − produced), then occupation/logistics/operations. 14080c0 is CCountryResources, not request deficits. This scene’s official infantry total is 77 from 1835’s 80−3. The 2520 fielded-deficit sum is not that official total.

Produced (daily accept only, t177–t178):

- Pre-daily, for each `production+0x200` present type with `qty>0`, `offered` starts as that FIXED qty and is reduced by earlier acceptors before 15a93d0.
- `give = min(max(0, need − produced), offered)` (non-air: cb8e80 passes r9 through).
- Not `produced = min(need, current stock)` after the type has left the pool. Infantry is still absent at hour 12; produced=3 stays t170/t171 evidence. The campaign was not advanced.

These formulas are in `research/t179_need_produced_formulas.json` and offsets key `need_produced_formulas_t179`. They are not written into the official inventory as demanded.

## Adjacency (switched after the 77 bound; not promoted)

Live CProvince id remains +0xa4. The neighbor candidate array is still at `[CProvince+0xb8]+0x70` (t156), with plausible degrees 5–9 on the 12 own provinces. t156’s stride 40 was wrong. An empirical **stride 48**, target at **+8**, fits every record (`0, 0, id, …`), all 73 targets are plausible province ids, there are no self-edges, and all 22 internal edges among the 12 own provinces are reciprocal.

This is **not** enough to promote `world.provinces.neighbors`: the stride is empirical (no bound array reader yet), and land vs sea/strait/river is not code-proven. `has_river_crossing` is untouched. Offsets key `province_adjacency_array_t179` records the location only.

## Artifacts

- research/t179_checkpoint.md
- research/t179_session_recheck.json
- research/t179_1409810_callers.json
- research/t179_1409810_no_stored_total.json
- research/t179_1409890_callers.json
- research/t179_bounded_77_scan.json
- research/t179_need_produced_formulas.json
- research/t179_adjacency_strings.json, t179_adjacency_xrefs.json, t179_province_neighbor_live.json, t179_province_b8_array.json, t179_adjacency_stride48_empirical.json
- clips: `_t179_clip_140ba10.txt`, `_t179_clip_neighbours_0xa228f0.txt`, `_t179_clip_not_neighbours_0x3663e0.txt`, `_t179_clip_NeighborAdjacency_assert_0xdb76e0.txt`
- offsets keys: `need_produced_formulas_t179`, `province_adjacency_array_t179`
- tests: research/test_t179_input_formulas_and_77.py

## Next independent block

Bind a **code reader** of `[CProvince+0xb8]+0x70` to confirm stride 48 and the target field, and distinguish land adjacency from sea/strait/river before considering `world.provinces.neighbors` or `has_river_crossing`. Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter. Other snapshot-ready unverified fields (supply, formation, plans/wars in this empty-peace scene, leaders.assigned_to) stay available if adjacency hits a new bound.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
