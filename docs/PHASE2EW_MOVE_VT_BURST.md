# Phase 2ew — MOVE-VT edge-burst / Cancel-edge heap (RO)

**Goal:** Capture short-lived leaf `CMoveCommand` / `CUnitMoveAction` without `ALLOW_POST`.

## VT candidates (1.19.4 RPM RVA)

| Name | RVA |
|------|-----|
| CMoveCommand | `0x2a2c790` |
| CUnitMoveAction | `0x2a1f648` |
| CStrategicRedeploymentCommand | `0x2a2d818` |
| CUnitStrategicMoveAction | `0x2a1f7e8` |
| CSupportAttackCommand | `0x2a2cb28` |
| CMassMoveCommand | `0x2a2c848` |
| CCancelMovementCommand | `0x2a2c9b8` |
| CMassCancelMovementCommand | `0x2a0fc40` |

## Scan recipe (one focused attempt)

1. Busy-poll DummyServer **pending** + Session **stage** (~0 sleep).
2. On `drain`/`exec`/`seq` edge: immediate burst (16–48) re-samples; stop burst early if leaf Move seen.
3. On `CCancelMovementCommand` sight: writable-heap scan ≤48MB for MOVE needles (object header = `base+vt`).
4. Decode via `phase2bm_midflight_ready.dump_cmd` (action embed @ `+0x28`).
5. Bounded window (~30–150s) then **STOP**. Never Post / never 5x.

## 2ew live result (ITA `-start_tag=ITA -start_speed=1`, pid 30680)

- ~30s: **634711** polls, **2110** edges, **33760** burst samples.
- Sightline: `CHourlyTickCommand` + rare `COrderAssignCommand` only.
- **No** Cancel → Cancel-edge heap **never fired**.
- **No** leaf `CMoveCommand` / `CUnitMoveAction` on stage/pending.
- Hypothesis unchanged: leaf Move too short-lived **or** never lands in DummyServer stage (direct Execute path).

Script: `scripts/phase2ew_move_burst.py`  
Reports: `reports/phase2ew_move_burst.json`, `reports/phase2ew_summary.json`
