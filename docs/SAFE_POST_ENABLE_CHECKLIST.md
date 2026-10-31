# Safe gated Post-enable checklist (CLOSED)

**Status: CLOSED — do not enable Post / tool-gate / ALLOW_POST.**  
Phase **2en** documentation only. Haiti Path C land readiness.

This is the single source of “what is still missing before any Post is allowed.”  
It does **not** open gates. It does **not** authorize writes.

---

## Hard invariants (never violate)

| Rule | State |
| --- | --- |
| `allow_post()` | **hard-returns False** even if env set |
| `CLAUSEWITZ_ALLOW_POST` | **must stay unset / ignored** |
| `command_queue` / tool-gate | **DISABLED** / **CLOSED_NOT_OPENED** |
| Speed | pause or **1x** only — **NEVER 5x** |
| NEVER_POST set | never Post Inc/Dec/SetGameSpeed, HourlyTick, Ping, Pause |
| Guess writes | no `WriteProcessMemory` / Post on unproven layouts |
| Input inject | DX11 ignores SendInput; do not ask user to right-click from agent slices |

Runtime check: `from calling.config import allow_post; assert allow_post() is False`.

---

## Exact proofs still MISSING (block enable)

Ordered shortest-path. All must be green before any gated enable discussion.

### 1. Live midflight `CMoveCommand` (+ `CUnitMoveAction` embed) — **STUBBED**

| Item | Detail |
| --- | --- |
| Why | Without a real buffer we cannot prove province path / unit_handle / move_priority against live memory, nor close sample→recreate |
| Watcher | Armed RO: `scripts/phase2bm_midflight_ready.py` (`--interval 0.02 --burst-on-edge 12`); heartbeat `reports/midflight_watcher_heartbeat.json`; instant dump `reports/midflight_cmove_capture.json` |
| Sightline | **OK** at 1x: `CHourlyTickCommand` seen via stage (Phase 2em) — pipeline works; Move class not yet observed |
| How obtained | Real gameplay land right-click (human); agent must **not** inject / ask in automated slices |
| Done looks like | `caught_army_move=true` + hex dump with action embed fields populated |

### 2. Serialize / recreate round-trip into Dummy ring — **STUBBED** (structural sticky OK)

| Item | Detail |
| --- | --- |
| Why | Hand-built or captured Move must survive Dummy recreate (`0x22d8ad0` path) into ring without corruption |
| Have | Sticky StartGame structural serdes/factory RO (2bq/2br) |
| Need | Same proof on **Move** (or Strategic) using captured buffer — needs (1) |

### 3. Explicit `CLAUSEWITZ_ALLOW_POST=1` — **hard-deny until human**

| Item | Detail |
| --- | --- |
| Why | Policy + `allow_post()` hard-deny; never auto-enable in per-tick loops |
| Need | Conscious human env set **after** (1)+(2); tooling still must refuse NEVER_POST set |

### 4. Tool-gate open predicates — **CLOSED_NOT_OPENED**

| Item | Detail |
| --- | --- |
| Why | `command_queue_tool_gate` stays DISABLED until (1)–(3) and a written enable review |
| Need | Explicit gate flip in a dedicated slice — **not this doc** |

---

## Already DONE (do not re-churn)

| Piece | Status |
| --- | --- |
| LAND Execute catalog 121/121 | CLOSED |
| Post-path confidence 1.0 | CLOSED |
| Post ABI / cmd_layout RO | CLOSED (2bc/2bm) |
| Order Execute layouts / factories | CLOSED (2ar/2bm/2bn) |
| Army handle / province wiring | CLOSED (2as/2bn/2bo) |
| Drain/execute edges / Dummy ring structure | CLOSED (2bn/2br) |
| NEVER_POST speed/HourlyTick inventory | CLOSED (2bo) |
| GS UI datetime Y-M-D H via `+0x484` hours | CLOSED (2el); minute N/A |
| Midflight watcher edge-burst + HourlyTick sightline | CLOSED (2em) |
| Non-Post MOVE issue path | **NONE** (2ek audit) |

---

## What does **not** count as enable progress

- Capstone / 121 / confidence re-scans
- HourlyTick sightings alone (sightline only)
- `movement_dest` under `-noai` while empty
- DX11 / console / Space “move” attempts
- Docs that open the gate, set env, or Post “just once”

---

## Enable sequence (future; still CLOSED now)

```
[ ] 1 midflight CMove (+ action embed) capture JSON
[ ] 2 recreate/ring embed proof on that sample (or equivalent Move build)
[ ] 3 human sets CLAUSEWITZ_ALLOW_POST=1 for a single controlled experiment
[ ] 4 dedicated slice opens tool-gate with NEVER_POST filters enforced
[ ] 5 one land MOVE Post at 1x; verify exec/seq + army path; pause; unset env
```

