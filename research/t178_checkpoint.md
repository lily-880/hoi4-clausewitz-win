# t178 checkpoint — no hourly CReinforcementStatus slot 2 accept; daily is the bound path

Authorization: t169u still valid. Read-only live attach to HOI4 1.19.5.0.7c6c pid 26976 (ETH index 44, 1x, 1936-01-01 hour 12, hour tick 60759371). Process rechecked in-game before scanning. No memory write, no Post, no campaign or speed change, no save I/O, no commit/push.

## Session

Same live scene as t171–t177. Observation evidence still t171 captures (collector unchanged). Official inventory not rewritten: 116 fields, 14 tables, 3 columns, 41/75, SHA256 4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f. Tests 136 passed (130 prior + 6 t178). complete_input=false.

## Hourly tick does not call slot 2 accept

`gamestate.hourly` is **1f5230** (profiler string at `0x27a0810`). It uniquely calls 1e5660, 202f30, and 1ee7f0. None of those, and none of 1f5230 itself, call d71b60, d71810, d724e0, 72f220, 15a93d0, 15aa9c0, 140b9c0, ce4fc0, 717400, 1095760, or d6f140. There is no `call [reg+0x90]` (CArmy slot 18) in the hourly function.

15a93d0 still has no E8/E9; its only preferred-base hit is CReinforcementStatus vtable slot 2. d71b60’s only E8 callers are **d71810** (daily, live status in rdx) and **d724e0**. d71810 is only called from 72f220, which is only called from gamestate.daily 1eae60. d6f140 is only called from d71b60.

**d724e0** is a shorter sibling of d71810: it still calls d71b60 then d727b0/d72540 and walks CDeploymentStatus+0x60. Its two callers (d47380, d4b860) do `xor edx/r8/r9` then `d724e0([country+0xf70])`. Incoming rdx/r8/r9 are therefore null, so d71b60’s d6f140 on CReinforcementStatus / CArmyUpgradesStatus / CCountryOccupationStatus is skipped. That path does **not** accept onto reinforcement.

## What the hour path actually does

ce4fc0 is **CArmy vtable `0x29d6d98` slot 18** (`+0x90`), the 24-hour staggered request work from t172 (no E8/E9). It is the only E8 caller of 15ab390, which calls 15aa9c0. 15aa9c0 (also reached from ce82d0 / ceb320) calls **15a26f0** (request init) and **140b9c0** (logistics modes 1/0/6), plus 15a5c80 and 1095760. Its two `call [rax+0x10]` sites (`0x15aaef8`, `0x15aafe8`) are allocator frees (`rcx`=allocator, `rdx`=buffer, no type/offered in r8/r9), not 15a93d0. So the hour work list stamps/updates requests and logistics; it does not run the accept.

CCountry’s vtable has no 15a93d0 / d71810 / 72f220 / ce4fc0 slot.

## Produced prediction (daily only)

The only bound accept that invokes CReinforcementStatus slot 2 with a live status and a stock-based r9 is **deployment.daily** (t177). Pre-daily formula, for each `production+0x200` present type with `qty>0`:

1. `offered` starts as that row’s FIXED qty.
2. Acceptors with slot-1 want>0 (resources, occupation, upgrades, deployment lists, then reinforcement if want>0) each get `slot2(..., r9=offered)` and write back the remainder.
3. For reinforcement (non-air): cb8e80 passes r9 through; `give = min(max(0, need − produced), offered)`.

This is **not** `produced = min(need, current stock)` after the type has left the pool. The live scene is hour 12; infantry_equipment is still absent from production+0x200, so the formula cannot be evaluated against the current pool for produced=3 (still t170/t171). No campaign step was taken to catch a daily boundary.

## What was not promoted

- Official 1409810 infantry total 77 still has no campaign-stored non-UI cross-check.
- `[1835]` is still only this hour’s official contributor, not a confirmed `affected_unit_ids` contract.
- `world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` were not written into the official inventory and are not emitted by the collector.

## Artifacts

- research/t178_checkpoint.md
- research/t178_session_recheck.json
- research/t178_hourly_vs_daily_accept.json
- research/t178_e8_and_strings.json
- research/t178_hourly_profile_leas.json
- research/t178_hourly_funcs.json
- research/t178_validation_summary.json
- research/t178_document_update_verification.json
- listings: research/_t178_clip_1f5230.txt, d724e0, d47380, d4b860, 15aa9c0, 1e5660, 202f30
- offsets key: `reinforcement_accept_daily_only_t178`
- tests: research/test_t178_input_hourly_no_slot2.py (6 cases; suite 136 OK)

## Next independent block

Use the pre-daily remaining-share formula only as a static prediction rule; do not treat the current empty infantry row or produced=3 as a live evaluation. Continue looking for a **non-UI stored 1409810 total** that can cross-check 77 (1409951 still sums request+0x78 need=80 for 1835, not 77). `affected_unit_ids` still needs a contract meaning (this-hour official contributors vs all short fielded divisions). Do not write `produced = min(need, stockpile)` against the current pool. Do not promote 77 or [1835] without a stored official cross-check and that contract confirmation. Do not advance the campaign to wait for the next daily tick. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
