# t176 checkpoint — cb8e80 offered is air-gated; non-air r9 is pass-through

Authorization: t169u still valid. Read-only live attach to HOI4 1.19.5.0.7c6c pid 26976 (ETH index 44, 1x, 1936-01-01 hour 12, hour tick 60759371). Process rechecked in-game before scanning. No memory write, no Post, no campaign or speed change, no save I/O, no commit/push.

## Session

Same live scene as t171–t175. Observation evidence still t171 captures (collector unchanged). Official inventory not rewritten: 116 fields, 14 tables, 3 columns, 41/75, SHA256 4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f. Tests 122 passed (113 prior + 9 t176). complete_input=false.

## Offered formula (cb8e80)

t175 described cb8e80 as walking country-linked equipment sources via fe84d0/fe86c0. That walk is **air-only**.

`cf4e10` is `IsAir()`: walk parent via `+0x538`, `or` flags at `+0x5a0`/`+0x5a8`, clean bits with `100f620`, then `test 0x1f0037fc00`. This is proven by the debug asserts in fe84d0 / fe86c0 / fe1160 / fe1590: `pVariant->GetType().IsAir() && "Expected air equipment."` A second assert requires matching mission types.

cb8e80 (`0xcb8f4c`) calls `cf4e10([type+0x3f0])`. If false, it jumps to `0xcb9306` and does `*out = rbx` where rbx is the incoming r9 (reset from the home space before any take). **No** `[717410_result+0x58]` walk, **no** fe84d0/fe86c0.

If true (air), it builds two variant lists from holders at `[717410_result+0x58]` (inner list `+0x28`, gated by `10948a0(holder+0x20+0x310, type+0x3f0)` and type mask `type+0x408` vs `holder+0x20+0x5a8`). fe1160 sends an item to list A (fe84d0); fe1590 to list B (fe86c0). Each of those functions computes `take` in integer equipment units, capped by variant availability (`fe35d0(item) − item+0x7c` or `item+0x7c`), then `*out = incoming − take * 0x186a0` (FIXED 100000). They are not pure queries: `fdf340` does `1092b70(variant+0x1d8, type, take*FIXED)` and writes `variant+0x7c`; fe86c0 also does `variant+0x88 += take`. Do not execute them against the live process. The value 15a93d0 then passes to 15a16a0 is the leftover r9 after those takes.

Live infantry_equipment `0x26bc2d15050`: flags `+0x5a0 = 0x20`, `+0x5a8 = 0`, IsAir = **false**. Therefore **this scene’s offered is exactly the r9 passed into 15a93d0 / cb8e80**. It is still not a read of `production+0x200` (present types remain only `train_equipment=5`). Do not write `produced = min(need, stockpile)`.

The magic constant `0x29f16b11c6d1e109` with `sar 0xe` is signed division by 0x186a0 (FIXED), confirmed by the inverse `take * -0x186a0 + incoming` store.

## 15a93d0 caller still virtual

cb8e80 has exactly one E8 caller: 15a93d0. 15a16a0 has exactly two: 15a92c0 and 15a93d0. 15a93d0 has no E8/E9 callers. Its only preferred-base hit is CReinforcementStatus vtable `0x2a4b878` slot 2 at `0x2a4b888`. File LEAs of that vtable remain ctor `15a4a70` and dtor `15a5180`.

`717400` is the two-instruction getter `mov rax, [rcx+0xf78]; ret`. Live: `CCountry+0xf78` is the same CReinforcementStatus `0x26c49c0c140`. `CCountry+8 = 44` (ETH index), which is the 717410 handle used with `c08790` into `global+0x690`. The eight E8 callers of 717400 are **not** the accept path: ctor `15a4620`, UI/description `15a8180`, status `+8` get/set, and the 1409810-family walks `1409951` / `140a0e5` that sum `10948a0(request+0x78)` over `status+0x20` groups (need, same FIXED caps as 1409810). For unit 1835 that need term is 80, so this is **not** by itself a stored cross-check of official 77.

A nearby sibling dispatcher `15a8f00` (same list-at-`+0x20`, slot 1 then slot 2, shared offered) is **CArmyUpgradesStatus** vtable `0x2a4ba28` slot 2, not the reinforcement hourly driver. `15a8cf0` is CArmyUpgradesRequests slot 2.

## What was not promoted

- Official 1409810 infantry total 77 still has no campaign-stored non-UI cross-check.
- `[1835]` is still only this hour’s official contributor, not a confirmed `affected_unit_ids` contract.
- `world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` were not written into the official inventory and are not emitted by the collector.
- No later-hour slots were tested; the campaign was not advanced.

## Artifacts

- research/t176_checkpoint.md
- research/t176_session_recheck.json
- research/t176_offered_semantics.json
- research/t176_static_refs.json
- research/t176_717400_callers.json
- research/t176_vtables_and_isair.json
- research/t176_validation_summary.json
- research/t176_document_update_verification.json
- listings: research/_t176_clip_fe84d0.txt, fe86c0, fe6550, fe1160, fe1590, cf4e10_full, 10948a0_full, fdf340, 717410_full, 15a8f00 (as `_t176_clip_0x15a8f00.txt`), 717400
- strings: research/_t176_strings_fe84d0.json (and fe86c0/fe1160/fe1590)
- offsets key: `reinforcement_offered_t176`
- tests: research/test_t176_input_offered_isair.py (9 cases; suite 122 OK)

## Next independent block

Bind the **non-ctor virtual caller of CReinforcementStatus slot 2 / 15a93d0** and reduce the **r9 it passes** (that value *is* offered for non-air types, including infantry). A likely shape is a stock or budget query whose result is passed as r9, but do not assume it is `production+0x200` until the caller is bound. Continue looking for a non-UI stored 1409810 total that can cross-check 77. `affected_unit_ids` still needs a contract meaning (this-hour official contributors vs all short fielded divisions). Do not write `produced = min(need, stockpile)`. Do not promote 77 or [1835] without a stored official cross-check and that contract confirmation. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
