# t177 checkpoint — 15a93d0 daily caller and r9 (production+0x200 remaining share)

Authorization: t169u still valid. Read-only live attach to HOI4 1.19.5.0.7c6c pid 26976 (ETH index 44, 1x, 1936-01-01 hour 12, hour tick 60759371). Process rechecked in-game before scanning. No memory write, no Post, no campaign or speed change, no save I/O, no commit/push.

## Session

Same live scene as t171–t176. Observation evidence still t171 captures (collector unchanged). Official inventory not rewritten: 116 fields, 14 tables, 3 columns, 41/75, SHA256 4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f. Tests 130 passed (122 prior + 8 t177). complete_input=false.

## Non-ctor caller of CReinforcementStatus slot 2

15a93d0 still has no E8/E9 callers; the call is virtual. The first bound non-ctor caller is **d71b60 at `0xd723b6`**: `call [vtable+0x10]` with `r8=type`, `r9=rdi` (remaining offered), `rdx=out`. For a CReinforcementStatus that is 15a93d0.

Call chain (profiler strings + live classes):

1. **1eae60** is `gamestate.daily`. It loops countries at `[GS+0x310][i]` and calls **72f220**.
2. **72f220** (country daily) does `d71810(country+0xf70, country+0xf78, country+0xf80, country+0xfd0)`.
3. **d71810** is profiled `deployment.daily`. `this` is **CDeploymentStatus**. Live: `country+0xf70 = CDeploymentStatus 0x26c4c4d41b0`, `+0xf78 = CReinforcementStatus 0x26c49c0c140`, `+0xf80 = CArmyUpgradesStatus 0x26c49c0b970`, `+0xfd0 = CCountryOccupationStatus 0x26c4c4d4410`. Its first callee is **d71b60** with those four arguments (`rdx` is the reinforcement status, saved at `[rbp+0x1008]`).

## r9 / offered for non-air types

d71b60 reads `CProductionStatus` from `[CDeploymentStatus+0x118]+0xf68` (the country), then `1095760(production+0x200, out-list)`. 1095760 walks the pool’s present rows at `+0x20`, stride 16 `{type, qty FIXED}`, skipping `qty==0`.

For each present type with `qty>0`, d71b60 sets `rdi = qty` and builds an acceptor list with **d6f140(list, object, type)**:

- d6f140 calls `object.slot1(out, type)`, stores the want at `object+0x10`, and appends the object only if want > 0.
- Objects offered to d6f140 include CCountryResources (`country+0x11f8`), **CReinforcementStatus**, **CCountryOccupationStatus**, **CArmyUpgradesStatus**, plus lists on CDeploymentStatus (`+0x60`, `+0x78`, `+0x90`) and related holders.

The list is sorted, then for each acceptor: `slot2(out, type, r9=rdi); rdi = *out`. So **15a93d0’s r9 is the remaining share of that type’s production+0x200 quantity after earlier acceptors** (upgrades, occupation, resources, deployment lists, …). Combined with t176, non-air cb8e80 then passes that r9 through unchanged, and 15a92f0 does `give = min(max(0, need − produced), offered)`.

This does **not** authorize `produced = min(need, stockpile)` as a live predictor. The bound path is **daily**, not an identified hourly path. The live scene is hour 12; `production+0x200` still has no infantry_equipment row, so this daily path would not offer infantry now. produced=3 remains the t170/t171 snapshot from after the completed hour, not a current-stock cross-check. 140b9c0 remains the logistics mode 1/0/6 wrapper and is not this accept path. An additional hourly accept caller is not ruled out.

## What was not promoted

- Official 1409810 infantry total 77 still has no campaign-stored non-UI cross-check.
- `[1835]` is still only this hour’s official contributor, not a confirmed `affected_unit_ids` contract.
- `world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` were not written into the official inventory and are not emitted by the collector.
- No later-hour slots were tested; the campaign was not advanced.

## Artifacts

- research/t177_checkpoint.md
- research/t177_session_recheck.json
- research/t177_slot2_daily_caller.json
- research/t177_country_statuses_live.json
- research/t177_d71810_e8.json
- research/t177_f78_qword_and_e8.json
- research/t177_validation_summary.json
- research/t177_document_update_verification.json
- listings: research/_t177_clip_d71810.txt, d71b60, d6f140, 1095760, 72f220 window, 1eae60
- offsets key: `reinforcement_slot2_daily_t177`
- tests: research/test_t177_input_slot2_daily_caller.py (8 cases; suite 130 OK)

## Next independent block

Determine whether a **non-daily / hourly** accept path also calls CReinforcementStatus slot 2 (ce4fc0 / 140b9c0 did not in this batch). If daily is the only accept, say so, and treat produced prediction as a pre-daily stock remaining-share formula — not a live `min(need, current stock)` after the type has left the pool. Continue looking for a non-UI stored 1409810 total that can cross-check 77. `affected_unit_ids` still needs a contract meaning (this-hour official contributors vs all short fielded divisions). Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not promote 77 or [1835] without a stored official cross-check and that contract confirmation. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
