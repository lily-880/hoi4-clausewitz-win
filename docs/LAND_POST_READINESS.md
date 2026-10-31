# Land Post-readiness (catalog-only) — Phase 2gi

**Status: CLOSED — NO Post / NO ALLOW_POST / NO tool-gate / NO recipe execute.**  
`allow_post()` hard-returns **False**. Speed: pause or **1x** only — **NEVER 5x**.

Single catalog consolidate of proven RO toward eventual land Post. Does **not** open gates.
Policy detail: `docs/SAFE_POST_ENABLE_CHECKLIST.md`.

---

## 1. Proven session / Post ABI (RO constants)

| Symbol | Value | Source |
| --- | --- | --- |
| `G_GAMESTATE` | `0x33dd6b0` | offsets_verified |
| `G_IDLER` | `0x33ddb08` | offsets_verified |
| `G_SESSION` | `0x34ffbe8` | PROVEN_STATIC / post_abi |
| `FN_CMD_QUEUE_POST` | `0x22c41e0` | PROVEN_STATIC |
| `CSession_SERVER` | `+0x40` | post_abi |
| `CDummyServer_PENDING` | `+0x58` | post_abi |
| `CSession_STAGE_ARRAY` | `+0x48` | post_abi |
| `CSession_STAGE_COUNT` | `+0x54` | post_abi |
| `CSession_DRAIN_COUNTER` | `+0x60` | post_abi |
| `CSession_EXEC_COUNTER` | `+0x6c8` | post_abi |
| Dummy recreate path | `0x22d8ad0` | sticky StartGame RO |

UI datetime: GS `+0x484` hours → Y-M-D H (minute N/A).

---

## 2. Land command catalogs (factory_idx + IsValid / Execute)

### MOVE / STRATEGIC / CANCEL / SUPPORT_ATTACK (`cmd_layout`)

| Cmd | VT | type_id | factory_idx | factory | IsValid | Execute |
| --- | --- | --- | --- | --- | --- | --- |
| `CMoveCommand` | `0x2A2C790` | `0x28A2` | **1402** | `0x13FB000` | `0x14002F0` | `0x13FC990` |
| `CStrategicRedeploymentCommand` | `0x2A2D818` | `0x35B9` | **4753** | `0x13FB580` | `0x1402260` | `0x13FC990` |
| `CCancelMovementCommand` | `0x2A2C9B8` | `0x28AF` | **1415** | `0x13FACE0` | `0x13FED40` | `0x13FBBD0` |
| `CSupportAttackCommand` | `0x2A2CB28` | `0x314C` | **3620** (`0xE24`) | `0x13FB5E0` | `0x1402270` | `0x13FDD00` |

Action embeds:
- MOVE → `CUnitMoveAction` VT `0x2A1F648` @ cmd`+0x28` (unit_handle, province/path arrays, clear/safe/avoid, move_priority, sticky).
- STRATEGIC → `CUnitStrategicMoveAction` VT `0x2A1F7E8` @ cmd`+0x28` (army_handle@+16, province@+24, clear@+28, move_priority@+32).

### ORDERS Assign / Unassign / Execute (`cmd_layout.ORDERS`)

| Cmd | VT | type_id | factory_idx | IsValid | Execute |
| --- | --- | --- | --- | --- | --- |
| `COrderAssignCommand` | `0x2A84498` | `0x303E` | **3350** | `0x18DE900` | `0x18D41B0` |
| `COrderUnassignCommand` | `0x2A84550` | `0x304D` | **3365** | `0x18E01D0` | `0x18DB050` |
| `COrderExecuteCommand` | `0x2A85468` | `0x3040` | **3352** | `0x18DEF40` | `0x18D6430` |
| `COrderNewFallbackCommand` | `0x2A84C80` | `0x33D7` | **4271** | `0x18DF4B0` | `0x18D8FC0` |
| `COrderDeleteCommand` | `0x2A843E0` | `0x303F` | **3351** | `0x18DEEE0` | `0x18D5FE0` |

Instance maps (RO): Instance`+0x70` ordered u32 provinces; `+0x88` `CPdxArray<CProvince*>`; `+0xe0` u32 stream; `+0x100` packed twin / soft VT `0x2794550`. NF VT `0x2A84C80` / RF `0x2A84D38`. Units `CPdxArray@+0x28` size@`+0x34` stride8 `{type,index}`; Execute oi@`+0x30`.

