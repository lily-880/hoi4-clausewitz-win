# Safe gated Post-enable checklist (CLOSED)

**Status: CLOSED — do not enable Post / tool-gate / ALLOW_POST.**  
Phase **2en** documentation only. Haiti Path C land readiness.

Catalog consolidate: `docs/LAND_POST_READINESS.md` (Phase 2gi + **§6f agent card** 2hc/2hd).

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
| 2 recreate/ring embed | Move or equivalent | Offline Strategic **bit_identical PASS (2fd)**; recipe **v2 DESIGN (2gk)** + StartGame sticky RT (2bq) — **execution STUBBED** |
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

1. In-process Dummy ring_embed push on Strategic sample — STUBBED (offline PASS 2fd; design v2 2gk)  
2. Human `CLAUSEWITZ_ALLOW_POST=1` — HARD_DENY  
3. Tool-gate dedicated open — CLOSED  
4. NEVER invent writes / helper patches / recipe execution from agents  

Docs: `docs/PHASE2FC_STRATEGIC_ISVALID_SAFE.md`, `reports/phase2fc_strategic_isvalid_path.json`, `reports/phase2fb_ring_embed_recipe.json`, `reports/phase2gk_ring_embed_recipe_v2.json`.

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
| Ordinary CMove live sample | STUBBED midflight; offline skeleton + factory **1402 MATCH (2gj)** | 2gj |

### Exact next **human-gated** step (NOT agent-auto)

```
[ ] Human reviews SAFE + 2fd offline PASS
[ ] Human sets CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] Dedicated slice opens tool-gate with NEVER_POST filters
[ ] ONE Strategic (preferred) or Move Post at 1x; verify; pause; unset env
```

Until then: **agents must not Post, inject, patch helpers, or execute 2fb/2gk recipe.**

Catalog: `STRATEGIC.factory_idx` corrected 4505→**4753**; MOVE/CANCEL factory_idx filled.

*Phase 2fe — documentation + catalog only. Gate stays CLOSED.*

---

## Agent card pointer — LAND_POST §6f (2hc/2hd)

**Canonical card:** `docs/LAND_POST_READINESS.md` §6f (Phase 2hc).  
**Gate:** CLOSED. `allow_post` False. No recipe execute. Never 5x. Do not ask user to right-click.

### Can feed today (RO IDs)

| ID | Signal |
| --- | --- |
| `LOCATE` / `PATH200` / `INST7088` | CArmy locate · `+0x200` candidates · Instance`+0x70`/`+0x88` |
| `OG50MI` | OG`+0x50` ≡ CArmy`+0xB8` (MI VT `0x29d6fb8`) walkback |
| `ASSIGN51` | Assign units type=51 → CArmy (oi often 0) |
| `FACTORY` / `FN_VT` | factory_idx MATCH + live VT`+0x48`/`+0x50` FN MATCH (2ha/2hb) |
| `CLOCK` | hours/UI/pending/stage/drain/exec |

### HARD_DENY (do not invent)

| ID | Gate |
| --- | --- |
| `MIDFLIGHT` / `NAMED_DEST` | HONEST_EMPTY — stop non-interactive midflight re-poll |
| `ASSIGN_OI` | QUIET until plan-dense oi≠0 |
| `RING` embed STUBBED; `RING_LAYOUT` RO HIT 2hf; `POST`/`SPEED5X` HARD_DENY/NEVER |

### Human-gated (unchanged — still CLOSED)

```
[ ] A  CMove midflight hex OR Strategic-only + human SAFE Post for ring_embed
[ ] B  Ring-embed recreate proof
[ ] C  Human CLAUSEWITZ_ALLOW_POST=1 for ONE experiment
[ ] D  Tool-gate + NEVER_POST
[ ] E  ONE land Post @1x; verify; pause; unset
```

Docs: `docs/PHASE2HC_AGENT_READINESS_CONSOLIDATE.md`, `docs/PHASE2HD_SAFEPOST_6F_POINTERS.md`.

---

## Phase 2gj … 2iv — checklist polish (CLOSED)

**Gate remains CLOSED. allow_post False. tool-gate CLOSED. Recipes NOT executed.**

Catalog consolidate pointer: `docs/LAND_POST_READINESS.md` (Phase 2gi + deltas below).

