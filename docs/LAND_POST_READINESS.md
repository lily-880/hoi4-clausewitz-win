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
| StrategicRedeploy leaf | **2fa capture + 2fb layout MATCH** | size `0x50`; recipes `phase2fb_ring_embed_recipe.json` + **`phase2gk_ring_embed_recipe_v2.json`** — **NOT executed** |
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
| 2fb/2gk recipe live execute | **FORBIDDEN** |
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

## 6. RO ceiling + next cheapest NON-Post

ITA war-day pending+heap plan leaves empty (2gc–2gh). CMove ≤45s observe empty (2gj). Dummy ring pending/execlist empty (2gk). Catalog + offline layouts are the Post-side ceiling without human midflight or SAFE Post.

**2gm/2gn perception:** `CArmy+0x200` multi-province hits (tag-FP filtered). **2gn cross:** `+0x200` ⊀ Instance`+0x70`/`+0x88` (3 multi × 57 shaped OIs, overlap=0) — extends 2fy no-overlap. Named `movement_dest` **NOT_DEMANGLED**; army↔OI membership field **STUBBED**.

**Next shortest NON-Post:** optional Assign-stage membership sight or named movement_dest hunt; else human midflight CMove hex / SAFE Post for ring_embed; retry GitHub push when reachable. Still **NO ALLOW_POST**.


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


## 8. Phase deltas 2gj / 2gk (catalog — still CLOSED)

| Phase | Result | What changed | Still blocked |
| --- | --- | --- | --- |
| **2gj** | `MOVE_OFFLINE_SKELETON_PASS_FACTORY1402_MATCH_OBSERVE_EMPTY` | CMove `0x88` offline skeleton; shared header w/ Strategic/Cancel; live factory_idx **1402** → `0x13FB000` **MATCH**; ≤45s CMove observe **HONEST_EMPTY** | No live CMove hex → not bit_identical; province_arr/path_arr need game allocs |
| **2gk** | `STRATEGIC_RING_EMBED_DESIGN_V2_STARTGAME_CONCORDANCE` | Recipe **v2** DESIGN: steps 1–4 proof-tagged (2fd/2bq/2gj); step 5 ring push **STUBBED**; StartGame sticky = best live recreate sightline; Strategic = best offline rebuild | In-process ring_embed needs Post/sink |
| **2gm** | `CARMY_PATH_INSTANCE_RO_PLUS200_MULTI_HIT` | Perception: `CArmy+0x200` multi (2) after tag-FP filter; Instance+0x70/+0x88 hit 8/14; +0xe0/+0x100 empty; named movement_dest NOT_DEMANGLED | No demangled movement_dest; Post/ring still HARD_DENY |
| **2gn** | `CROSS_200_VS_70_NO_OVERLAP` | CArmy+0x200 ↔ Instance+0x70/+0x88: 3 multi × 57 shaped, **overlap=0**; membership handle scans empty; oi_u32 noise untrusted | +0x200 ≠ order path; Post/ring HARD_DENY |

Docs: `docs/PHASE2GJ_MOVE_OFFLINE_LAYOUT.md`, `docs/PHASE2GK_STRATEGIC_RING_EMBED_DESIGN.md`.  
Recipes: `reports/phase2fb_ring_embed_recipe.json`, `reports/phase2gk_ring_embed_recipe_v2.json` — **DESIGN ONLY, never execute from agent slices.**

HARD_DENY unchanged: `allow_post` False · tool-gate CLOSED · no Post inject · no ask-user right-click · never 5x.


*Phase 2gn · +0x200↔+0x70 cross NO_OVERLAP · 2026-10-31 Asia/Shanghai*