Factory table live MATCH: ORDERS 26/26 (2fg); STRATEGIC idx 4753 (2fd/2fe); MOVE/CANCEL filled (2fe).

---

## 3. Captured layouts (MATCH — still no Post)

| Capture | Result | Notes |
| --- | --- | --- |
| StrategicRedeploy leaf | **2fa capture + 2fb layout MATCH** | size `0x50`; recipe design in `reports/phase2fb_ring_embed_recipe.json` — **NOT executed** |
| MOVE offline skeleton (catalog) | **2gj SKELETON_PASS** + factory 1402 MATCH | No live CMove hex → not bit_identical (vs Strategic 2fd) |
| CancelMovement | Live midflight adjacent | ≠ ordinary CMove |
| Assign / Unassign / OG / Instance | Catalog + maps proven | Live pending+heap plan leaves repeatedly empty (2gc–2gh) |
| NewFallback / RF | VT known; midflight leaves empty | NF/RF midflight still empty |

---

## 4. HARD_DENY / still STUBBED

| Item | State |
| --- | --- |
| `allow_post` / `CLAUSEWITZ_ALLOW_POST` | **HARD_DENY** (config hard-returns False) |
| `command_queue` tool-gate | **CLOSED_NOT_OPENED** |
| Ordinary `CMoveCommand` leaf (+ action embed) | **STUBBED** — never caught midflight; **2gj** offline skeleton + factory_idx **1402** live MATCH (no bit_identical without hex) |
| Ring embed / Dummy recreate on Move|Strategic sample | **STUBBED** in-process; recipe **v2 DESIGN** (2gk) + offline bit_identical (2fd) + StartGame sticky RT (2bq) — **NOT executed** |
| 2fb recipe live execute | **FORBIDDEN** |
| SAFE_POST / Post inject / helper patch | **FORBIDDEN** |
| Self-MOVE / NF midflight / CMove leaf | **STUBBED** |
| Live Assign/Unassign on pending+heap (plan leaves) | War-day + heap empty through denser hours (2gh RO ceiling) |
| Capstone / 121 / confidence re-scan | **CLOSED — do not re-churn** |
| NEVER_POST (speed/HourlyTick/Ping/Pause Inc/Dec) | Never Post these |

---

## 5. Human-gated next criteria (still CLOSED)

Agents must **not** set env, open tool-gate, Post, inject, or ask user to right-click.

```
[ ] A  Ordinary CMove (+ CUnitMoveAction embed) live midflight capture JSON
      — OR equivalent Dummy recreate proof on Strategic sample without live Post abuse
[ ] B  Ring-embed recreate proof on that captured buffer (no corruption)
[ ] C  Conscious human sets CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] D  Dedicated slice opens tool-gate with NEVER_POST filters
[ ] E  One land MOVE|Strategic Post at 1x; verify exec/seq + army path; pause; unset env
```

Until A–B green and human does C: **gate stays CLOSED**.

What does **not** unlock Post: Capstone/121 re-churn; HourlyTick sightings alone; empty war-day pending/heap; docs that “just once” Post.

---

## 6. RO ceiling (2gh) + next cheapest NON-Post

ITA war-day pending+heap plan leaves empty (hours denser 18→25; Assign/Unassign/Exec heap=0). Catalog + layouts are the ceiling for pure RO without human gameplay midflight.

**Next shortest NON-Post:** keep gate CLOSED; optional pause-and-UI-plan observe for counts only; retry GitHub push when reachable. Still **NO ALLOW_POST**.


## 7. Live RO snapshot (2gi optional B, ≤15s)

| Field | Value |
| --- | --- |
| pid | 30352 |
| hours | 40 → 41 |
| UI | 1936-01-02 16:00 → 1936-01-02 17:00 |
| pending / stage | 0 / 0 |
| drain / exec | 35113 / 13535 |
| scenario | ITA@1x current process (no relaunch; RO snapshot only) |
| captured_at | 2026-10-31 15:13 Asia/Shanghai |

No Post. Speed policy pause/1x only. Report: `reports/phase2gi_land_post_readiness.json`.

---

*Phase 2gi · catalog-only · 2026-10-31 15:11 Asia/Shanghai*
