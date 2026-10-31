# Phase 2fa — ETH denser execlist-only RO

**Result:** `LEAF_MOVE_CAPTURED_ETH`  
**Scenario:** `ETH @1x AI-on` pid **9928**  
**UI (Asia/Shanghai box clock at capture):** 1936-01-01 05:00 (hours=5) · captured_at Asia/Shanghai **2026-10-31 11:44:39**  
**Observe:** 65.5s · polls 1 191 497 · edges 4607 · execlist_head stayed 0x0  
**Leaf:** **CStrategicRedeploymentCommand** on `stage[48]`

## Capture (RO)

| field | value |
|-------|-------|
| addr | `0x26bf0828b90` |
| vt_rva | `0x2a2d818` |
| seq | 6260 |
| tick | 1 |
| embed | **CUnitStrategicMoveAction** vt `0x2a1f7e8` |
| army_handle | `[51, 1092]` |
| province | 11874 |
| clear / move_priority | 1 / 2 |

Also saw Assign family on stage (7 sightings). No Cancel this window. No ordinary `CMoveCommand` / `CUnitMoveAction` / `CSupportAttack`.

## Gates

- **allow_post = False** (unchanged)
- Never 5x · no Post · no helper patch · no Capstone/121 re-churn

## Next cheapest (still NO ALLOW_POST)

Layout-only decode of this StrategicRedeploy embed toward ring_embed design — compare to factory MOVE (tid 0x28a2) / Cancel. Ordinary CMove sample still optional/stubbed.

## Artifacts

- `scripts/phase2fa_eth_execlist.py`
- `reports/phase2fa_leaf_move_capture.json`
- `reports/phase2fa_summary.json`
- `reports/phase2fa_eth_execlist.json` (full observe on PC)

Return Haiti: `python scripts/launch_into_map.py --speed 1 --allow-ai`
