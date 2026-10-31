# Midflight CMoveCommand capture recipe (Phase 2ei)

**Posting: DISABLED.** This document is read-only capture readiness only.
Never set `CLAUSEWITZ_ALLOW_POST`, never enable `command_queue_tool_gate`, never inject input / Post / WriteProcessMemory.

## Why this is the shortest remaining land-command blocker

| Piece | Status |
| --- | --- |
| LAND Execute catalog | **CLOSED** 121/121 (do not re-churn) |
| Post-path confidence | **CLOSED** 1.0 |
| Tooling Post ABI | **CLOSED** (2bc/2bm) |
| `midflight_CMoveCommand` live sample | **STUBBED** — needs real gameplay right-click |
| In-process Move → Dummy ring embed | **STUBBED** (needs sample buffer or Post) |
| `command_queue_tool_gate` | **CLOSED_NOT_OPENED** |
| `allow_post` / `CLAUSEWITZ_ALLOW_POST` | hard-deny |

Without a live mid-flight `CMoveCommand` (+ embedded `CUnitMoveAction`) hex dump, we cannot prove province path / unit_handle / move_priority fields against a real buffer, and we cannot close the sample gap that still blocks safe-enable.

## Watcher (armed RO)

| Field | Value |
| --- | --- |
| Script | `scripts/phase2bm_midflight_ready.py` |
| Typical arm | `python scripts/phase2bm_midflight_ready.py --seconds 86400 --interval 0.05 --heap-every 0` |
| Heartbeat | `reports/midflight_watcher_heartbeat.json` (periodic) |
| Final / capture out | `reports/phase2bm_midflight_ready.json` |
| Immediate capture | `reports/midflight_cmove_capture.json` (written the instant a Move-class hit appears) |
| Phase 2ei live pid | **36128** (re-armed after 2ei script sync if needed) |
| HOI4 | Haiti session, pid typically **2880** |
| Speed rule | pause or **1x** only — **NEVER 5x** |
| Input | **none** from tooling (DX11 ignores SendInput / PostMessage anyway) |

### What it polls (RO)

1. `CDummyServer+0x58` pending linked list (`post_abi.CDummyServer_PENDING`)
2. `CSession+0x48` stage array × `+0x54` count
3. Optional light heap VT scan — **default off** (`--heap-every 0`) to save CPU; only enable for short smoke

### Watched VTs (RVA)

| Name | VT RVA |
| --- | --- |
| `CMoveCommand` | `0x2A2C790` |
| `CUnitMoveAction` | `0x2A1F648` |
| `CStrategicRedeploymentCommand` | `0x2A2D818` |
| `CUnitStrategicMoveAction` | `0x2A1F7E8` |
| `CCancelMovementCommand` | `0x2A2C9B8` |

On `CMoveCommand` hit the watcher dumps action embed @ `cmd+0x28`: unit_handle, province_size, path_size, clear/safe, move_priority, sticky.

## Exact human capture steps (when user is awake)

1. Confirm watcher heartbeat fresh (`reports/midflight_watcher_heartbeat.json` age < 5s) and `posting=DISABLED`.
2. Keep Haiti at **pause**, then briefly set **1x** (never 5x).
3. Select one land army; **right-click** a neighboring province (real mouse / hardware).
4. Watcher should break with `caught_army_move=true` and write:
   - `reports/midflight_cmove_capture.json`
   - `reports/phase2bm_midflight_ready.json`
5. Pause again. Do **not** Post. Hand the capture JSON to the next slice for layout proof + (later) ring-embed design.

If capture stays empty: game was paused with no right-click, or the Move object was freed inside the SP tick before the 50ms poll saw it — re-arm with `--interval 0.02` for a short window only; still no inject.

## movement_dest while paused

Army path / movement destination vectors are **empty under pause** (observed 0 nonempty). Do **not** invent destinations. Retest only after a real move at 1x with a capture in hand.

## Still stubbed after capture readiness

- `ring_embed` of a hand-built or captured Move into DummyServer ring (structural Dummy `+0xa0` stride known; live Move buffer embed not proven)
- `command_queue_tool_gate` enable — **CLOSED_NOT_OPENED**
- `ALLOW_POST` / `CLAUSEWITZ_ALLOW_POST`
- Helper patch / Post inject / HourlyTick / GameSpeed writes

