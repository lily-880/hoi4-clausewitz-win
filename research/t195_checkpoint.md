# t195 checkpoint — new pid 8500 probe, move scaffold succeeded, COrderGroupCommand Post timed out and the process crashed

Authorization: [pt181u] + [pt180u]. Previous live process 26976 was gone after the laptop reconnect. Continue under standing write/Post authority with pause/1x only, no save I/O, no commit/push. Rebind every live handle to the new pid. Do not assume the old ETH 1936-01-01 contrasts were still present.

## Session probe (read-only, before any t195 write)

Confirmed on LAPTOP-6FQIF6OJ, machineId `a849f760-4114-424f-af9c-d10eef8ca3e8`:

- hoi4.exe **pid 8500** (26976 gone)
- Windows 1.19.5.0.7c6c, exe SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`
- New ASLR base `0x7ff7a91c0000`
- New live objects: `CGameState 0x2baa5e7eaf0`, `CCountry 0x2baca590b60`, `CInGameIdler 0x2bb8bca7a50`
- Player **ETH** index 44, date **1936-01-01 12:00** Asia/Shanghai, hour tick 60759371
- Official pause `CInGameIdler+0x6c1=1`, speed index 0, hour progress 0.0
- 21 own divisions ids 1829–1849, theatre handle **{67, 43}**
- **Legacy contrasts were gone**: 1829 was again at 5010 with an **empty** path; no COrdersGroup, no CArmyGroup, no COrderInstance, all 20 leaders unassigned

This was a fresh start of the same campaign date, not a resume of the t193 objects. Old 26976 pointers were not reused.

## Safe subjects chosen for scaffolding

- Move: unit **1829** interior **5010 → 8036** (live land neighbors, not ITA-adjacent)
- Army member (planned, not completed): unit **1838** at 7980
- Plan vertices (planned, not posted): interior pair **5097 / 7944**, not the ITA-border provinces 13237/13238 and not the move pair
- Spare unit for a later unit-leader dry-run (not reached): 1846 at 12757

Factory table on this pid matched the 1.19.5 RVAs already bound in t192–t194 (Move 0x13fb070, OrderGroup 0x18d0140 size 0x60, SetArmyLeader 0x18d0c10, ArmyGroup 0x18cf780, NewRoot 0x18d0440, NewFront 0x18d03b0, Assign 0x18cfd10, Execute 0x18d00e0, PauseGame 0xe53a00). t194 official-entry disassembly was reused; it was not redone.

## Commands that actually ran

### 1. CMoveCommand — succeeded, stayed paused

`calling/move_order.move(1829, 8036)`:

- dry-run `DRY_RUN_VALID`
- one live Post, gate opened only for this call, `PATH_CONTAINS_DEST`, `post_rax=1`, `post_wait=0`, `province_buf_kind=ucrt_malloc`
- Readback: unit 1829 still in 5010, `CArmy+0x200=[8036]`, full_path empty, commandlist empty, progress 0
- Pause still 1, speed still 0, process still alive
- This was scaffolding only. `path_province_ids` was already promoted in t191 and was **not** re-promoted

### 2. COrderGroupCommand — dry-run valid, Post timed out, process later crashed

Packing followed the t192 recipe: unit handle `{0x33, 1838}` in a ucrt vector at `+0x30`, theatre `{67, 43}` at `+0x48`. Dry-run `IsValid=1`.

One Post, `wait=258` (WAIT_TIMEOUT, 8000 ms), `post_rax=0`, remote stub **not** freed (correct on timeout). Immediately after the timeout, theatre `+0x80` was still empty (no COrdersGroup). Gate was closed. Pause flag still read as 1 at that moment.

A later read-only recheck found pid 8500 **not alive**. `GetExitCodeProcess` = **3221225477** (`0xC0000005`, STATUS_ACCESS_VIOLATION). No army appeared. Unit 1829 path was still `[8036]` in the last readable snapshot; 1838 had no orders-group pointer. No further Posts were issued. The game was not relaunched, and no retry loop was attempted.

## What was not done

Because the process died after the OrderGroup timeout, the rest of the planned minimal sequence was **not** started:

- CSetArmyLeaderCommand (army or army group)
- CArmyGroupCommand
- COrderNewRootCommand / COrderNewFrontCommand (vertex_province_ids)
- COrderAssignCommand
- COrderExecuteCommand
- CPauseGame 1x observation for `order.type` / `target_province_ids` / `eta`
- CSetArmyLeader dry-run onto a single division

## Promotions

**None.** Already-promoted path / army / army_group / plan_id fields were not withdrawn and were not re-promoted. Remaining t194 targets (`plans.type`, `vertex_province_ids`, `assigned_unit_ids`, `executing`, `axis_province_ids`, `plans.status`, `order.type` / `target` / `eta`, `assigned_to` kind=unit) stay 未验证.

Official inventory on D: was **not** written. Still 14 tables, 116 fields, 3 columns, **62 verified / 54 unverified**, SHA256 `e4b7db714556524ac084c55367414e5f3ac55feb4b904bbb2fdec8ea866b75f0`. `complete_input` remains false.

## Post / output lessons

- A new pid requires a full session rebind. Date/tag can look identical to the old campaign while every object pointer and every contrast is new.
- Move factory 1402 still accepts an interior neighbor destination while officially paused, with the same ucrt_malloc path as t191.
- **Do not wholesale-zero a factory object from +0x8 to the end.** This block did that after `COrderGroupCommand` returned, then posted. t192 packed only the known fields and left the rest of the factory initialisation alone. The unused-field zeroing lesson from t193 (`+0x60` / `+0x6c` leftovers on NewRoot) means *explicitly clear known leftover pack slots*, not wipe bytes the factory may have already initialised. This is the leading suspicion for the timeout + `0xC0000005` crash; it is not proven, and the Post was **not** retried.
- On WAIT_TIMEOUT the remote stub must be leaked, not freed. That part was followed.
- After a timed-out Post, do not issue another command and do not assume the queue is idle. Recheck process health first.

## Stop state

- hoi4.exe pid 8500 has **exited** with `0xC0000005`. There is no live session to restore to official pause.
- Post gate is closed (`allow_post()=false`, `safe_land_tool_gate.OPEN` absent).
- No save I/O, no commit/push.
- Next start must be a new pid, a new read-only probe, and a new handle bind. If the user relaunches, rebuild scaffolding again, but **do not** zero whole factory objects; pack like t192/t193. Do not retry the failed OrderGroup Post against a dead process.

## Artifacts

- research/t195_session_recheck.json
- research/t195_neighbors_factories.json
- research/t195_scaffold_post.json
- research/t195_after_og_timeout.json
- research/t195_process_after_crash.json
- research/t195_checkpoint.md
- research/_t195_*.py helper scripts
