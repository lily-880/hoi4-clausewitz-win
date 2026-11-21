from pathlib import Path
ck = r'''# t180 checkpoint — province neighbors code-bound and promoted

## Session

Live process rechecked before capture: pid 26976, HOI4 1.19.5.0.7c6c, in_game, ETH index 44 1x, 1936-01-01 12, hour tick 60759371, country 0x26c4b672530. Speed notch 1, pause flag still unresolved. This batch was read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change.

## Proven this batch

The adjacency array at `[CProvince+0xb8]+0x70` now has a code reader and a typed writer, not only the t179 empirical stride.

- Reader `0xe90560` (clip `research/_t180_clip_NeighborAdjs_size_0xe90560.txt`): `rdi` is the `CProvince+0xb8` object; `data = [rdi+0x70]`; loop `add r12, 0x30` while index `< [rdi+0x7c]`; neighbor id is `dword [r12 + data + 8]`. Index scale `lea rbx, [rax+rax*2]; shl rbx, 4` is also `*48`.
- Writer `0x14a6540` (clip `research/_t180_clip_0x14a6540.txt`): `lea r10, [rax+rax*2]; add r10, r10` then `[data + r10*8 + off]` is `index*48`. Type byte: `mov byte ptr [rax + r10*8 + 0x10], r8b`.
- Parser `0xab3660` (adjacencies.csv, clip `research/_t180_clip_0xab3660.txt`) assigns `r12b` then `movzx r8d, r12b; call 0x14a6540`:
  - 0 land (`xor r12b, r12b` default)
  - 1 sea (`mov r12b, 1`)
  - 2 river (`sete r12b; add r12b, r12b`)
  - 3 river_large (`mov r12b, 3`)
  - 4 impassable (`mov r12b, 4`)
- Pathfinding `0xd55250` uses `CMap+0x238` i32 land-index, `-1` = sea, consistent with the type-1 exclusion.

Live own 12 ETH provinces (landlocked): 73 edges, type hist `{0:57, 2:16}`, 0 sea / 0 impassable, 0 land-index `-1`, 22/22 internal edges reciprocal, no self-edges. Types 1 and 4 are parser+writer proven; this scene has no coastal live sample. `CMap+0x2c0` is **not** a universal `CProvince*` table (sea-id slots were not CProvince) and was not used by the collector.

## Promotion

`world.provinces.neighbors` is promoted and emitted for currently observed own-unit provinces as the neighbor ids with type in `{0, 2, 3}` (land, river, river_large) in engine array order. Sea (1) and impassable (4) are excluded. Two read-only captures were equal; 73 emitted ids match `research/t180_landindex_and_edges.json`.

`world.provinces.has_river_crossing` is **not** promoted. Type 2/3 is a per-edge enum; the schema allows bool or object, and the contract shape is still unconfirmed. Do not treat "any type-2/3 edge" as that field.

Do not promote 77, `[1835]`, `demanded`, `deficit`, or `affected_unit_ids`. `produced` is still not `min(need, current stockpile)`. Observation equipment remains only `train_equipment` stockpile 5. `complete_input` stays false (`in_combat` / `order` still missing). Building damaged/overlay levels remain restricted; 1552CF0 remains a string formatter.

## Official inventory

Updated D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md only for `world.provinces.neighbors`. Still 116 fields, 14 tables, 3 columns; **42 verified / 74 unverified**. SHA256 `0f0576e02549f045b58f158472cb4adf8fa13e6b39b321cbbd549737a480841b`.

## Artifacts

- research/t180_checkpoint.md
- research/t180_session_recheck.json, research/t180_session_recheck_final.json
- research/t180_neighbor_reader.json, research/t180_adjacency_type_enum.json
- research/t180_landindex_and_edges.json, research/t180_stride48_sites.json, research/t180_adjacency_xrefs.json
- research/t180_live_capture.json, research/t180_live_capture_repeat.json
- research/t180_inventory_sha256.json
- clips: `_t180_clip_NeighborAdjs_size_0xe90560.txt`, `_t180_clip_0x14a6540.txt`, `_t180_clip_0xab3660.txt`, `_t180_clip_sea_province_pathfinding_0xd55250.txt`
- offsets key: `province_adjacency_reader_t180` (t179 empirical key left unchanged)
- collector: `province_land_neighbors` in calling/input_loaded_fields.py; emitted from calling/input_capture_live.py
- tests: research/test_t180_input_neighbors.py (8 tests). Suite 143 + 8 = 151.

## Next independent block

Confirm the `has_river_crossing` contract (province bool vs per-edge list/object) against type 2/3 and the already-pulled river_crossing token clip `research/_t180_clip_river_crossing_token_0x83760.txt`. Only promote that field if the shape is proven. Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter. Other snapshot-ready unverified fields (supply, formation, leaders.assigned_to, in_combat, order) stay available if the river contract hits a new bound.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
'''
Path("research/t180_checkpoint.md").write_text(ck, encoding="utf-8")
print("checkpoint written", len(ck))
