# t181 checkpoint — has_river_crossing contract proven and promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, ETH index 44 1x, 1936-01-01 12, hour tick 60759371, country 0x26c4b672530. Speed notch 1, pause flag still unresolved. This batch was read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change.

## Contract

`world.provinces.has_river_crossing` is **per-edge**, not a stored province boolean.

- The t180 token clip `0x83760` is only the string-token registrar. `river_crossing` at 0x2b494b0 is LEA'd at 0xab285 into slot 0x346D188; that slot has no other RIP consumers that read a field.
- Engine predicate in supply/infra pathfinding `0x12971a0` (four clones at 0x1297f10, 0x1298c80, 0x12999f0, 0x129a760), walking the same `[CProvince+0xb8]+0x70` records as neighbors:

      0x1297bbd  movzx eax, byte ptr [rdx + 0x10]
      0x1297bc1  sub al, 2
      0x1297bc3  cmp al, 1
      0x1297bc5  ja  0x1297bd1

  Unsigned range `type in {2, 3}` (river, river_large). On match the pathfinder adds an extra edge cost. Asserts in the same function / caller (`NeighborFlow < CurrentEntry._Flow`, `InfraRatio <= 1_fixed`, `!_NonLocalNodes.Contains(_pCapital->GetProvinceID())`) identify this as capital-network / infra flow, still a per-edge property.
- CProvince `+0..0x200` has **no** byte or aligned scalar that splits the 8 own provinces with type-2 edges from the 4 without. Definition object arrays at `[CProvince+0xb8]+0x28` and `+0x40` appear only on the 8, but size `+0x34` is 1 vs 0 while province 1984 has five type-2 edges; those arrays match RTTI `SRiverPath` / `SProvinceRiverPoint` (map river geometry), not this field.
- Schema allows boolean or object. A single province bool would be the wrong shape. The emitted value is an **object**: decimal-string neighbor id → bool, one key per `neighbors` entry, true iff type is 2 or 3.

## Promotion

Emitted for currently observed own-unit provinces only. Live 12 provinces, 73 land edges, 16 true crossings (all type 2 this scene; type 3 is included by the range check but not present in the ETH sample). Two read-only captures were equal; the 16 trues match `research/t180_landindex_and_edges.json`.

Do not promote 77, `[1835]`, `demanded`, `deficit`, or `affected_unit_ids`. `produced` is still not `min(need, current stockpile)`. Observation equipment remains only `train_equipment` stockpile 5. `complete_input` stays false (`in_combat` / `order` still missing). Building damaged/overlay levels remain restricted; 1552CF0 remains a string formatter.

## Official inventory

Updated D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md only for `world.provinces.has_river_crossing`. Still 116 fields, 14 tables, 3 columns; **43 verified / 73 unverified**. SHA256 `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254`.

## Artifacts

- research/t181_checkpoint.md
- research/t181_session_recheck.json
- research/t181_has_river_crossing_contract.json
- research/t181_no_stored_province_bool.json
- research/t181_live_capture.json, research/t181_live_capture_repeat.json
- research/t181_inventory_sha256.json
- clips: `_t181_clip_river_type_range_0x12971a0.txt`, `_t181_clip_family_0x12971a0.txt`, `_t181_clip_predicate_0x13e0c40.txt`
- offsets key: `has_river_crossing_t181`
- collector: `province_adjacencies` (neighbors + has_river_crossing); `province_land_neighbors` remains a wrapper
- tests: research/test_t181_input_has_river_crossing.py (6 tests). t180 inventory test frozen to its historical SHA so it no longer hashes live D. Suite 151 + 6 = 157.

## Next independent block

Snapshot-ready unverified fields that can move independently: `in_combat`, `order` (required; do not invent false/idle from empty arrays), supply, formation, leaders.assigned_to. Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
