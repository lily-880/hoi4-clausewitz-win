# Phase 2gj — ordinary CMove offline layout polish

**Result:** `MOVE_OFFLINE_SKELETON_PASS_FACTORY1402_MATCH_OBSERVE_EMPTY`  
**allow_post:** **False** · 2fb recipe **NOT executed** · never 5x

## A) Offline MOVE skeleton (catalog)

| check | value |
|-------|-------|
| status | **SKELETON_PASS_NO_LIVE_HEX** |
| bit_identical | **False** (no live CMove hex) |
| size / factory_idx | `0x88` / **1402** |
| factory RVA | `0x13fb000` |
| type_id / VT | `0x28a2` / `0x2a2c790` |
| action embed | `@+0x28` VT `0x2a1f648` type `0x3648` |

Shared header (Strategic + Cancel live): tick`@+0xC`; seq`@+0x1C` echoed `@+0x20`; embed `@+0x28`.

Action fields needing game alloc (blocker vs Strategic scalar): `province_arr`, `path_arr`.

## B) Live factory_idx 1402 RO

See `reports/phase2gj_move_offline_layout_polish.json` → `live.factory_ro`.

## C) Brief ≤45s CMove observe

Pending/stage VT sight only — no heap marathon. Honest empty is success for this slice.

## Harness gap

In-process serialize→recreate→ring embed still **STUBBED**. Offline Strategic remains the only bit_identical rebuild (2fd). Ordinary CMove still needs a midflight hex sample (human gameplay; agent must not ask/inject).

**Gate CLOSED. still NO ALLOW_POST.**

Artifacts: `reports/phase2gj_*.json`, `scripts/phase2gj_move_offline_layout_polish.py`