| Phase | Delta | State |
| --- | --- | --- |
| 2gj | MOVE offline `0x88` skeleton; factory_idx **1402** live MATCH; ≤45s CMove observe | **HONEST_EMPTY** midflight; skeleton **PASS** (no bit_identical) |
| 2gk | ring_embed recipe **v2** DESIGN; StartGame sticky ↔ Strategic offline concordance; live ring VT MATCH | Steps 1–4 proof-tagged; step 5 ring push **STUBBED** |
| 2gl | This checklist + LAND_POST polish with 2gj/2gk deltas | **Docs only** |
| 2gm | Perception: `CArmy+0x200` multi-prov hit (2) after tag-FP filter; Instance+0x70/+0x88 8/14 | **HIT** (not demangled movement_dest; Post still CLOSED) |
| 2gn | `+0x200` ↔ Instance`+0x70`/`+0x88` cross (3×57) | **NO_OVERLAP** (extends 2fy; Post still CLOSED) |
| 2go | Named `movement_dest` PE + soft/scalar hunt | **HONEST_EMPTY** (strict 0; Post still CLOSED) |
| 2gp | Assign ≤90s + OG+0x50↔CArmy+0xB8 MI | **HIT** membership proxy (Post still CLOSED) |
| 2gq | Assign oi≠0 confirm ≤90s; B catalog polish | **QUIET** on A; walkback 294/294 (Post still CLOSED) |
| 2gr | denser Assign oi≠0 (clock nudge + heap edge); B catalog polish | **QUIET** on A; walkback 375/375 (Post still CLOSED) |
| 2gs | perception §6b + readiness catalog; ≤60s path snapshot | **DOCS/RO polish** (Post still CLOSED) |
| 2gt | ≤90s non-interactive midflight RO + §6c agent summary | **MIDFLIGHT_HONEST_EMPTY** (Post still CLOSED) |
| 2gu | §6d agent feed ceiling (can-feed / HARD_DENY); catalog-only | **AGENT_FEED_CEILING_CATALOG_POLISH** (Post still CLOSED) |
| 2gv | ≤90s non-interactive midflight RO reaffirm | **MIDFLIGHT_HONEST_EMPTY** (Post still CLOSED) |
| 2gw | §6e agent checklist + ≤60s path/walkback; no midflight re-poll | **AGENT_CHECKLIST_CATALOG_POLISH** (Post still CLOSED) |
| 2gx | ≤30s Assign oi≠0 edge + factory1402/execlist corner | **ASSIGN_QUIET_FACTORY1402_MATCH** (Post still CLOSED) |
| 2gy | SA3620/Cancel1415 factory MATCH + OG50 walkback | **SA_CANCEL_FACTORY_MATCH_OG50_WALKBACK** (Post still CLOSED) |
| 2gz | Assign3350/Unassign3365/Execute3352 factory MATCH | **ASSIGN_UNASSIGN_EXECUTE_FACTORY_MATCH** (Post still CLOSED) |
| 2ha | Assign/Unassign/Execute VT FN + OG50 polish | **ASSIGN_FN_MATCH_OG50_WALKBACK** (Post still CLOSED) |
| 2hb | MOVE/SA/Cancel/Strategic VT FN polish | **MOVE_FAMILY_FN_FACTORY_MATCH** (Post still CLOSED) |
| 2hc | §6f ONE agent readiness (2ha+2hb FN/factory + OG50 + HARD_DENY) | **AGENT_READINESS_ONE_SUMMARY** (Post still CLOSED) |
| 2hd | SAFE_POST §6f agent-card pointer + PHASE2HC expand | **SAFEPOST_6F_POINTERS_POLISH** (Post still CLOSED) |
| 2he | Full land factory MATCH + Dummy execlist/ring corner | **FACTORY_EXECLIST_RING_CORNER** (Post still CLOSED) |
| 2hf | ring@+0xa0 INLINE layout polish (2he ptr misread corrected) | **RING_INLINE_LAYOUT_POLISH** (Post still CLOSED) |
| 2hg | CLOCK reload≠wrap + ring seq delta vs 2hf | **CLOCK_RELOAD_RING_SEQ_POLISH** (Post still CLOSED) |
| 2hh | Post-reload ≤45s PATH200+OG50 perception | **POST_RELOAD_PERCEPTION_HIT** (Post still CLOSED) |
| 2hi | PATH200 denser one-shot nonempty/multi sample | **PATH200_DENSE_MULTI_HIT** (Post still CLOSED) |
| 2hj | PATH200 multi-army matrix (empty+nonempty+multi) | **PATH200_MULTI_ARMY_MATRIX_HIT** (Post still CLOSED) |
| 2hk | OG50 walkback polish + 2hj PATH200 matrix fold | **OG50_MEMBERSHIP_POLISH_HIT** (Post still CLOSED) |
| 2hl | OG50NAME demangle attempt (MI VT RTTI + PE needles) | **OG50NAME_CLASS_HIT_LIVE_MISS** (Post still CLOSED) |
| 2hm | OG+0x50↔path-army reverse membership (1042/1048) | **OG50_REVERSE_EMPTY_COHORT_ONLY** (Post still CLOSED) |
| 2hn | OG+0x50 × PATH200@+0x60 ITA crosstab | **OG50_PATH_CROSSTAB_ALL_OUT** (Post still CLOSED) |
| 2ho | OG+0x50 widen oi1..511 ITA + tag hist | **OG50_WIDE_ITA_HIT_HI** (Post still CLOSED) |
| 2hp | oi=481 OG50×Inst70/88×PATH200 cross | **OG481_MEMBERS_PATH_ONLY** (Post still CLOSED) |
| 2hq | PATH200 denser focus {3816,3938,915} + Instant VT dump | **PATH200_FOCUS_PROV_HIT** (Post still CLOSED) |
| 2hr | INST_VT false-gate fix + oi=481 Instant×PATH | **INST_VT_GATE_CORRECT_CROSS_HIT** (Post still CLOSED) |
| 2hs | Instant+0x88 CP_VT fix + oi=481 × PATH/70 | **ARR88_CP_VT_CORRECT_HIT** (Post still CLOSED) |
| 2ht | multi-oi Instant+0x70 × ITA PATH200 | **MULTI_OI_INST70_PATH_HIT** (Post still CLOSED) |
| 2hu | PATH×OG+0x50×Inst70 triangle | **PATH_OG50_INST70_TRIANGLE_HIT** (Post still CLOSED) |
| 2hv | OG481 member rollup + cover_only reverse | **OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT** (Post still CLOSED) |
| 2hw | path∉Inst70 covering-oi + cover_only reverse widen | **PATH_OUTLIER_COVER_WIDEN_HIT** (Post still CLOSED) |
| 2hx | hi-band OG962/976 dig Inst70+OG50+PATH | **HIBAND_OG962_976_DIG_HIT** (Post still CLOSED) |
| 2hy | PATH200 denser @2hx focus {1176,3938,3816,915} × hiband OG50 | **PATH200_HXFOCUS_DENSE_HIT** (Post still CLOSED) |
| 2hz | non-hiband 2hy path armies → OG+0x50 reverse oi1..1200 | **NONHIBAND_PATH_OG50_REVERSE_HIT** (Post still CLOSED) |
| 2ia | mid-band OG575 dig Inst70+OG50+PATH (2hz 2640 home) | **MIDBAND_OG575_DIG_HIT** (Post still CLOSED) |
| 2ib | PATH200 denser all-nonempty → OG50 reverse | **PATH200_ALL_REVERSE_HIT** (Post still CLOSED) |
| 2ic | PATH200 ∩ OG481 Inst70 triangle denser | **PATH_OG481_INST70_TRIANGLE_HIT** (Post still CLOSED) |
| 2id | OG481 Instant+0x88 CP_VT × denser PATH × Inst70 | **ARR88_PATH_DENSE_HIT** (Post still CLOSED) |
| 2ie | OG575 PATH-only shell denser × 481 Inst70 | **OG575_PATH_SHELL_DENSE_HIT** (Post still CLOSED) |
| 2if | post-reload PATH200 denser → OG50 reverse | **PATH200_RELOAD_REVERSE_HIT** (Post still CLOSED) |
| 2ig | post-reload OG481 Instant+0x88 × PATH denser | **ARR88_RELOAD_PATH_HIT** (Post still CLOSED) |
| 2ih | post-reload known-OG PATH shells denser | **KNOWN_OG_PATH_SHELLS_HIT** (Post still CLOSED) |
| 2ii | shell-member PATH × 481 Inst70/ARR88 drift | **SHELL_PATH_INST_DRIFT_HIT** (Post still CLOSED) |
| 2ij | CONTINUOUS PATH200 denser → OG50 reverse | **PATH200_CONT_REVERSE_HIT** (Post still CLOSED) |
| 2ik | CONTINUOUS OG481 Instant+0x88 × PATH denser | **ARR88_CONT_PATH_PARTIAL** (Post still CLOSED) |
| 2il | CONTINUOUS PATH200 multi denser → OG50+481 hub | **PATH200_MULTI_DENSE_HIT** (Post still CLOSED) |
| 2im | CONTINUOUS PATH200 focus (4527, 256) denser → OG50+481 hub | **PATH200_FOCUS4527_DENSE_HIT** (Post still CLOSED) |
| 2in | CONTINUOUS PATH200 focus 6867+2im-multi denser → OG50+481 hub | **PATH200_FOCUS6867_DENSE_HIT** (Post still CLOSED) |
| 2io | CONTINUOUS PATH200×live-Inst70-tri denser → OG50+481 hub | **PATH200_INST70_TRI_DENSE_HIT** (Post still CLOSED) |
| 2ip | CONTINUOUS PATH200 path-only-outside-Inst70 → OG50+481 hub | **PATH200_PATHONLY_OUTSIDE70_HIT** (Post still CLOSED) |
| 2iq | CONTINUOUS PATH200 mixed-Inst70+outside-companion → OG50+481 hub | **PATH200_MIXED70_COMPANION_HIT** (Post still CLOSED) |
| 2ir | CONTINUOUS PATH200 dense-mixed+hiband-pathonly → OG50+481 hub | **PATH200_DENSE_MIXED_PATHONLY_HIT** (Post still CLOSED) |
| 2is | CONTINUOUS PATH200 focus1053+1869-reintersect → OG50+481 hub | **PATH200_FOCUS1053_1869_HIT** (Post still CLOSED) |
| 2it | CONTINUOUS PATH200 arr88xpath-9840class → OG50+481 hub | **PATH200_ARR88_9840_HIT** (Post still CLOSED) |
| 2iu | CONTINUOUS PATH200 focus740-og50-refresh → OG50+481 hub | **PATH200_FOCUS740_OG50_HIT** (Post still CLOSED) |
| 2iv | 2iu focus-740 cohort rehome after oi recycle | **COHORT_REHOME_HIT** (Post still CLOSED) |
| 2iv-relaunch | fresh ITA PATH200 path_only oi=70/57 | **PATH200_RELAUNCH_PATH_ONLY_HIT** (Post still CLOSED) |
| 2iw-NONPOST | denser PATH200 oi=57/70 focus_oi_seed | **PATH200_OI57_70_DENSE_HIT** (Post still CLOSED; Post-2iw script not re-run) |
| 2ix-NONPOST | longer 1x advance; PATH stable-thin / calendar stall | **PATH200_LONGER_STABLE_THIN** (Post still CLOSED) |
- **2iy:** calendar softlock (WS collapse) fixed by relaunch ITA@1x; PATH200 still thin path_only; new OG reverse OIs 45/55; Inst empty; allow_post False; NO Post.
- **2iz:** 1x advance day+12; PATH denser nonempty=3 new_dest 1903 oi=58; multi_n=0; Inst empty; allow_post False; NO Post.
- **2ija:** CONTINUOUS day74; PATH multi_n=2 nonempty=15; new dests/OIs; Inst empty; allow_post False; NO Post.
- **2ijb:** Instant×PATH hunt; multi_n=2; Instant empty after one nudge; PATH≠Inst honesty; allow_post False; NO Post; stop Instant-empty polls.
- **2ijc:** PATH200/OG50 polish NO Instant; multi_n=1; Instant peacetime PARKED; PATH≠Inst; allow_post False; NO Post.
- **2ijd:** PATH200/OG50 denser; multi_n=0; new_ois 495/503; Instant PARKED; allow_post False; NO Post.
- **2ije:** PATH200/OG50 track; multi_n=1 new_dest 832 oi=504; Instant PARKED; PathC ~60% honesty (not 70%); allow_post False; NO Post.
- **2ijf:** PATH200/OG50 denser2; multi_n=1 new_dest 2679 oi=448; Instant PARKED; PathC ~60% honesty (not 70%); allow_post False; NO Post.

### HARD_DENY unchanged

- `allow_post()` hard-returns **False**
- `CLAUSEWITZ_ALLOW_POST` unset / ignored
- No Post inject / helper patch / guess writes / 5x / ask-user right-click
- No Capstone/121/confidence re-churn

### Exact next human-gated (unchanged order)

```
[ ] Midflight CMove hex OR accept Strategic-only path with human SAFE Post for ring_embed
[ ] Human CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] Dedicated tool-gate open + NEVER_POST
[ ] ONE Strategic (preferred) or Move Post at 1x; verify; pause; unset
```

*Phase 2iv — cohort rehome + relaunch PATH200. Gate stays CLOSED. 2026-11-01 Asia/Shanghai*

