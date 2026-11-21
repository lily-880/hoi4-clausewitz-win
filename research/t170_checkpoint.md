# t170 checkpoint — CReinforcementRequest ownership and aggregation (ETH live)

Saved 2026-11-18 11:37 America/New_York (EST). Resume authorized by t169u after the bedtime pause. Official inventory unchanged.

## Session recheck (do not reuse pre-shutdown pointers)

- Machine `a849f760-4114-424f-af9c-d10eef8ca3e8`. HOI4 1.19.5.0.7c6c, exe SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`.
- Old pid 29000 was gone after shutdown. Live pid **26976**, process start 2026-11-18 11:26:33 EST, base now `0x7ff721aa0000`.
- In-game `CInGameIdler`, player ETH index 44, GS+0x4BC=0 (1x), date 1936-01-01 hour 12, hour progress 0. Pause bit still unresolved and omitted. Read-only: no Post, no memory write, no speed/pause/campaign change, no save I/O.
- Pre-shutdown heap addresses (for example `0x1b108bb67a0`) are invalid on this pid. Requests were re-found from typed roots.

## Official inventory (unchanged this batch)

- Path: `D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md`
- 116 fields, 14 tables, 3 columns. **41 verified / 75 unverified**.
- SHA256 `4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f` (same as t169 delivery; uppercase equivalent in the shutdown checkpoint).
- No D overwrite. `complete_input` remains false. Schema still reports 54 errors (expected; input is incomplete).
- Tests: **87 passed** (previous 81 plus 6 new `research/test_t170_input_reinforcement.py`).
- Live captures: `research/t170_live_capture.json` and `_repeat.json`, observations equal. 21 units, 4 templates, 12 provinces, 20 leaders, train stockpile 5, 1063 dependent reads rechecked.

## What was proven about the 3/80 request

Live request at `0x26cb1969530` (CReinforcementRequest):

| named field | pool | type | amount |
|---|---|---|---|
| produced (serializer 15AB830, request+0x38) | CEquipmentVariantPool | infantry_equipment | 3 |
| need (same writer, request+0x78) | CEquipmentArcheTypePool | infantry_equipment | 80 |

Ownership:

- Group `CArmyReinforcementRequests` `0x26cb01e6fa0` +0x20 is receiving `CArmy` `0x26cb1c30c30`.
- That army is **unit_id 1835**, owner index 44, present in the own army list. There is no reverse pointer inside the 0x690 CArmy object.
- 15A8790 loads group+0x20 as CArmy and calls CDB4B0, which reads CArmy+0x3B8 (already proven CReferencedDivisionTemplate) and CArmy+0x348 (unit equipment pool).

Unit 1835 cross-check (independent official pools, not the request itself):

- Template 588 Mehal Sefari, `CReferencedDivisionTemplate+0x120` need = **400**.
- Unit pool `CArmy+0x348` current = **320** (ratio 0.8).
- Remaining deficit 400−320 = **80**, equal to request need.
- Request produced 3 is in-transit/produced-toward-request, not the unit's 320 on hand.

## What must not be promoted

- Own-unit infantry deficits across all 21 ETH divisions sum to **2520**, not 80 (or 77). 19 units are short; only 1829 and 1843 are full.
- Only **one** active request group exists, for unit 1835. The 18 other short units have no request in `CReinforcementStatus+0x20`.
- Therefore request need 80 is **this unit's remaining template deficit**, not national demanded. `[1835]` is not the complete `affected_unit_ids` list. `world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` stay unverified.
- Occupation+0x28, logistics+0x28, and operations+0x10 were empty in this scene only. Deployment F70 still has a large +0x20 array and was not treated as empty. 1409890 country-need summation is traced but not fully reimplemented. 15A8790 tail uses a weighted ratio (including a 0x190 factor) and is not accepted as raw need−current.

## Code added (evidence only)

- `calling/input_loaded_fields.py`: `own_reinforcement_requests` — typed, country backlink at status+0x38, army must be in the own list, produced/need plus unit current/template need as evidence.
- `calling/input_capture_live.py` stores the collector under `evidence.reinforcement_request_collection`. Official observation still emits only the already-verified train `stockpile` (5). No demanded/deficit/affected values are written into the observation.
- Offsets note: `calling/tables/offsets_input_windows_1.19.5.json` key `reinforcement_requests_t170`.
- Semantic proof: `research/t170_reinforcement_semantic_proofs.json`.

## Next independent block (no user action required if the same campaign is still live at 1x)

Finish the official country-need path around **1409890** and the **deployment F70** component; determine official `affected_unit_ids` semantics (why 19 short units exist but only one request is live). Do not invent a national demand from the 2520 unit-deficit sum or from the single 80-need request. Building damaged/overlay states remain restricted. 1552CF0 remains a string formatter, not a level getter.

If HOI4 is gone or not in-game at resume, report and stop; do not start or change a campaign. Pause bit is still unknown and must stay omitted. Keep CLAUSEWITZ_ALLOW_POST=0 / WRITE=0, no save I/O, no commit/push, pause/1x not 5x.
