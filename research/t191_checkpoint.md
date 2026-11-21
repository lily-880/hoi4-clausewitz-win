# t191 checkpoint — one-shot interior Move Post; promote path_province_ids only

Authorization: [pt180u] write/Post and issue a minimal own-division order to auto-validate remaining input fields and learn the Post/output path. Pause/1x only; no save I/O; no commit/push. Fog rule unchanged.

## Session

Confirmed before the command: pid 26976, HOI4 Windows 1.19.5.0.7c6c, ETH 44, 1936-01-01 12:00, hour tick 60759371, official pause CInGameIdler+0x6c1=1, speed index 0 (1x). Same CGameState `0x26c259d0ff0` / CCountry `0x26c4b672530` as t187–t190. GS+0x268 combats still empty. After the Post the clock, pause bit, and speed notch were unchanged; the process stayed alive (exit 259).

## Safe subject

Own division **1829** in ETH-controlled interior province **5010** (all land neighbors ETH, not ITA-adjacent). Destination **8036**, a land neighbor, also ETH interior, not ITA-adjacent, no river crossing, no own unit already there. Addis 1984 and the ITA-border stacks were not touched.

## Post machinery (reused, then rebound)

Existing `calling/move_order.py` factory 1402 + `FN_CMD_QUEUE_POST` + ucrt_malloc province buffer, gated by `CLAUSEWITZ_ALLOW_POST=1` and `research/safe_land_tool_gate.OPEN`. The first dry-run with the 1.19.4 constants returned `ARMY_NOT_FOUND` without posting: live CArmy vtable is `0x29d6d98` (profile and RTTI), not `0x29d6d68`.

1.19.5 rebase, all read-only before the one-shot:

- Live `TYPEID_FACTORY_TABLE` (`0x35011e0`) idx 1402 → factory `0x13fb070` (old `0x13fb000` +0x70). Head is still `mov ecx, 0x88` (command size unchanged).
- RTTI vtables: `CMoveCommand 0x2a2cde0`, `CUnitMoveAction 0x2a1fac8`.
- Action IsValid = action vt+0x50 = `0x12c2d10` (old `0x12c2ca0` +0x70).
- `FN_CMD_QUEUE_POST` = `0x22c4250`. Pdata function uses session gates `+0x725` / `+0x726` / `+0x6cc`, then `mov rcx, [rbx+0x40]; call [vt+0x28]` into live `CDummyServer` sink `0x23f5d40`. `G_SESSION` itself was already valid on this build.
- Gate opened only for the live Post, then removed. `allow_post()` is false again.

## Command and readback

1. Dry-run `move(1829, 8036)` → `DRY_RUN_VALID`.
2. One live Post, same arguments, `province_buf_kind=ucrt_malloc` → `PATH_CONTAINS_DEST`, `post_rax=1`, `post_wait=0`.
3. Stayed paused. Did not unpause, did not change speed, did not issue Cancel (the path is the contrast sample). Cancel 1415 remains the documented reverse; its 1.19.5 factory is `0x13fad50` but was not used.

Live readback (and a later confirmation pass): unit 1829 still in 5010; `CArmy+0x200` path = `[8036]` (size 1); the other 20 own divisions still have empty paths. `CArmy+0x220` full_path empty. `CArmy+0x2c0` commandlist size 0. `CArmy+0x240` movement_progress 0.

## Promoted

- `world.own_units.order.path_province_ids` — official `CArmy+0x200` ordered u32 province array. First non-empty live acceptance. Resolver: `input_loaded_fields.unit_movement_path`. Empty path is still not idle.

Official inventory (D: 14 tables, 116 fields, 3 columns): **48 verified / 68 unverified**. SHA256 `e38f089d93bbbfa7dd081966bc7f43ada13bd960f74513e2c38c55861bc4c9fc`. `complete_input` remains false. The collector still does not emit a complete `order` object (schema requires type, target, and path together).

## Not promoted (honest)

- `order.type` — commandlist still empty, so element+8 is still unmapped onto OrderType. A nonempty path is not `type=move`.
- `order.target_province_ids` — `full_path` stayed empty; do not infer target as `path[-1]`.
- `order.eta` — movement_progress stayed 0 while paused (the division has not started walking).
- Leaders `assigned_to` and formation / `world.armies` — not attempted in this block. The brief allowed an optional second minimal step only if still safe; the move already gave the path contrast, so that step is left for a later checkpoint.
- Combat / supply / manpower gap / damaged buildings / crises — deferred as instructed.

## Post / output notes learned this block

- The working land Post path is: factory 1402 allocates `CMoveCommand` (size 0x88) with embedded `CUnitMoveAction` at +0x28; pack handle `type=0x33` + army index at action+0x10; pack a **ucrt malloc** u32[1] destination at action+0x18 (VirtualAllocEx here heap-corrupts on vector dtor); action+0x50 clear flag and +0x58 move priority 2 (player order); IsValid(action); `FN_CMD_QUEUE_POST(session, cmd, r8=1)`.
- Province destination must be on the CRT heap; the 4KB buffer is intentionally leaked after a live Post so the queued command cannot UAF it.
- On WAIT_TIMEOUT the remote thunk pages must be leaked, not VirtualFreeEx'd, while the thread may still be inside Post.
- Command queue execute ran while officially paused: path appeared immediately, the division did not leave 5010, the hour tick did not advance. No 1x unpause was required for this acceptance.
- 1.19.4 Post RVAs must be rebound on 1.19.5 before calling anything; the first dry-run failure was a vtable pin, not a refused order.
- One-shot gate discipline from earlier land Post work still applies: env + `safe_land_tool_gate.OPEN`, then delete the marker.

## Artifacts

- research/t191_checkpoint.md
- research/t191_session_recheck.json
- research/t191_live_units.json
- research/t191_vt_compare.json
- research/t191_rtti_move_vts.json
- research/t191_factory_slots.json
- research/t191_post_rva.json
- research/t191_post_disasm.json
- research/_t191_clip_fn_post_0x22c4250.txt
- research/t191_move_post.json
- research/t191_live_path.json
- research/t191_move_path.json
- research/t191_inventory_sha256.json
- offsets key: `move_path_t191`
- tests: research/test_t191_input_move_path.py
- calling/move_order.py and calling/post_abi.py 1.19.5 RVA pins
- calling/input_loaded_fields.py `unit_movement_path`
- t187–t190 inventory tests now pin their *recorded* SHA (t186 style) so later D writes do not break the suite

## Next independent block

Optional minimal next step, still pause/1x, no saves: assign one ETH general, *or* create one orders_group and put at least one own division in it, to validate `leaders.assigned_to` and `formation` / `world.armies`. Leave the 1829 path in place unless a Cancel is needed for safety. Do not start the combat / supply / building-damage / crisis block until command and formation evidence is closed. If HOI4 is gone or not in this campaign at the next resume, report and stop.