Until every box is checked, **Post remains disabled.**

---

## Related paths

- Recipe: `docs/MIDFLIGHT_CMOVE_CAPTURE.md`
- Machine checklist JSON: `research/safe_enable_checklist.json` (`enable_when`, `blocks_enabling_post`)
- Issue-path audit: `reports/phase2ek_issue_path_audit.json`
- Watcher sightline: `reports/midflight_watcher_sightline.json`

*Phase 2en — documentation only. Gate stays CLOSED.*

---

## Phase 2fc — Strategic alternate path (CHECKLIST ONLY)

**Gate remains CLOSED. allow_post stays False. Do not execute ring_embed.**

### Progress vs original enable sequence

| Step | Original | 2fc state |
| --- | --- | --- |
| 1 midflight leaf | CMove (+ embed) | **Strategic leaf CAPTURED (2fa)** + layout MATCH (2fb); ordinary CMove still STUBBED |
| 2 recreate/ring embed | Move or equivalent | **DESIGN drafted (2fb recipe)** — execution STUBBED; needs Dummy recreate proof |
| 3 human ALLOW_POST env | required | **HARD_DENY** — unset / ignored |
| 4 tool-gate | CLOSED | **CLOSED_NOT_OPENED** |
| 5 one land Post | forbidden | **FORBIDDEN** |

### Strategic IsValid path (observation)

- Wrap: `0x22d8ea0`
- Cmd IsValid: `0x1402260` (type_id `0x35b9`)
- Action IsValid: `0x12c2c20` (embed type_id `0x364a`)
- Shared execute thunk w/ MOVE: `0x13fc990` → action.execute `0x12c3190`
- Catalog IsValid callees: `0x57f7b0, 0x1e1510, 0x2607890` (strategic-only `0x57f7b0)`

### Still blocking any Post (Strategic path)

1. Dummy ring recreate proof on Strategic sample — STUBBED  
2. Human `CLAUSEWITZ_ALLOW_POST=1` — HARD_DENY  
3. Tool-gate dedicated open — CLOSED  
4. NEVER invent writes / helper patches / recipe execution from agents  

Docs: `docs/PHASE2FC_STRATEGIC_ISVALID_SAFE.md`, `reports/phase2fc_strategic_isvalid_path.json`, `reports/phase2fb_ring_embed_recipe.json`.

*Phase 2fc — documentation only. Gate stays CLOSED.*

---

## Phase 2fd — Strategic offline recreate RO

**Gate remains CLOSED. allow_post False. 2fb recipe NOT executed.**

| proof | state |
| --- | --- |
| Offline Strategic 0x50 bit-identical rebuild | **PASS** |
| Live factory idx=4753 → `0x13fb580` | **MATCH** |
| recreate `0x22d8ad0` readable | **OK** |
| gettypeid / action ser tokens | **OK** |
| In-process ring embed push | **STUBBED** (needs Post) |

Docs: `docs/PHASE2FD_STRATEGIC_RING_RECREATE_RO.md`.

*Phase 2fd — RO only. Gate stays CLOSED.*

---

## Phase 2fe — RO ceiling (Post-gated remainder)

**Gate remains CLOSED. allow_post False. tool-gate CLOSED. 2fb recipe NOT executed.**

### Strategic alternate path (RO complete ceiling)

| proof | state | phase |
| --- | --- | --- |
| Live Strategic leaf + embed | DONE | 2fa |
| Layout decode MATCH | DONE | 2fb |
| IsValid path documented | DONE | 2fc |
| Offline 0x50 bit-identical rebuild | **PASS** | 2fd |
| Live factory idx→slot MATCH | **PASS** (idx **4753**) | 2fd/2fe |
| In-process ring embed / Post | **STUBBED — needs Post** | — |
| Ordinary CMove live sample | STUBBED (catalog complete) | 2fe note |

### Exact next **human-gated** step (NOT agent-auto)

```
[ ] Human reviews SAFE + 2fd offline PASS
[ ] Human sets CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] Dedicated slice opens tool-gate with NEVER_POST filters
[ ] ONE Strategic (preferred) or Move Post at 1x; verify; pause; unset env
```

Until then: **agents must not Post, inject, patch helpers, or execute 2fb recipe.**

Catalog: `STRATEGIC.factory_idx` corrected 4505→**4753**; MOVE/CANCEL factory_idx filled.

*Phase 2fe — documentation + catalog only. Gate stays CLOSED.*
