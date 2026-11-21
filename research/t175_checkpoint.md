# t175 checkpoint — 15a92f0 callers and offered source

Authorization: t169u still valid. Read-only live attach to HOI4 1.19.5.0.7c6c pid 26976 (ETH index 44, 1x, 1936-01-01 hour 12, hour tick 60759371). Process rechecked in-game before scanning. No memory write, no Post, no campaign or speed change, no save I/O, no commit/push.

## Session

Same live scene as t171–t174. Observation evidence still t171 captures (collector unchanged). Official inventory not rewritten: 116 fields, 14 tables, 3 columns, 41/75, SHA256 4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f. Tests 113 passed (106 prior + 7 t175). complete_input=false.

## What this batch bound

t174 found no E8/E9 or raw-RVA absolute caller of 15a92f0 because vtable slots are stored as preferred-base pointers (`0x140000000 + RVA`, e.g. `0x1415a92f0`). Scanning `.rdata` with that encoding locates the accept function as **CReinforcementRequest vtable 0x2a4b768 slot 2** (`+0x10`). Slot 1 (`+8`) is 15a8c20 (need query: if status+0x20==0 and need>0, `*out=0x186a0`, else 0). Slot 0 is dtor 15a50d0. Secondary vtable at request+0x18 is 0x2a4b7a0.

Call chain (static + live):

1. **CReinforcementStatus slot 2 = 15a93d0.** Live status `0x26c49c0c140`: `+0x38` is CCountry `0x26c4b672530`; `+0x20` is a list of count 1, the CArmyReinforcementRequests group `0x26cb01e6fa0` already owned in t170. 15a93d0 does `717410(status+0x38)`, then `cb8e80` writes a computed offered amount, then `15a16a0(out, type, offered, status+0x20)`.
2. **15a16a0** is a shared offer dispatcher over a pointer list: for each object, `[vtable+8]` (want/query) then `[vtable+0x10]` (accept) with the remaining offered in r9; remaining is written back.
3. **CArmyReinforcementRequests vtable 0x2a4b7f0:** slot 1 = 15a8790 (want weight via cdb4b0 / unit+0x348); slot 2 = **15a8cd0**, a 12-instruction wrapper that calls `15a9440(out, group+0x28, type, offered)`. Do not stitch the next `.pdata` fragment 15a8cf0 onto this function.
4. **15a9440** walks the request pointer list at group+0x28. At `0x15a9640` it does `rcx=*request; rax=*vtable; r9=remaining offered; r8=type; call [rax+0x10]` — that is 15a92f0 — then `rbx=*returned remaining`. Live group+0x28 count 1 is request `0x26cb1969530` (unit 1835). A later `[rax+0x10]` at `0x15a9685` is an allocator free, not the accept slot.
5. **15a92f0** (already proven in t174): `give = min(max(0, need − produced), offered)`; `1092b70(request+0x38, type, give)`; remaining = offered − give.

**15a92c0** is the same dispatcher interface for CCountryOccupationStatus and CGarrisonStatus; offered is passed in r9 and there is no cb8e80.

## Offered is not raw stockpile

cb8e80 is the offered source used by 15a93d0. It is **not** a read of `production+0x200`. It gates with `cf4e10(type+0x3f0)`, walks country-linked equipment sources at `[717410_result+0x58]`, and uses 10948a0 / fe6550 / fe1160 / fe84d0 / fe86c0, then writes rbx to `*out`. The live production+0x200 present-type set is still only `train_equipment=5`; infantry_equipment is absent after the completed hour. Therefore **produced is still not predictable as `min(need, stockpile)`**. The accept math is closed once offered is known; the offered formula itself is not yet reduced to a stockpile expression.

717410 looks up an object from `global+0x690` via a handle (`c08790`) or index 0; it is the same helper used elsewhere to resolve CCountry from a status handle, but the object it returns into cb8e80 is not assumed to be the production pool.

The **hourly / tick caller of 15a93d0** is still unbound. File LEAs of the CReinforcementStatus vtable are ctor/dtor only (15a4a70, 15a5180). The call is virtual.

## What was not promoted

- Official 1409810 infantry total 77 still has no campaign-stored non-UI cross-check.
- `[1835]` is still only this hour’s official contributor, not a confirmed `affected_unit_ids` contract (19 short fielded units exist).
- `world.shortages.equipment.demanded` / `deficit` / `affected_unit_ids` were not written into the official inventory and are not emitted by the collector.
- No later-hour slots were tested; the campaign was not advanced.

## Artifacts

- research/t175_session_recheck.json
- research/t175_15a92f0_refs_static.json
- research/t175_CReinforcementRequest_vtables.json
- research/t175_virt_slot2_parents.json
- research/t175_offered_vtables.json
- research/t175_reinforcement_status_live.json
- research/t175_group_vtable_live.json
- research/t175_offered_callers.json
- research/t175_validation_summary.json
- research/t175_document_update_verification.json
- listings: research/_t175_clip_15a8c20.txt, 15a50d0, 15a8cd0, 15a8790, 15a9440, 15a16a0, 15a93d0, 15a92c0, 717410, cb8e80_head/body
- offsets key: `reinforcement_offered_t175` in calling/tables/offsets_input_windows_1.19.5.json
- tests: research/test_t175_input_offered_callers.py (7 cases; suite 113 OK)

## Next independent block

Finish reducing **cb8e80** to a closed offered formula (which country-linked source, what 10948a0 / fe84d0 actually add, and how that relates to — or differs from — production+0x200 and 1409810), and/or bind the **non-ctor virtual caller of CReinforcementStatus slot 2 / 15a93d0** so the hourly accept is reachable without advancing the campaign. Continue looking for a non-UI stored 1409810 total that can cross-check 77. `affected_unit_ids` still needs a contract meaning (this-hour official contributors vs all short fielded divisions). Do not write `produced = min(need, stockpile)` until offered is a closed formula. Do not promote 77 or [1835] without a stored official cross-check and that contract confirmation. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
