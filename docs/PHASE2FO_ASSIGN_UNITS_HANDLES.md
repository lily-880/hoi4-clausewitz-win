# Phase 2fo — Assign units.data handle decode

**Result:** `ASSIGN_UNITS_HANDLES_DECODED`  
**Base:** `0a1105a` (2fn) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## Element layout (proven RO)

`units.data[i]` = `{u32 type, u32 index}` stride **8** (same as `unit_handle` `[ty, ix]`).

`HANDLE_TYPE_ARMY = 0x33` (51). Live army-typed lists: `[[51, 1346], [51, 1803], [51, 1810], [51, 1811], [51, 1816], [51, 1815]]`

## Prior 2fn reread

ok=3 / rows=4

## Sight

elapsed=20.0 assign_handles=2  
unassign_handles=0 fallback=False  
counts={"CHourlyTickCommand": 17068, "COrderAssignCommand": 2}

```json
{
  "pid": 34188,
  "hours": 157,
  "ui_date": "1936-01-07 13:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ITA@1x Assign units.data handle decode (no Post)"
}
```


## Credibility

- **Authoritative:** 2fo on-stage Assign (size=4) — all four elems `[51, ix]` = HANDLE_TYPE_ARMY; `resolve_handle` OK; `CArmy+0x18` echo matches.
- **Also good:** 2fo on-stage Assign (size=2) — one ARMY `[51, 1803]` + one non-ARMY `[4713, 3906]` (unresolved; type≠0x33; no invent).
- **LOW:** 2fn units.data reread — heap reuse; mixed garbage + one surviving ARMY. Prefer on-stage decode.

Live ARMY lists (authoritative): `[51,1810] [51,1811] [51,1816] [51,1815]` and `[51,1803]`.

**Next shortest blocker (NON-Post):** NON-Post: NewFallback/ReplaceFallback midflight subject type-id OR Assign units.data→order subject cross-link; still NO ALLOW_POST
