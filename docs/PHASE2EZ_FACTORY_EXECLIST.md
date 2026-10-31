# Phase 2ez — MOVE factory-site + execlist RO

**Result:** `FACTORY_LOOKUP_PROOF_EXECLIST_EMPTY_NO_LIVE_MOVE`  
**allow_post:** False

## A) Factory birth path (RO, live-proven)

| Item | Value |
|------|-------|
| CMoveCommand factory | `0x13fb000` — `mov ecx,0x88` then allocator; size matches layout |
| factory_lookup | `0x22d8d20`, table `0x35011e0`, idx=`tid-0x2328` |
| MOVE tid `0x28a2` → idx 1402 | slot **matches** factory `0x13fb000` |
| Cancel / SupportAttack slots | **match** factories |
| Execute thunk `0x13fc990` | `[cmd+0x28]` → `jmp [vt+0x48]` into **CUnitMoveAction.execute `0x12c2670`** |
| Direct E8 xrefs to factory | **0** in scanned windows — expected (table-indirect) |

Disasm: `reports/phase2ez_factory_disasm.json`  
Lookup proof: `reports/phase2ez_factory_lookup_proof.json`

## B) Execlist observe (45s ITA@1x)

- `CDummyServer+0x40` execlist **head = 0** throughout
- Stage: HourlyTick + rare Assign only — **no leaf Move**

## Conclusion

Birth/Execute path for Move is catalog-closed RO via factory_lookup → factory → Post → Dummy → Execute thunk → action.  
**Live midflight Move buffer still missing** under ITA AI traffic.

## Next cheapest

Accept Move sample gap OR ETH denser Cancel/Move window (execlist-head-only) — still **NO ALLOW_POST**. Do not Capstone/121 re-churn.
