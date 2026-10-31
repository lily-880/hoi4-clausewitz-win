# Phase 2fe — Ordinary CMove layout note (catalog only)

**Live sample:** STUBBED — not hunted this slice.  
**Catalog:** COMPLETE.

| field | value |
|-------|-------|
| vt | `0x2a2c790` |
| type_id | `0x28a2` |
| size | `0x88` |
| factory | `0x13fb000` |
| factory_idx | **1402** (formula 1402) |
| action embed | `0x28` → `CUnitMoveAction` `0x2a1f648` |

Action fields: `{"unit_handle": "0x10", "province_arr": "0x18", "province_size": "0x24", "path_arr": "0x30", "path_size": "0x3c", "clear": "0x50", "safe": "0x51", "safe_until_end": "0x52", "safe_nonsafe_fb": "0x53", "avoid": "0x55", "move_priority": "0x58", "sticky": "0x5c"}`

vs Strategic: shared execute thunk `0x13fc990`; Move needs province/path **vectors**; Strategic scalar province is cheaper for any future Post experiment.

allow_post **False**.
