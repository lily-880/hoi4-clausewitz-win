# UI clock alignment（界面时钟对齐）

**Status:** verified with player UI 2026-11-05 (Asia/Shanghai)  
**Build:** HOI4 Windows 1.19.x · ETH campaign on map  
**Evidence:** `reports/clock_align_11.json`, `clock_align_12.json`, `clock_align_12_confirmed.*`, `clock_align_13.json`

## Formula (read-only)

| UI field | Memory | Notes |
|----------|--------|-------|
| **Date** `YYYY-MM-DD` | year `@G_GAMESTATE+0x478` (i32) + day_index `@+0x484` (i32, days after Jan 1) | Confirmed: year=1936, day_index=4 → **1936-01-05** |
| **Hour** | u32 `@G_GAMESTATE+0x468` | Increments **exactly +1** each UI hour (11→12→13) |
| UI hour | `(u32(+0x468) % 24) + 1` | Gave **11, 12, 13** matching the on-screen clock |

### Discard

| Offset | Why |
|--------|-----|
| `+0x480` | Stayed **4** while UI went 11→12→13 — **not** the UI hour |
| `+0x47c` (`date_aux`) | Still hypothesis only; not day-of-month |

## Helpers

- `calling/clock.py` → `ui_date(year, day_index)`, `ui_hour(hour_tick)`
- `clausewitz_win.py status` campaign summary exposes `date_full.ui` and `date_full.ui_hour` (RO)

## Safety

Read-only. No Post. Never set game speed to 5x.