## Rejected (do not revive)

- org/str @ `CArmy+0x520` / `+0x6ec`
- `CProvince+0x58` as controller-country tag
- `CFront` multi-slot / `>0x90` bleed
- army↔front via controller/FS provinces while paused

## Naval / production

Out of scope for this capture path.

## Phase 2em strengthen (edge-burst + sightline) �� 2026-10-31

**Still CLOSED for Post.** `allow_post` hard-False. No inject / right-click asked.

### What changed
- `--burst-on-edge N` (default 12): on drain/exec/seq advance, immediately re-sample pending+stage N times (no sleep) to catch short-lived cmds at 1x.
- `--interval 0.02` preferred for long arm (was 0.05).
- Sightline JSON: `reports/midflight_watcher_sightline.json` counts **any** watched VT (HourlyTick/Orders/Move��); Move still the only break/capture class.
- Heartbeat phase `2em_midflight_heartbeat` includes `sight_counts`, `edge_events`, `burst_samples`, `sightline_ok`.

### Live smoke (25s @ 1x Haiti, -noai)
| Metric | Value |
| --- | --- |
| polls | 1185 |
| edge_events | 1182 |
| burst_samples | 14184 |
| sight_counts | **CHourlyTickCommand: 289** (stage[0]) |
| caught_army_move | false (expected; no right-click / -noai) |
| allow_post | False |

**Proof:** RO queue sightline works at 1x �� HourlyTick is visible midflight via stage under edge-burst. Move sample remains the blocker; when a real right-click happens, capture path is tighter.

### Re-arm
```
python scripts/phase2bm_midflight_ready.py --seconds 86400 --interval 0.02 --heap-every 0 --burst-on-edge 12
```

## Phase 2eo — full action-embed decode on capture — 2026-10-31

**Still no Post / no right-click ask.** Watcher remains RO-armed.

When a move-like cmd appears, dump_cmd now records full fields from cmd_layout:

| Object | Fields decoded |
| --- | --- |
| CMoveCommand embed @+0x28 | CUnitMoveAction: unit_handle, province_arr/size, path_arr/size, clear/safe/safe_until_end/safe_nonsafe_fb/avoid, move_priority, sticky, type_id@+8 |
| standalone CUnitMoveAction | same via ction_fields |
| CStrategicRedeploymentCommand embed | army_handle, province, clear, move_priority |
| CCancelMovementCommand | units_data, units_count, sticky |

Smoke @ 1x: HourlyTick sightline still OK; Move sample still absent (expected under -noai). Instant capture JSON will carry phase_decode=2eo + full embed when Move hits.

## Phase 2es note (AI / substitutes)

- Current preferred launch for clock proof: `-start_tag=HAI -start_speed=1` (**no** `-noai`). AI-on alone does **not** produce peacetime Haiti land `CMoveCommand`.
- Watcher WATCH expanded for substitute land VTs (attack/retreat/order/frontline family). Sightline may count them; Move-break still only on Move-class names.
- Do **not** enable Post to force a move sample.

## Phase 2et war-start path (ETH)

Preferred RO path when peacetime Haiti yields only `CHourlyTickCommand`:

```text
python scripts/phase2et_war_midflight.py --tag ETH --speed 1 --observe-seconds 180
```

Equiv CLI: `-gdpr-compliant -start_tag=ETH -start_speed=1` (AI on). Never 5x.

**Observed (2et):** `COrderUnassignCommand` ×2 midflight; `CMoveCommand` still absent.

Return to Haiti: `python scripts/launch_into_map.py --speed 1 --allow-ai`.

## Phase 2eu — Cancel ≠ Move

Longer ETH@1x observe captured **`CCancelMovementCommand`** into `midflight_cmove_capture.json` because Cancel is in `ARMY_MOVE_NAMES`. Treat as Move-adjacent proof only; leaf `CMoveCommand` still missing.

If ETH stays Cancel-only: switch to ITA attacker:
```text
python scripts/phase2et_war_midflight.py --tag ITA --speed 1 --observe-seconds 240
```
