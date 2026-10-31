# Phase 2ey — Cancel-correlated concurrent heap (RO)

**Result:** `CANCEL_EDGE_HEAP_NO_MOVE`

| Metric | Value |
|--------|-------|
| Scenario | ITA @1x pid 30680 |
| UI | 1936-01-04 13:00 |
| Observe | 90.0s |
| Cancel sights | 2 (first t=35.003706216812134) |
| Heap scans | 4 × 64MB |
| Leaf Move | 0 |
| Heap finds | {} |

Option B conclusion: Cancel-correlated heap still finds no leaf Move. Stack/direct-Execute-only Move remains unproven; more consistent with AI rarely constructing CMoveCommand objects that survive into DummyServer/heap windows. Sample gap persists. Still NO ALLOW_POST.

Next: `Factory-site / execlist RO peek (observation)` — still **NO ALLOW_POST**.

Script: `scripts/phase2ey_cancel_edge_heap.py`
