# t173 checkpoint — template+0x120 work list, request-need prediction, no stored 77

Saved 2026-11-19 about 01:20 Asia/Shanghai (UTC+8). Continued under t169u after t172. Official inventory unchanged.

## Session recheck

- Machine `a849f760-4114-424f-af9c-d10eef8ca3e8`. HOI4 1.19.5.0.7c6c, exe SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`.
- Live pid **26976**, still in-game `CInGameIdler`, ETH index 44, 1x, date 1936-01-01 hour 12, hour tick **60759371**. Pause bit still omitted. Read-only: no Post, no memory write, no speed/pause/campaign change, no save I/O.

## Official inventory (unchanged this batch)

- Path: `D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md`
- 116 fields, 14 tables, 3 columns. **41 verified / 75 unverified**.
- SHA256 `4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f`.
- No D overwrite. `complete_input` remains false. Schema still 54 errors (expected).
- Tests: **100 passed** (previous 96 plus 4 new `research/test_t173_input_need_worklist.py`).
- Capture code was not changed. t171 live captures remain the current observation evidence.

## (b) 15a26f0 work list is template+0x120, not a distinct +0x108 table

t172 read `CReferencedDivisionTemplate+0x108` as a list and correctly refused to claim that layout. The address was wrong:

- `cdb4b0` returns **`template+0x18`** (`lea rax, [rdx+0x18]`, or null if no template).
- `15aa9c0` then does `lea r8, [rax+0x108]`, which is **`template+0x120`**, the already-proven `CEquipmentArcheTypePool` need pool.
- `c44c40` copies that pool as 16-byte `{type, amount}` rows (skipping zero amounts), which matches the archetype-pool stride.

`15a26f0` then, for each row, takes `1094900(unit+0x348, type)` as current and forms

`request need += max(0, template_need - current - existing_request_need)`.

For unit 1835 that is 400 − 320 = **80**, equal to the live request need. When another short unit later hits its `unit_id % 24` hour slot, its request need can be predicted from the same two official pools, without advancing the campaign.

Allocation after a non-empty work list: `c07690(army+0x1d8)` looks up the owner country from `GS+0x310`; `717350` is `country+0xF98` **CLogisticsStatus** (live `+0x20` is the country backlink). `140b9c0` is a thin wrapper on `CLogisticsStatus+8` that calls `14075c0` with modes 1, 0, and 6; `14075c0` walks the work list and calls `15b1da0` (using `type+0x598`). Scene `produced=3` is the amount allocated on this path. `15b1da0` is not fully reimplemented, so **produced is not a claimed prediction formula**.

## (a) No campaign-stored 1409810 total to cross-check 77

Callers (including UI function `1e1f6a0`) compute 1409810 on demand and may cache it on a **view object** at `+0x648` (equipment type held at `+0x5e0`). That cache is not a campaign field.

Bounded reads on country, reinforcement/deployment/logistics/occupation/operations/production/resources, the infantry `CEquipmentType`, and the 1835 request/template found **no** qword `77*100000` (7,700,000). `CEquipmentType+0x648` is not 77. `CLogisticsStatus+0x20` being country does confirm the 1409890 `this+0x20` shape when callers pass `717350(country)`.

So 77 remains a disassembly-faithful live reimplementation, still without a stored-value cross-check.

## What must not be promoted

`world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` stay unverified. Official 1409810 this hour only includes live requests (deploy queue empty). Requests appear when a unit's hour slot is processed, so `[1835]` is this hour's official contributor set, not the complete 19-unit short-fielded set. Contract meaning is still unconfirmed.

## Next independent block

Either finish `15b1da0` / `14075c0` so `produced` can be predicted from stock, or find an always-present (non-UI) stored 1409810 total. For `affected_unit_ids`, a contract decision is still required: this-hour official contributors vs all short fielded units. Do not advance the campaign to test later hour slots. Building damaged/overlay states remain restricted. 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at resume, report and stop; do not start or change a campaign. Keep CLAUSEWITZ_ALLOW_POST=0 / WRITE=0, no save I/O, no commit/push, pause/1x not 5x.

Technical proof: `research/t173_worklist_and_stored_need.json`. Live scan: `research/t173_stored_need_live.json`. Offsets note: `calling/tables/offsets_input_windows_1.19.5.json` key `reinforcement_worklist_t173`.
