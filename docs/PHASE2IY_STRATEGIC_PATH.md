# Phase 2iy — one strategic order shows up on the army path

**Result:** `PATH_CONTAINS_DEST`

Army **1042** was ordered to province **758** after action IsValid (`vt+0x48` = `0x12c2c20`) returned 1. Immediately after `FN_CMD_QUEUE_POST` returned 1, `CArmy+0x200` ended at **758**. Before the call the path was `[9717]`.

## Do not call the command-slot thunk

`CStrategicRedeploymentCommand` vt+`0x48` (`0x1402260`) is not a bool check. It tail-jumps to the action **Execute** slot (`vt+0x50` = `0x12c3190`). Calling it off the game thread killed `hoi4.exe`. IsValid is the action function, with `rcx = cmd+0x28`.

## Date

`G_GAMESTATE+0x478` is the year. `+0x484` is days since 1 January of that year, not hours since 1936-01-01. Day index 229 is **1942-08-18**.

## Recovery

The crash was recovered with `-start_save=autosave -start_speed=1`. That autosave is the monthly save **意大利 1942.8.1**, not the unsaved 8 月 18 日 moment.

*Phase 2iy · 2026-11-01*
