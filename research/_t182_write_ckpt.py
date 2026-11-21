# -*- coding: utf-8 -*-
from pathlib import Path
md = """# t182 checkpoint — official CArmy writers bound; in_combat / order not promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, ETH index 44 1x, 1936-01-01 12, hour tick 60759371, country 0x26c4b672530, gs 0x26c259d0ff0. Speed notch 1. This batch was read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No test war, no orders issued.

## Official ABI

CArmy serialization goes through the secondary interface at **CArmy+0x10** (vtable RVA 0x29d6f78, writer `0xced2e0`). `rcx` is already CArmy+0x10; every writer offset needs **+0x10** to reach the CArmy slot used by observation. The base writer `0xc5c0a0` is called first from `0xced2e0`. Reading writer offsets as if they were CArmy-absolute (the first live pass this batch) mixed allocator stubs into scalars; the +0x10 reread is consistent with location, path, and the t165 supply slots.

Path / full_path share serializer `0x1d2bf0`:

    0x1d2c00  movsxd rbx, dword ptr [r8 + 0xc]
    0x1d2c07  mov r14, qword ptr [r8]
    0x1d2c0a  test ebx, ebx
    0x1d2c0c  jle  0x1d2c7f
    … mov edx, dword ptr [r14 + rbx*4]

A pdx i32 array (`data=[r8]`, `size=[r8+0xc]`). size≤0 omits the key. On CArmy: path at +0x200 / size +0x20c (token 0x174); full_path at +0x220 / size +0x22c (token 0x362c).

Commandlist (token 0xcb) lives at CArmy+0x2c0, size +0x2cc, stride-8 pointers; the writer does `cmp dword [rdi+0x2bc], 0; je skip` and, when present, uses `dword [elem+8]` as a per-command serializer token. Official empty encoding = omit the whole key.

Location token 0x286d is the already-verified CProvince* at CArmy+0x1f0 (`id` at +0xa4). retreat (0x2920, CA+0x24c), withdraw (0x38ec, +0x24d) and strategic_redeployment (0x2edb, +0x2af) are bytes written only if nonzero. out_of_supply_days (0x335f, CA+0x498) is skipped when ≤0. last_combat_date (0x2fdf, date at CA+0x1d0, gate CA+0x1c8) is a historical date, not current in_combat.

Supply tokens on `0xced2e0`:

    0xced380  mov r8, qword ptr [rbx + 0x5f0]   ; TOKEN max_supply 0x3a43  → CA+0x600 = 108.0
    0xced59b  mov r8, qword ptr [rbx + 0x600]   ; TOKEN army_current_supply_ratio 0x4ced → CA+0x610 = 72.0
    0xced5af  mov r8, qword ptr [rbx + 0x5f8]   ; TOKEN supply_gain 0x4cec → CA+0x608 = 0.0

t165 had the names swapped relative to the raw writer offsets; after the +0x10 conversion they match t165's CArmy slots. 72.0 is still not a 0..1 ratio. Do not invent `72/108`.

GetOrderType (`0x10b2c60` `cmp dword [rcx+0x30], 1` = ORDER_MOVE; `0x10b038e` `cmp …, 3` = ORDER_INVASION; also cmp 4, likely PARADROP) is a **battle-plan / COrderInstance** type, not `world.own_units.order.type`. land_combat_id token 0x34a6 is written at `0x2091bc` from `[obj+0x748]` in `0x208f90`, sibling navy_id 0x34a5 at +0x74c — not a CArmy field.

## Live (21 own divisions)

All 21: commandlist size 0, path size 0, full_path size 0, support_attack/previous null, retreat/withdraw/SR/execute_order/was_paradropped/uc_pause 0, movement_progress 0, out_of_supply_days 0, location ids match known own-unit provinces. GS+0x268 combats: data 0, size 0. Two earlier concerns (max_supply looking like a pointer, oos_days looking corrupted) were the missing +0x10.

## Not promoted

Empty official lists and zero flags prove structure and the official empty encoding; they do **not** distinguish the schema contracts:

- `in_combat`: no official CArmy IsInCombat / current CLandCombat* reader bound. Empty GS+0x268 and last_combat_date are not a current-combat boolean.
- `order`: omitting commandlist/path when size==0 is official “no list”, not `order.type=idle`. retreat/withdraw/SR official-zero are those flags only, not the schema enum. Do not write empty arrays as false/idle.
- `supply.ratio` / in_supply / isolated: official ratio slot is 72.0 /100000; no named isolated or in_supply token.
- `formation`, `leaders.assigned_to`: not bound this batch (`is_assigned` 0x385b writers 0x26940 / 0x14a8ec0 still unbound). t165 theatres remain structure-only.

`complete_input` stays false. Do not promote 77, `[1835]`, demanded / deficit / affected_unit_ids. `produced` is still not `min(need, current stockpile)`. Building damaged/overlay levels remain restricted; 1552CF0 remains a string formatter.

## Official inventory

D:\\Michael Foo\\钢四陆军总司令\\态势信息读取能力清单.md was **not** written. Still 116 fields, 14 tables, 3 columns; **43 verified / 73 unverified**. SHA256 `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254` (unchanged from t181).

## Artifacts

- research/t182_checkpoint.md
- research/t182_session_recheck.json
- research/t182_carmy_writers.json
- research/t182_empty_not_idle.json
- research/t182_carmy_order_supply_live.json
- research/t182_inventory_sha256.json
- research/t182_combat_order_strings.json, research/t182_order_combat_xrefs.json
- clips: `_t182_clip_carmy_base_writer_0xc5c0a0.txt`, `_t182_clip_carmy_secondary_writer_0xced2e0.txt`, `_t182_clip_path_serializer_0x1d2bf0.txt`, `_t182_clip_land_combat_id_0x208f90.txt`, `_t182_clip_GetOrderType_0x10b2c60.txt` and siblings
- offsets key: `combat_order_supply_t182` (`promoted: false`)
- tests: research/test_t182_input_combat_order.py (6 tests). Suite 157 + 6 = 163. Collector unchanged; no in_combat / order / supply.ratio emission.

## Next independent block

Bind a current-combat reader (CLandCombat* / IsInCombat) if one exists, without promoting false from the empty GS_COMBATS array. Bind commandlist element type at +8 only when a command object is present, or from the official element serializer alone if that is enough to fix the `order` shape. Continue supply scale / `in_supply` / `isolated` only with an official 0–1 getter or a named token. Independently: `formation` and `leaders.assigned_to` (`is_assigned` 0x385b). Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

This empty peace scene cannot finish the `in_combat` / `order.type` promotions. Minimal user condition, only when those fields must be contrasted: issue one move order to one own division, or provide a live combat — the agent will not start a war, change speed/pause, or give orders. Other work above can continue without that.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
"""
Path("research/t182_checkpoint.md").write_text(md, encoding="utf-8")
print("checkpoint written", Path("research/t182_checkpoint.md").stat().st_size)
