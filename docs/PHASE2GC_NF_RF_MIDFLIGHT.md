# Phase 2gc — Bounded NF/RF midflight (ITA @1x)

**Slice:** B (war-dense relaunch too heavy). A skipped.  
**allow_post:** False. Never 5x. No Post / inject / tool-gate / 2fb / Capstone.

## Result

`nf_rf_midflight_empty_window`

Bounded **75s** @1x ITA: **777** polls of DummyServer pending + session stage + periodic writable-heap VT scans for:

- `COrderNewFallbackCommand` VT `0x2a84c80`
- `COrderReplaceFallbackCommands` VT `0x2a84d38`
- context: AG fallback / Assign / Execute / NewFront

**Honest empty:** zero NF/RF captures. Peace-time ITA this window does not emit fallback order cmds onto pending/stage/heap.

## RO ceiling (this slice)

Without a war-dense relaunch (or player-issued fallback), midflight RO cannot deepen NF subject hex beyond the 2fl/2fm static field map. Next cheapest NON-Post progress needs war-dense ETH/ITA or a named CArmy path observe under movement.

## Live

```json
{
  "pid": 34188,
  "hours": 316,
  "ui_date": "1936-01-14 04:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ITA@1x bounded NF/RF midflight (no Post)"
}
```

**Next shortest NON-Post blocker:** war-dense ETH/ITA relaunch for NF/RF live hex OR named CArmy path — still **NO ALLOW_POST**.

Script: `scripts/phase2gc_nf_rf_midflight.py`
