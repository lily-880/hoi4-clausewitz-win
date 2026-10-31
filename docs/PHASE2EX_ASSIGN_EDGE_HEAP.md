# Phase 2ex — Assign-edge heap for leaf MOVE (RO)

**Goal:** Catch short-lived `CMoveCommand` / `CUnitMoveAction` on Assign/Unassign edge without Post.

## Live result (ITA pid 30680 @1x, Asia/Shanghai ~11:30–11:31)

| Metric | Value |
|--------|-------|
| Observe | 90s |
| Polls / edges | 1410895 / 5292 |
| Heap scans | 6 × 64MB writable |
| Assign | ×17 (first ~1.2s, stage) |
| Unassign | ×12 |
| Cancel | ×3 (vt `0x2a2c9b8` = cmd_layout) |
| Leaf Move (stage/pending/heap) | **0** |

## Conclusion

- Assign-edge heap **armed and fired**; **no** MOVE VT needles in heap windows.
- Cancel also on DummyServer stage — Post→Dummy path live for order/Cancel classes.
- Option B catalog: **no proven DummyServer-bypass** for Move (`reports/phase2ex_direct_execute_ro.json`).

## Next cheapest (do not run endless)

Cancel-correlated concurrent heap — see `next_cheapest_recipe` in that JSON. Still **NO ALLOW_POST**.

Script: `scripts/phase2ex_assign_edge_heap.py`
