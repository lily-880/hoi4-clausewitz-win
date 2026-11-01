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

Factory table live MATCH: ORDERS 26/26 (2fg); STRATEGIC idx 4753 (2fd/2fe); MOVE/CANCEL filled (2fe). **2ha/2hb live VT+0x48/0x50 FN MATCH** for Assign/Unassign/Execute + MOVE/SA/Cancel/Strategic; factory 3350/3365/3352 + 1402/3620/1415/4753 reaffirm (2gz–2hb).

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

**2gm–2gs perception (see §6b):** `CArmy+0x200` multi (tag-FP) ⊀ Instance`+0x70`; named dest empty; **OG+0x50 ≡ CArmy+0xB8** walkback live; Assign type=51 resolve proven; Assign oi≠0 **quiet** through dense 2gr.

**Next shortest NON-Post:** Human G4 CLAUSEWITZ_ALLOW_POST=1 (executor cannot flip) → G5 → G2 live/G6; agent card folded 2ijl. Still **NO ALLOW_POST**. (2iv `COHORT_REHOME_HIT`); retry GitHub push when reachable. Still **NO ALLOW_POST**.



## 6b. Perception map (2gm–2gs consolidate — RO only)

| Layer | Proven | Semantics / ceiling |
| --- | --- | --- |
| `CArmy+0x200` | 2gm multi after tag-FP; 2gn **NO_OVERLAP** vs Instance`+0x70`/`+0x88` | Multi-prov **candidate** only — **not** demangled `movement_dest`; **not** order path |
| Instance`+0x70` / `+0x88` | ordered u32 provinces / `CProvince*` hub (2gm seed) | Order/front path — **≠** army midflight dest |
| **OG+0x50 ≡ CArmy+0xB8** | MI VT `0x29d6fb8`; walkback **376/376** (2gs live; was 375 @2gr) | Membership **proxy** — demangled +0x50 name **STUBBED** |
| Assign units type=`51` | 2gp: ix 410/445 → ITA CArmy tag=15; oi@`+0x48` | oi=0 unset; **oi≠0 units↔OI** quiet through 2gq/2gr dense |
| Named `movement_dest` | 2go PE **HONEST_EMPTY** | Do not invent |

**2gs live path snapshot (≤60s @1x):** carmy_rows=8 nonempty=6 multi=3 ticks=1 hours=227 UI=1936-01-10 11:00 allow_post=False.


## 6c. Agent-facing perception summary (2gt)

**What land agent can read RO today (no Post):**
- CArmy locate via handle type=51 + country_tag
- CArmy+0x200 multi-prov path *candidates* (tag-FP filtered; not demangled dest)
- Instance+0x70/+0x88 order/front province maps (≠ midflight dest)
- OG+0x50 ≡ CArmy+0xB8 membership proxy (VT 0x29d6fb8)
- Assign units type=51 → CArmy resolve (when Assign sighted; oi often 0)
- Live hours/UI date, pending/stage/drain/exec counters (RO)

**What is still blocked / honest-empty:**
- Ordinary CMove midflight hex (bit_identical rebuild) — still empty without human/AI leave
- Named movement_dest demangle
- Assign units↔OI when order_index≠0 (quiet through 2gq/2gr/2gt)
- ring_embed / Dummy recreate in-process (needs SAFE Post)
- Any Post / tool-gate / recipe execute

**2gt midflight sample:** result=`MIDFLIGHT_HONEST_EMPTY` · move_hex=0 · cancel_hex=0 · assign_oi≠0=0 · live hours=246 UI=1936-01-11 06:00 · allow_post=False.
**2gv midflight sample:** result=`MIDFLIGHT_HONEST_EMPTY` · move_hex=0 · cancel_hex=0 · assign_oi≠0=0 · live hours=276 UI=1936-01-12 12:00 · allow_post=False.

## 6d. Agent feed ceiling — can feed today / HARD_DENY (2gu)

Catalog consolidate of §6b perception + §6c midflight empty + 2gp–2gr Assign/OG50.
**No Post. No recipe execute. allow_post False.**

### Can feed land agent today (RO)

| Signal | How | Status |
| --- | --- | --- |
| CArmy locate | handle type=51 + country_tag | HIT (2gp) |
| CArmy+0x200 multi-prov candidates | tag-FP; not demangled dest | LIVE nonempty/multi (2gs) |
| Instance+0x70/+0x88 order/front | ≠ midflight; ⊀ +0x200 | HIT (2gm/2gn) |
| OG+0x50 ≡ CArmy+0xB8 membership | MI VT `0x29d6fb8` | walkback live (2gs) |
| Assign units type=51 → CArmy | oi@`+0x48` often 0 | HIT when sighted (2gp) |
| Live clock/counters | hours/UI/pending/stage/drain/exec | HIT |

### HARD_DENY / honest-empty (do not invent)

| Signal | Status |
| --- | --- |
| CMove/SA/Cancel midflight hex | HONEST_EMPTY (2gt ≤90s non-interactive) |
| Named `movement_dest` | HONEST_EMPTY (2go) |
| Assign oi≠0 units↔OI | QUIET (2gq/2gr/2gt) |
| ring_embed / Dummy recreate | STUBBED — needs SAFE Post |
| Post / tool-gate / 2fb\|2gk execute | HARD_DENY |
| Demangled OG+0x50 name | STUBBED |

**2gu live:** pid=30352 · hours=257 · UI=1936-01-11 17:00 · allow_post=False.
**Ceiling:** non-interactive RO cannot raise midflight/oi≠0 further without human midflight or SAFE Post.

## 6e. Agent checklist — use RO today / do not invent (2gw)

Folds §6b perception + §6c/2gv midflight empty + §6d feed ceiling + 2gp–2gr Assign/OG50.
**Catalog + brief ≤60s path/walkback only. No midflight leaf hunt. No Post.**

### Use RO today

| ID | Item | Gate |
| --- | --- | --- |
| `LOCATE` | Locate CArmy via handle type=51 + country_tag | HIT 2gp |
| `PATH200` | Read CArmy+0x200 multi-prov candidates (tag-FP; not demangled dest) | LIVE nonempty=4 multi=0 |
| `INST7088` | Read Instance+0x70/+0x88 order/front maps (≠ midflight; ⊀ +0x200) | HIT 2gm/2gn |
| `OG50MI` | Membership via OG+0x50 ≡ CArmy+0xB8 (VT 0x29d6fb8) | walkback 379/379 |
| `ASSIGN51` | Resolve Assign units type=51 → CArmy when sighted (oi often 0) | HIT 2gp |
| `CLOCK` | Read hours/UI/pending/stage/drain/exec | hours=290 UI=1936-01-13 02:00 |

### Do not invent / HARD_DENY

| ID | Item | Gate |
| --- | --- | --- |
| `MIDFLIGHT` | CMove/SA/Cancel midflight hex for bit_identical rebuild | HONEST_EMPTY 2gt+2gv (move=0) |
| `NAMED_DEST` | Named movement_dest demangle | HONEST_EMPTY 2go |
| `ASSIGN_OI` | Assign units↔OI when order_index≠0 | QUIET 2gq/2gr/2gt/2gv (oi≠0=0) |
| `RING` | ring_embed / Dummy recreate in-process | STUBBED — needs SAFE Post |
| `POST` | Any Post / tool-gate / 2fb|2gk recipe execute | HARD_DENY allow_post=False |
| `OG50NAME` | demangled OG`+0x50` / MI field name | OG50NAME_CLASS_HIT_FIELD_STUBBED MI_class=CArmy (2hl; 2hm reverse maps path armies; field STUBBED) |

**2gw live path (≤60s @1x):** carmy=6 nonempty=4 multi=0 ticks=20 · walkback 379/379 · pid=30352 hours=290 UI=1936-01-13 02:00 allow_post=False.
**2gx cheap edge:** result=`ASSIGN_QUIET_FACTORY1402_MATCH` · assign_sight=0 · oi≠0=0 · factory1402_match=True · hours=304 UI=1936-01-13 16:00 · allow_post=False.
**2gy factory+OG50:** result=`SA_CANCEL_FACTORY_MATCH_OG50_WALKBACK` · SA3620=True · Cancel1415=True · MOVE1402=True · Strat4753=True · walkback 380/380 · hours=312 UI=1936-01-14 00:00 · allow_post=False.
**2gz factory Assign/Unassign/Execute:** result=`ASSIGN_UNASSIGN_EXECUTE_FACTORY_MATCH` · Assign3350=True · Unassign3365=True · Execute3352=True · MOVE1402=True · hours=321 UI=1936-01-14 09:00 · allow_post=False.
**2ha FN+OG50:** result=`ASSIGN_FN_MATCH_OG50_WALKBACK` · all_fn=True · all_factory=True · walkback 380/380 · hours=330 UI=1936-01-14 18:00 · allow_post=False.
**2hb move-family FN:** result=`MOVE_FAMILY_FN_FACTORY_MATCH` · all_fn=True · all_factory=True · MOVE1402=True · SA3620=True · Cancel1415=True · Strat4753=True · hours=338 UI=1936-01-15 02:00 · allow_post=False.
**2hc readiness consolidate:** result=`AGENT_READINESS_ONE_SUMMARY` · move_family=True · assign_family=True · walkback 380/380 · hours=347 UI=1936-01-15 11:00 · allow_post=False.
### Instant×PATH peacetime PARK (2ijb/2ijc)
Instant VT false on peacetime path OIs (65/450/448/…). Do not Instant-empty re-poll. Resume Instant×PATH on wartime or human midflight CMove. PATH≠Inst honesty: PATH/OG50 ≠ Instant-validated order. Post CLOSED.


**Midflight ceiling:** 2gt+2gv both `MIDFLIGHT_HONEST_EMPTY` — stop non-interactive midflight re-polls until human leave or plan-dense Assign window.

## 6f. ONE agent-facing readiness summary (2hc)

**Status: CLOSED — allow_post False · tool-gate CLOSED · recipes NOT executed · never 5x.**
Folds §6b–§6e + **2ha** Assign FN/factory + **2hb** MOVE-family FN/factory + OG50 into one land-agent card.


### 2ijh agent card — READY / PARKED / HARD_DENY (catalog)

See `docs/PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md`. Folds 2ijf denser2 MULTI_HIT + 2ijg TRACK2 **MULTI_STABLE** + Instant peacetime PARK + midflight ceiling + Post CLOSED into one agent-facing card.

- **READY:** clock/queue health; PATH200@+0x60; OG+0x50 membership proxy (name stubbed); multi STABLE 2643→[3945,2679] oi=448; factory/VT FN MATCH catalogs; PATH≠Inst honesty; INST_VT/CP_VT catalog-only.
- **PARKED:** Instant/Inst70/ARR88/tri70 empty re-polls; peacetime Instant×PATH; non-interactive midflight re-polls; Assign oi≠0 quiet; **further PATH/OG50-only densify (diminishing returns)**.
- **HARD_DENY:** allow_post / Post inject / ring_embed live / 2fb/2gk execute / tool-gate / 5x / invent field names / Capstone/121.
- **Path C honesty (t50u):** still ~60%; this consolidate ≠ +10pp; ~70% needs Instant or SAFE Post/midflight — not more PATH polish.


### 2iji SAFE Post gate checklist (catalog)

See `docs/PHASE2IJI_SAFE_POST_GATE_CHECKLIST.md`. Turns 2ijh READY/PARKED/HARD_DENY into enable gates **G1–G6**. Perception READY ≠ allow Post. Missing: midflight CMove (G1), ring_embed live (G2), Instant wartime (G3), human ALLOW_POST (G4), tool-gate (G5), one Post (G6). PathC ~60% honesty.



### 2ijj G1 Strategic-only acceptance (catalog)

See `docs/PHASE2IJJ_G1_STRATEGIC_ONLY_ACCEPTANCE.md`. Live Strat factory **4753 MATCH** + VT FN MATCH; offline 2fd bit_identical + 2gk DESIGN. G1 alternate to midflight CMove for SAFE Post *discussion* — **G2/G4/G5/G6 still block**. allow_post False. PathC ~60% honesty.


### 2ijl agent card — G1 Strategic-only + G2 RO prep fold (catalog)

See `docs/PHASE2IJL_AGENT_CARD_G1G2_FOLD.md`. Folds **2ijj G1 ACCEPTABLE** + **2ijk G2 RO prep HIT** into one READY/PARKED/HARD_DENY card with G1–G6 states.

- **READY (+G1/G2 RO):** prior 2ijh surfaces + Strategic-only G1 ACCEPTABLE + ring INLINE_BLOB / G2 RO prep catalog (live embed still STUBBED).
- **PARKED:** Instant peacetime; midflight empty; PATH/OG50 densify; G2 **live** until human SAFE Post.
- **HARD_DENY:** allow_post / Post / ring_embed live / tool-gate / 5x / invent names / ask-user Post / Capstone/121.
- **Gates:** G1 ACCEPTABLE (Strategic-only) · G2 RO HIT / live STUBBED · G3 PARKED · G4/G5/G6 human-gated CLOSED.
- Live reaffirm: pid 31788 day_index=227 ui=1936-08-15 factory/FN True/True Strat4753=True.
- **Path C honesty (t50u):** still ~60–62%; this fold ≤+1–2pp clarity; ~70% NOT crossed (G2 live / G4+).


### 2ijm factory/Post-ABI/clock RO (catalog)

See `docs/PHASE2IJM_FACTORY_POSTABI_CLOCK_RO.md`. Live reaffirm factory/FN/Strat4753 + post_abi↔offsets_verified + Dummy INLINE ring; G4–G6 human gates restated. allow_post False. pid 31788 day_index=241 ui=1936-08-29.
PathC ~60–62%; ~70% NOT crossed.


### Proven RO constants (session)

| Symbol | Value |
| --- | --- |
| `G_GAMESTATE` / hours UI | `0x33dd6b0` / GS`+0x484` |
| `G_SESSION` | `0x34ffbe8` |
| pending / stage / drain / exec | server`+0x58` / sess`+0x54` / `+0x60` / `+0x6c8` |
| cmd IsValid / Execute slots | VT`+0x48` / VT`+0x50` |

### Land catalogs — factory + live VT FN MATCH

| Family | factory_idx | factory MATCH | VT+0x48/0x50 FN MATCH | Slice |
| --- | --- | --- | --- | --- |
| MOVE / SA / Cancel / Strategic | 1402 / 3620 / 1415 / 4753 | True | True | 2hb (+2gy) |
| Assign / Unassign / Execute | 3350 / 3365 / 3352 | True | True | 2ha (+2gz) |

Layouts (MATCH, still no Post): Strategic 2fa/2fb; MOVE offline skeleton 2gj; Assign units `CPdxArray@+0x28` stride8 `{type,index}`; oi@`+0x48`.

### What land agent can feed today (RO)

| ID | Signal | How / status |
| --- | --- | --- |
| `LOCATE` | CArmy | handle type=51 + country_tag — HIT 2gp |
| `PATH200` | multi-prov candidates | 2hy hxfocus hits=25 by_prov=[1176:9,3816:3,3938:13] hiband=21 nonempty=25 |
| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` — 2hw outlier prov→oi={} widen_rev=2/2 |
| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2iv cohort rehome alive=[461, 1042] homed={461: [], 1042: [1454], 2647: [], 2649: [], 2671: []} stale_alive=[] bands={'1-499': 151, '500-999': 16, '1000-1499': 18, '1500-2000': 33} primary_oi=1454 clock=CONTINUOUS (name STUBBED) |
| `ASSIGN51` | Assign units→CArmy | type=51 when sighted; oi often 0 — HIT 2gp |
| `FACTORY` | cmd factory slots | MOVE/SA/Cancel/Strat + Assign/Unassign/Execute — MATCH 2gy–2hb |
| `FN_VT` | IsValid/Execute | live VT`+0x48`/`+0x50` ≡ catalog — MATCH 2ha/2hb |
| `CLOCK` | hours/UI/counters + year@+0x478 | HIT 2hg (RELOAD_OR_NEW_CAMPAIGN_LIKELY; hours=UI; year may disagree) |
| `RING_LAYOUT` | Dummy ring@+0xa0 INLINE blob | RO layout + seq@+0xd0 — HIT 2hf (embed still STUBBED) |

### HARD_DENY / do not invent

| ID | Item | Gate |
| --- | --- | --- |
| `MIDFLIGHT` | CMove/SA/Cancel midflight hex | HONEST_EMPTY 2gt+2gv — stop re-poll |
| `NAMED_DEST` | named movement_dest | HONEST_EMPTY 2go |
| `ASSIGN_OI` | Assign units↔OI when oi≠0 | QUIET 2gq–2gx |
| `RING` | ring_embed / Dummy recreate in-process | STUBBED — needs SAFE Post (layout RO ≠ embed) |
| `POST` | Post / tool-gate / 2fb\|2gk execute | HARD_DENY allow_post=False |
| `OG50NAME` | demangled OG`+0x50` name | STUBBED |
| `SPEED5X` | game speed 5x | NEVER |

### Human-gated next (still CLOSED — do not ask user to right-click / enable Post)

```
[~] A  G1 Strategic-only ACCEPTABLE (2ijj); ordinary CMove midflight still optional/STUBBED
[~] B  G2 RO prep HIT (2ijk INLINE_BLOB + needs catalog); **live ring_embed still STUBBED**
[ ] C  Human CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] D  Dedicated tool-gate open + NEVER_POST
[ ] E  ONE land MOVE|Strategic Post @1x; verify; pause; unset
```

Until A–B green and human does C: **gate stays CLOSED**.

**2hc live:** result=`AGENT_READINESS_ONE_SUMMARY` · move_family=True · assign_family=True · walkback 380/380 · hours=347 UI=1936-01-15 11:00 · allow_post=False.
**2hd SAFE_POST §6f pointers:** result=`SAFEPOST_6F_POINTERS_POLISH` · move_family=True · assign_family=True · walkback 380/380 · hours=357 UI=1936-01-15 21:00 · allow_post=False.
**2he factory+execlist corner:** result=`FACTORY_EXECLIST_RING_CORNER` · all_factory=True · dummy_vt=True · execlist_empty=True · pending_empty=True · ring_present=True · hours=1 UI=1936-01-01 01:00 · allow_post=False.
**2hf ring layout polish:** result=`RING_INLINE_LAYOUT_POLISH` · kind=INLINE_BLOB · cap_like=0x10 · seq=84065 · hours=15 UI=1936-01-01 15:00 drain=325194 · allow_post=False · 2he ptr misread corrected.
**2hg clock+seq polish:** result=`CLOCK_RELOAD_RING_SEQ_POLISH` · class=RELOAD_OR_NEW_CAMPAIGN_LIKELY · hours=27 year=1937 (year_match=False; hours=UI) · seq=86628 Δseq=2563 · drain=336223 · allow_post=False.
**2hh post-reload perception:** result=`POST_RELOAD_PERCEPTION_HIT` · carmy=6 nonempty=2 multi=1 · walkback 387/387 · clock=RELOAD_OR_NEW_CAMPAIGN_LIKELY hours=41 UI=1936-01-02 17:00 · allow_post=False.
**2hi PATH200 denser:** result=`PATH200_DENSE_MULTI_HIT` · carmy=6 nonempty=2 multi=1 · offs=[0x60] · hours=52 UI=1936-01-03 04:00 · allow_post=False.
**2hj PATH200 multi-army matrix:** result=`PATH200_MULTI_ARMY_MATRIX_HIT` · carmy=6 empty=4 nonempty=2 multi=1 · off60=[idx=1042→[915, 490]; idx=1048→[3938]] · hours=66 UI=1936-01-03 18:00 · allow_post=False.
**2hk OG50 membership polish:** result=`OG50_MEMBERSHIP_POLISH_HIT` · walkback 387/387 · ita_members=21 · 2hj matrix fold multi=1042 nonempty=1048 empty=1039/1043/1046/1049 · hours=76 UI=1936-01-04 04:00 · allow_post=False.
**2hl OG50NAME demangle:** result=`OG50NAME_CLASS_HIT_LIVE_MISS` · MI_class=CArmy · raw=.?AVCArmy@@ · live_mi_match=False · hours=88 UI=1936-01-04 16:00 · allow_post=False.
**2hm OG↔path-army reverse:** result=`OG50_REVERSE_EMPTY_COHORT_ONLY` · 1042→[] · 1048→[] · og_hits=1 · hours=111 UI=1936-01-05 15:00 · allow_post=False.
**2hn OG×PATH crosstab:** result=`OG50_PATH_CROSSTAB_ALL_OUT` · hyp=PATH_BEARING_ABSENT_EMPTY_ALSO_OUT · ita=5 multi=0 nonempty=2 empty=3 · path_in=0 path_out=2 empty_in=0 · og_hits=0 · hours=130 UI=1936-01-06 10:00 · allow_post=False.
**2ho OG50 wide ITA scan:** result=`OG50_WIDE_ITA_HIT_HI` · ita=11 · ita_lo=0 ita_hi=6 · walk=1066/1066 · og_members=343 · player_tag_in_hist=6 · hours=145 UI=1936-01-07 01:00 · allow_post=False.
**2hp oi=481 Inst×PATH cross:** result=`OG481_MEMBERS_PATH_ONLY` · ita_members=6 · cross70=0 cross88=0 · path_union=[3816, 3938] · out_og_path=[(1039, [915]), (1042, [3816])] · hours=156 UI=1936-01-07 12:00 · allow_post=False.
**2hq PATH200 focus-prov denser:** result=`PATH200_FOCUS_PROV_HIT` · focus_hit_n=3 by_prov=[915:1,3816:2] · ita_ok=11 nonempty=4 · oi481_any_inst_vt=False · hours=174 UI=1936-01-08 06:00 · allow_post=False. hits=[idx=461→[3816]; idx=1039→[915]; idx=1042→[3816]]
**2hr INST_VT gate correct:** result=`INST_VT_GATE_CORRECT_CROSS_HIT` · live_vt=0x2a02558 · correct_demangle=COrderInstance · false_demangle=None · cross70=1 cross88=0 focus70=[915, 3816] · hours=190 UI=1936-01-08 22:00 · allow_post=False.
**2hs arr88 CP_VT correct:** result=`ARR88_CP_VT_CORRECT_HIT` · ids88=54 · kinds={'CProvince_correct': 54, 'CProvince_false_vt': 0, 'CArmy': 0, 'COrderInstance': 0, 'other': 0, 'nullish': 0} · cross88∩path=[] · cross88∩70_n=13 · focus_in_88=[] · pe_CP=CProvince · hours=203 UI=1936-01-09 11:00 · allow_post=False.
**2ht multi-oi Inst70×PATH:** result=`MULTI_OI_INST70_PATH_HIT` · oi_inst_ok=327 shaped70=164 · focus70={'915': [481], '3816': [481]} · path_armies=4 covered=4 · hours=218 UI=1936-01-10 02:00 · allow_post=False. hits=[idx=410→{'1176': [481]}; idx=461→{'3816': [481]}; idx=1042→{'1176': [481]}; idx=1043→{'1176': [481]}]
**2hu PATH×OG50×Inst70 triangle:** result=`PATH_OG50_INST70_TRIANGLE_HIT` · tri=1/2 · member_only=0 cover_only=1 · cand_ois=[481] · inst_ok=327 shaped70=164 · hours=233 UI=1936-01-10 17:00 · allow_post=False. hits=[idx=461 tri=[481] cover=[481] mem=[481]]
**2hv OG481 member rollup + cover reverse:** result=`OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT` · og50=6 walk=6 arr70=28 · ita_tri_members=2 ita_path=4 · cover_only=1 reverse_hit=0 · hours=247 UI=1936-01-11 07:00 · allow_post=False. ita_mem=[idx=461 path=[3816] tri=True; idx=410 path=[] tri=False; idx=455 path=[1176] tri=True; idx=445 path=[] tri=False; idx=382 path=[] tri=False; idx=463 path=[3938] tri=False] cover_rev=[idx=1046→ois=[]]
**2hw path∉Inst70 + cover widen:** result=`PATH_OUTLIER_COVER_WIDEN_HIT` · outliers=1 cover_only=2 · prov→oi={} · widen_rev=2/2 band=[512, 1023] · hours=260 UI=1936-01-11 20:00 · allow_post=False. out=[idx=463 out=[3938]→{}] widen=[idx=1042→[962]; idx=1046→[976]]
**2hx hi-band OG962/976 dig:** result=`HIBAND_OG962_976_DIG_HIT` · oi962 size=20 walk=20 arr70=0 expect_in=True tri=0, oi976 size=21 walk=21 arr70=0 expect_in=True tri=0 · cross70_n=0 shared=[] · ref481_arr70=28 · hours=280 UI=1936-01-12 16:00 · allow_post=False
**2hy PATH200 hxfocus denser:** result=`PATH200_HXFOCUS_DENSE_HIT` · focus_hit_n=25 by_prov=[1176:9,3816:3,3938:13] · new1176=9 focus_hiband=21 · ita_ok=50 nonempty=25 · hours=295 UI=1936-01-13 07:00 · allow_post=False. hits=[idx=455→[1176] hb=[]; idx=461→[3816] hb=[]; idx=463→[3938] hb=[]; idx=1042→[1176] hb=[962]; idx=1046→[3816] hb=[976]; idx=2640→[3938] hb=[]; idx=2641→[1176] hb=[962]; idx=2643→[1176] hb=[976]]
**2hz non-hiband path→OG50 reverse:** result=`NONHIBAND_PATH_OG50_REVERSE_HIT` · hit=4 · idx=455→ois=[481] path=[]; idx=461→ois=[481] path=[3816]; idx=463→ois=[481] path=[3938]; idx=2640→ois=[575] path=[3938] · oi_band=[1, 1200] oi_with_arr50=371 · hours=308 UI=1936-01-13 20:00 · allow_post=False
**2ia mid-band OG575 dig:** result=`MIDBAND_OG575_DIG_HIT` · oi575 size=3 walk=3 arr70=0 expect_in=True path_hit=True tri=0 · cross70_n=0 shared=[] · ref481_arr70=30 · hours=320 UI=1936-01-14 08:00 · allow_post=False
**2ib PATH200 denser→OG50 reverse:** result=`PATH200_ALL_REVERSE_HIT` · path_armies=20 hit=20 new_ois=[] oi_scanned=1200 oi_with_arr50=373 · hours=335 UI=1936-01-14 23:00 · allow_post=False
**2ic PATH∩OG481 Inst70 triangle:** result=`PATH_OG481_INST70_TRIANGLE_HIT` · path=23 tri=14 path_only=9 arr70=33 tri_in_481=2 · hours=347 UI=1936-01-15 11:00 · allow_post=False
**2id OG481 arr88×PATH denser:** result=`ARR88_PATH_DENSE_HIT` · path=13 arr70=33 arr88=64 cls={'tri70': 10, 'path_only': 2, 'tri70_88': 1} 3938_in70=False 3938_in88=False · hours=363 UI=1936-01-16 03:00 · allow_post=False
**2ie OG575 PATH shell denser:** result=`OG575_PATH_SHELL_DENSE_HIT` · size=4 walk=4 path_mem=1 tri481=1 po3938=0 expect=[1039, 1049, 2640] new=[2678] · ref481_arr70=30 · hours=10 UI=1936-01-01 10:00 · allow_post=False
**2if PATH200 reload→OG50 reverse:** result=`PATH200_RELOAD_REVERSE_HIT` · path_armies=20 hit=20 new_ois=[] oi_scanned=1200 oi_with_arr50=369 clock=RELOAD_OR_NEW_CAMPAIGN · hours=21 UI=1936-01-01 21:00 · allow_post=False
**2ig OG481 arr88 reload×PATH:** result=`ARR88_RELOAD_PATH_HIT` · path=17 arr70=28 arr88=55 cls={'path_only': 16, 'tri70_88': 1} 3938_in70=False 3938_in88=False clock=RELOAD_OR_NEW_CAMPAIGN · hours=30 UI=1936-01-02 06:00 · allow_post=False
**2ih known-OG PATH shells denser:** result=`KNOWN_OG_PATH_SHELLS_HIT` · shells=[481:6/2p, 575:4/1p, 962:16/8p, 976:17/2p] ref70=26 clock=RELOAD_OR_NEW_CAMPAIGN · hours=41 UI=1936-01-02 17:00 · allow_post=False
**2ii shell PATH×Inst drift denser:** result=`SHELL_PATH_INST_DRIFT_HIT` · path=15 arr70=27 arr88=27 cls={'path_only': 15} cross70=[] cross88=[] clock=CONTINUOUS · hours=54 UI=1936-01-03 06:00 · allow_post=False
**2ij PATH200 cont→OG50 reverse:** result=`PATH200_CONT_REVERSE_HIT` · path_armies=13 hit=13 new_ois=[] oi_scanned=1200 oi_with_arr50=364 clock=CONTINUOUS · hours=69 UI=1936-01-03 21:00 · allow_post=False
**2ik OG481 arr88 cont×PATH:** result=`ARR88_CONT_PATH_PARTIAL` · path=17 arr70=30 arr88=61 cls={'path_only': 17} 3938_in70=False 3938_in88=False clock=CONTINUOUS · hours=81 UI=1936-01-04 09:00 · allow_post=False
**2il PATH200 multi dense:** result=`PATH200_MULTI_DENSE_HIT` · multi=2 path_armies=2 hit=2 cls={'path_only': 2} dests=[256, 3938, 4527] cross70=[] cross88=[] clock=CONTINUOUS · hours=94 UI=1936-01-04 22:00 · allow_post=False
**2im PATH200 focus4527 dense:** result=`PATH200_FOCUS4527_DENSE_HIT` · dig=[4527, 256] path_armies=2 hit=2 cls={'path_only': 2} by_dig={'4527': [2644], '256': [2673]} dests=[256, 3938, 4527] cross70=[] cross88=[] clock=CONTINUOUS · hours=106 UI=1936-01-05 10:00 · allow_post=False
**2in PATH200 focus6867 dense:** result=`PATH200_FOCUS6867_DENSE_HIT` · dig=[6867, 490, 746, 875, 1048, 1656, 1869] path_armies=7 hit=7 cls={'path_only': 6, 'tri70_88': 1} by_dig={'6867': [461], '490': [2641, 2649, 2666], '746': [410], '875': [2641], '1048': [410, 2667], '1656': [], '1869': [2655]} dests=[489, 490, 746, 875, 1048, 1869, 3938, 6867] cross70=[6867] cross88=[6867] clock=CONTINUOUS · hours=125 UI=1936-01-06 05:00 · allow_post=False
**2io PATH200 inst70_tri dense:** result=`PATH200_INST70_TRI_DENSE_HIT` · dig=[884, 915, 918, 932, 3859, 3887, 3902, 6867, 6878, 6901, 9813, 9827, 9839, 11756, 11806, 11809, 11821, 11825, 13221, 13226, 13232] path_armies=5 hit=5 cls={'tri70_88': 5} by_dig={'6867': [461, 2644, 2675], '11825': [2645, 2649]} dests=[489, 490, 4527, 6867, 11825] cross70=[6867, 11825] cross88=[6867, 11825] clock=CONTINUOUS · hours=138 UI=1936-01-06 18:00 · allow_post=False
**2ip PATH200 pathonly_out70 dense:** result=`PATH200_PATHONLY_OUTSIDE70_HIT` · dig=[489, 490, 3816, 3938, 4527] path_armies=5 hit=5 cls={'path_only': 5} by_dig={'490': [2649, 2666], '3816': [382, 2641, 2678], '3938': [2649, 2666]} dests=[490, 3816, 3938] cross70=[] cross88=[] clock=CONTINUOUS · hours=151 UI=1936-01-07 07:00 · allow_post=False
**2iq PATH200 mixed70_comp dense:** result=`PATH200_MIXED70_COMPANION_HIT` · dig=[489, 490, 6867, 11825] path_armies=1 hit=1 cls={'tri70_88': 1} by_dig={'490': [2649]} dests=[490, 885] cross70=[885] cross88=[885] clock=CONTINUOUS · hours=164 UI=1936-01-07 20:00 · allow_post=False
**2ir PATH200 dense mixed+pathonly:** result=`PATH200_DENSE_MIXED_PATHONLY_HIT` · dig=[489, 490, 885, 1053, 1869, 4527, 6867] path_armies=11 hit=11 cls={'path_only': 11} by_dig={'489': [461, 2667], '490': [2666, 2675], '885': [463, 1043, 2644, 2649, 2655, 2666, 2678], '1053': [2682], '1869': [2655], '4527': [2644], '6867': [461, 2667, 2675, 2682]} dests=[489, 490, 885, 1053, 1869, 4527, 6867] cross70=[] cross88=[] clock=CONTINUOUS · hours=184 UI=1936-01-08 16:00 · allow_post=False
**2is PATH200 focus1053/1869:** result=`PATH200_FOCUS1053_1869_HIT` · dig=[885, 1053, 1869, 6867, 9840] path_armies=3 hit=3 cls={'tri70': 1, 'path_only': 2} by_dig={'885': [2655, 2682], '1053': [2682], '1869': [2655], '6867': [2648], '9840': [2648]} dests=[885, 1053, 1869, 6867, 9840] cross70=[9840] cross88=[] clock=CONTINUOUS · hours=198 UI=1936-01-09 06:00 · allow_post=False
**2it PATH200 ARR88×9840:** result=`PATH200_ARR88_9840_HIT` · dig=[489, 490, 740, 1656, 3579, 6901, 9840, 9857, 11838] path_armies=4 hit=2 cls={'tri70_88': 4} by_dig={'489': [461], '490': [2680], '740': [461, 2671, 2678, 2680], '1656': [2678], '3579': [2671]} dests=[489, 490, 740, 1656, 3579] cross70=[740] cross88=[740] clock=CONTINUOUS · hours=210 UI=1936-01-09 18:00 · allow_post=False
**2iu PATH200 focus740/OG50:** result=`PATH200_FOCUS740_OG50_HIT` · dig=[489, 490, 740, 1656, 3579] path_armies=5 hit=5 cls={'path_only': 5} by_dig={'489': [461], '490': [1042, 2649], '740': [461, 1042, 2647, 2649, 2671], '3579': [2671]} dests=[489, 490, 740, 3579] cross70=[] cross88=[] clock=CONTINUOUS · hours=222 UI=1936-01-10 06:00 · allow_post=False
**2iv cohort rehome:** result=`COHORT_REHOME_HIT` · alive=[461, 1042] homed={461: [], 1042: [1454], 2647: [], 2649: [], 2671: []} stale_alive=[] bands={'1-499': 151, '500-999': 16, '1000-1499': 18, '1500-2000': 33} primary_oi=1454 clock=CONTINUOUS · hours=229 UI=1936-01-10 13:00 · allow_post=False

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
| **2go** | `MOVEMENT_DEST_NAMED_HONEST_EMPTY` | PE strict named `movement_dest` family **0** hits; soft `+0x2B4` empty; no scalar≡`+0x200[-1]`; multi path still live (3) | Named dest STUBBED; Post/ring HARD_DENY |
| **2gp** | `ASSIGN_SIGHT_PLUS_OG50_MI_HIT` | ≤90s Assign/Unassign sight; units 410/445 = ITA CArmy; **OG+0x50 ≡ CArmy+0xB8** (VT `0x29d6fb8`) walkback 292/292 | Demangled +0x50 name stubbed; Assign oi=0 unset; Post/ring HARD_DENY |
| **2gq** | `ASSIGN_QUIET_OG50_CATALOG_POLISH` | ≤90s Assign oi≠0 hunt **quiet**; B walkback **294/294** reaffirm | oi≠0 units↔OI unconfirmed; Post/ring HARD_DENY |
| **2gr** | `ASSIGN_QUIET_DENSE_OG50_CATALOG_POLISH` | Clock nudge 205→206 + ≤90s pending/heap Assign oi≠0 **quiet**; B walkback **375/375** (oi 1..127) | oi≠0 units↔OI unconfirmed; Post/ring HARD_DENY |
| **2gs** | `PERCEPTION_READINESS_CATALOG_POLISH` | §6b perception map; ≤60s path snapshot; OG50 walkback reaffirm; SAFE_POST 2gp–2gr deltas | Post/ring HARD_DENY; oi≠0 still open |
| **2gt** | `MIDFLIGHT_HONEST_EMPTY` | ≤90s non-interactive midflight RO (CMove/SA/Cancel/Assign); §6c agent-facing summary | midflight hex / oi≠0 still open; Post HARD_DENY |
| **2gu** | `AGENT_FEED_CEILING_CATALOG_POLISH` | §6d can-feed / HARD_DENY consolidate (2gs+2gt+2gp–2gr); minimal live_meta | midflight hex / oi≠0 / Post HARD_DENY |
| **2gv** | `MIDFLIGHT_HONEST_EMPTY` | ≤90s non-interactive midflight RO reaffirm (CMove/SA/Cancel/Assign) | midflight hex / oi≠0 still open; Post HARD_DENY |
| **2gw** | `AGENT_CHECKLIST_CATALOG_POLISH` | §6e agent checklist (use RO / do not invent); ≤60s path+walkback; no midflight re-poll | midflight hex / oi≠0 / Post HARD_DENY |
| **2gx** | `ASSIGN_QUIET_FACTORY1402_MATCH` | ≤30s Assign oi≠0 edge + MOVE factory1402/execlist corner | oi≠0 / midflight / Post HARD_DENY |
| **2gy** | `SA_CANCEL_FACTORY_MATCH_OG50_WALKBACK` | SA3620/Cancel1415(+MOVE1402/Strat4753) factory MATCH + OG50 walkback 380/380 | oi≠0 / midflight / Post HARD_DENY |
| **2gz** | `ASSIGN_UNASSIGN_EXECUTE_FACTORY_MATCH` | Assign3350/Unassign3365/Execute3352(+MOVE1402) factory MATCH | oi≠0 / midflight / Post HARD_DENY |
| **2ha** | `ASSIGN_FN_MATCH_OG50_WALKBACK` | Assign/Unassign/Execute VT+0x48/0x50 FN MATCH + factory3350/3365/3352 + OG50 380/380 | oi≠0 / midflight / Post HARD_DENY |
| **2hb** | `MOVE_FAMILY_FN_FACTORY_MATCH` | MOVE/SA/Cancel/Strategic VT+0x48/0x50 FN MATCH + factory1402/3620/1415/4753 | oi≠0 / midflight / Post HARD_DENY |
| **2hc** | `AGENT_READINESS_ONE_SUMMARY` | §6f ONE agent-facing readiness (2ha+2hb FN/factory + OG50 + can-feed/HARD_DENY); live walkback 380/380 | oi≠0 / midflight / Post HARD_DENY |
| **2hd** | `SAFEPOST_6F_POINTERS_POLISH` | SAFE_POST §6f pointer + PHASE2HC expand; live move/assign FN+factory + OG50 380/380 | oi≠0 / midflight / Post HARD_DENY |
| **2he** | `FACTORY_EXECLIST_RING_CORNER` | Full land factory MATCH + Dummy execlist/ring/pending corner | oi≠0 / midflight / Post HARD_DENY |
| **2hf** | `RING_INLINE_LAYOUT_POLISH` | ring@+0xa0 INLINE layout polish (correct 2he ptr misread) + clock note | oi≠0 / midflight / Post HARD_DENY |
| **2hg** | `CLOCK_RELOAD_RING_SEQ_POLISH` | CLOCK reload≠wrap + ring seq delta vs 2hf | oi≠0 / midflight / Post HARD_DENY |
| **2hh** | `POST_RELOAD_PERCEPTION_HIT` | Post-reload ≤45s PATH200+OG50; 2hg CLOCK fold | oi≠0 / midflight / Post HARD_DENY |
| **2hi** | `PATH200_DENSE_MULTI_HIT` | PATH200 denser one-shot (nonempty/multi province vectors) | oi≠0 / midflight / Post HARD_DENY |
| **2hj** | `PATH200_MULTI_ARMY_MATRIX_HIT` | PATH200 multi-army matrix (empty+nonempty+multi @+0x60) | oi≠0 / midflight / Post HARD_DENY |
| **2hk** | `OG50_MEMBERSHIP_POLISH_HIT` | OG50 walkback polish + 2hj matrix fold into §6f | oi≠0 / midflight / Post HARD_DENY |
| **2hl** | `OG50NAME_CLASS_HIT_LIVE_MISS` | OG50NAME demangle attempt (MI VT RTTI + PE needles) | field name / oi≠0 / midflight / Post HARD_DENY |
| **2hm** | `OG50_REVERSE_EMPTY_COHORT_ONLY` | OG+0x50↔path-army reverse (1042/1048 vs empty) | field name / oi≠0 / midflight / Post HARD_DENY |
| **2hn** | `OG50_PATH_CROSSTAB_ALL_OUT` | OG+0x50 × PATH200@+0x60 ITA crosstab | field name / oi≠0 / midflight / Post HARD_DENY |
| **2ho** | `OG50_WIDE_ITA_HIT_HI` | OG+0x50 widen oi1..511 ITA + tag hist | field name / oi≠0 / midflight / Post HARD_DENY |
| **2hp** | `OG481_MEMBERS_PATH_ONLY` | oi=481 OG50×Inst70/88×PATH200 cross | field name / oi≠0 / midflight / Post HARD_DENY |
| **2hq** | `PATH200_FOCUS_PROV_HIT` | PATH200 denser focus {3816,3938,915} + oi=481 Instant VT dump | oi≠0 / midflight / Instant-map-repoll / Post HARD_DENY |
| **2hr** | `INST_VT_GATE_CORRECT_CROSS_HIT` | INST_VT false-gate fix 0x2A84A38→0x2A02558; oi=481 Instant×PATH | oi≠0 / midflight / Post HARD_DENY |
| **2hs** | `ARR88_CP_VT_CORRECT_HIT` | Instant+0x88 CP_VT fix 0x29D3C68→0x29EE248 id@+0xA4; oi=481 | oi≠0 / midflight / Post HARD_DENY |
| **2ht** | `MULTI_OI_INST70_PATH_HIT` | multi-oi Instant+0x70 × ITA PATH200 (corrected VTs) | oi≠0 / midflight / Post HARD_DENY |
| **2hu** | `PATH_OG50_INST70_TRIANGLE_HIT` | PATH×OG+0x50×Inst70 triangle (corrected INST_VT) | oi≠0 / midflight / Post HARD_DENY |
| **2hv** | `OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT` | OG481 member rollup + cover_only reverse | oi≠0 / midflight / Post HARD_DENY |
| **2hw** | `PATH_OUTLIER_COVER_WIDEN_HIT` | path∉Inst70 covering-oi + cover_only reverse widen | oi≠0 / midflight / Post HARD_DENY |
| **2hx** | `HIBAND_OG962_976_DIG_HIT` | hi-band OG962/976 dig Inst70+OG50+PATH | oi≠0 / midflight / Post HARD_DENY |
| **2hy** | `PATH200_HXFOCUS_DENSE_HIT` | PATH200 denser @2hx focus {1176,3938,3816,915} × hiband OG50 | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2hz** | `NONHIBAND_PATH_OG50_REVERSE_HIT` | non-hiband 2hy path armies → OG+0x50 reverse oi1..1200 | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ia** | `MIDBAND_OG575_DIG_HIT` | mid-band OG575 dig Inst70+OG50+PATH (2hz 2640 home) | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ib** | `PATH200_ALL_REVERSE_HIT` | PATH200 denser all-nonempty → OG50 reverse | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ic** | `PATH_OG481_INST70_TRIANGLE_HIT` | PATH200 ∩ OG481 Inst70 triangle denser | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2id** | `ARR88_PATH_DENSE_HIT` | OG481 Instant+0x88 CP_VT × denser PATH × Inst70 | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ie** | `OG575_PATH_SHELL_DENSE_HIT` | OG575 PATH-only shell denser × 481 Inst70 | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2if** | `PATH200_RELOAD_REVERSE_HIT` | post-reload PATH200 denser → OG50 reverse | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ig** | `ARR88_RELOAD_PATH_HIT` | post-reload OG481 Instant+0x88 × PATH denser | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ih** | `KNOWN_OG_PATH_SHELLS_HIT` | post-reload known-OG PATH shells denser | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ii** | `SHELL_PATH_INST_DRIFT_HIT` | shell-member PATH × 481 Inst70/ARR88 drift | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ij** | `PATH200_CONT_REVERSE_HIT` | CONTINUOUS PATH200 denser → OG50 reverse | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ik** | `ARR88_CONT_PATH_PARTIAL` | CONTINUOUS OG481 Instant+0x88 × PATH denser | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2il** | `PATH200_MULTI_DENSE_HIT` | CONTINUOUS PATH200 multi denser → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2im** | `PATH200_FOCUS4527_DENSE_HIT` | CONTINUOUS PATH200 focus (4527, 256) denser → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2in** | `PATH200_FOCUS6867_DENSE_HIT` | CONTINUOUS PATH200 focus 6867+2im-multi denser → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2io** | `PATH200_INST70_TRI_DENSE_HIT` | CONTINUOUS PATH200×live-Inst70-tri denser → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ip** | `PATH200_PATHONLY_OUTSIDE70_HIT` | CONTINUOUS PATH200 path-only-outside-Inst70 → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2iq** | `PATH200_MIXED70_COMPANION_HIT` | CONTINUOUS PATH200 mixed-Inst70+outside-companion → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2ir** | `PATH200_DENSE_MIXED_PATHONLY_HIT` | CONTINUOUS PATH200 dense-mixed+hiband-pathonly → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2is** | `PATH200_FOCUS1053_1869_HIT` | CONTINUOUS PATH200 focus1053+1869-reintersect → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2it** | `PATH200_ARR88_9840_HIT` | CONTINUOUS PATH200 arr88xpath-9840class → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2iu** | `PATH200_FOCUS740_OG50_HIT` | CONTINUOUS PATH200 focus740-og50-refresh → OG50+481 hub | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |
| **2iv** | `COHORT_REHOME_HIT` + `PATH200_RELAUNCH_PATH_ONLY_HIT` | cohort rehome + fresh ITA relaunch PATH200 path_only oi=70/57 | oi≠0 / midflight / Instant-repoll / Post HARD_DENY |

Docs: `docs/PHASE2GJ_MOVE_OFFLINE_LAYOUT.md`, `docs/PHASE2GK_STRATEGIC_RING_EMBED_DESIGN.md`.  
Recipes: `reports/phase2fb_ring_embed_recipe.json`, `reports/phase2gk_ring_embed_recipe_v2.json` — **DESIGN ONLY, never execute from agent slices.**

HARD_DENY unchanged: `allow_post` False · tool-gate CLOSED · no Post inject · no ask-user right-click · never 5x.


*Phase 2iv · cohort rehome · 2026-11-01 Asia/Shanghai*

**2iv relaunch PATH200:** result=`PATH200_RELAUNCH_PATH_ONLY_HIT` · fresh ITA `-start_tag=ITA -start_speed=1` pid=33840 · ita_ok=17 nonempty=2 multi=0 · 1040→[12857] oi=70 · 1053→[9945] oi=57 · focus740 miss · OG50 reverse oi_scanned=2000 oi_with_arr50=360 · clock=RELOAD_OR_NEW_CAMPAIGN year=1936 day_index=13 ui=1936-01-14 · allow_post=False · speed=1x CLI only · prior cohort 461/1042 N/A on new process · still NO ALLOW_POST / NO Post inject (2iw/2iy scripts not re-run).

**2iw NON-Post PATH200 oi57/70:** result=`PATH200_OI57_70_DENSE_HIT` · 1040→[12857] oi=70 · 1053→[9945] oi=57 · focus_oi_seed=2 · OG50 sizes 70:1 / 57:4 · Inst70 empty (inst_ok=False; Instant≠481) · ARR88×PATH in70_and_88=[] · clock=RELOAD_OR_NEW_CAMPAIGN ui=1936-01-14 · allow_post=False · historical Post 2iw script NOT re-run · still NO ALLOW_POST.

**2ix NON-Post longer PATH200:** result=PATH200_LONGER_STABLE_THIN · ~480s@1x day_index stuck=13 exec flat=8182 · PATH unchanged vs 2iw (1040/oi70, 1053/oi57) · new_dests=[] Inst70=[] · calendar stall honesty · allow_post=False · Post scripts not re-run.
**2iy PATH200 calendar unblock:** result=PATH200_CALUNBLOCK_DENSE_HIT · softlock prior pid33840 WS~238MB exec flat8182 day=13 → relaunch ITA@1x pid31788 · calendar_ok day10→11 exec↑ · PATH nonempty=2 multi=0 · new_ois=[45,55] (was 57/70) dests still [9945,12857] · inst_ok=[] · allow_post=False · NON-Post · see docs/PHASE2IY_PATH200_CALENDAR_UNBLOCKED.md
**2iz PATH200 1x advance denser:** result=PATH200_ADVANCE_MULTI_HIT · day24→36 (+12 @150s 1x) · nonempty=3 multi=0 · new_dest=[1903] oi=58@1041 · focus_oi_seed 45/55 still 9945/12857 · inst_ok=[] · PATH≠Inst honesty · allow_post=False · see docs/PHASE2IZ_PATH200_ADVANCE_DENSE.md
**2ija PATH200 longer advance CONTINUOUS:** result=PATH200_LONGER_ADVANCE_MULTI_N_HIT · day51→74 (+23 @300s 1x) clock=CONTINUOUS · nonempty=15 **multi=2** · new_dests=[415,740,2601,3938,3945,6906,9764,11707] new_ois=[65,448,450,478] · inst_ok=[] · PATH≠Inst honesty · allow_post=False · see docs/PHASE2IJA_PATH200_LONGER_ADVANCE.md
**2ijb Instant×PATH multi hunt:** result=INSTPATH_MULTI_PATH_INST_EMPTY · CONTINUOUS day85→90 (60s nudge) · multi_n=2 stable 2647/2683 · focus OIs 65/450/448/478 inst_ok=false · OG50 fat on 65/448 · PATH≠Inst honesty · allow_post=False · see docs/PHASE2IJB_INSTPATH_MULTI_HUNT.md
**2ijc PATH200/OG50 polish (Instant PARKED):** result=PATH200_OG50_POLISH_MULTI_HIT · CONTINUOUS day≈98 · multi_n=1 (2683 oi=450) · OG50 65/448=23 450=12 473=4 · no Instant VT dig · PATH≠Inst + Instant peacetime PARKED · allow_post=False · see docs/PHASE2IJC_PATH200_OG50_POLISH.md
**2ijd PATH200/OG50 denser (Instant PARKED):** result=PATH200_OG50_DENSE_HIT · CONTINUOUS day≈106 · multi_n=0 (2683 cleared) · new_ois=[495,503] · OG50 448=24 450=7 · no Instant dig · allow_post=False · see docs/PHASE2IJD_PATH200_OG50_DENSE.md
**2ije PATH200/OG50 track (Instant PARKED):** result=PATH200_OG50_TRACK_MULTI_HIT · CONTINUOUS day≈113 · multi_n=1 2649→[832,415] oi=448 · new_dest=832 new_oi=504 · PathC progress honesty ~60% (not +10pp) · allow_post=False · see docs/PHASE2IJE_PATH200_OG50_TRACK.md
**2ijf PATH200/OG50 denser2 (Instant PARKED):** result=PATH200_OG50_DENSE2_MULTI_HIT · CONTINUOUS day≈127 · multi_n=1 2643→[3945,2679] oi=448 · new_dest=2679 · PathC progress honesty ~60% (not +10pp) · allow_post=False · see docs/PHASE2IJF_PATH200_OG50_DENSE2.md
**2ijg PATH200/OG50 track2 (Instant PARKED):** result=PATH200_OG50_TRACK2_MULTI_STABLE · CONTINUOUS day≈144 · multi_n=1 stable 2643→[3945,2679] oi=448 · new_dest=[] · PathC progress honesty ~60% (not +10pp) · allow_post=False · see docs/PHASE2IJG_PATH200_OG50_TRACK2.md
**2ijh agent-card consolidate (NO PATH densify):** result=AGENT_CARD_READY_PARKED_DENY_CONSOLIDATE · READY/PARKED/HARD_DENY card · diminishing-returns note on PATH/OG50 · PathC ~60% honesty (not +10pp) · allow_post=False · see docs/PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md
**2iji SAFE-Post gate checklist (NO Post):** result=SAFE_POST_GATE_CHECKLIST_POLISH · G1–G6 missing matrix · PathC ~60% honesty (not +10pp) · allow_post=False · see docs/PHASE2IJI_SAFE_POST_GATE_CHECKLIST.md
**2ijj G1 Strategic-only acceptance:** result=G1_STRATEGIC_ONLY_ACCEPTANCE_PATH_HIT · Strat4753+FN MATCH · G1 alternate to CMove · G2/G4+ still block · PathC ~60% honesty (not +10pp) · allow_post=False · see docs/PHASE2IJJ_G1_STRATEGIC_ONLY_ACCEPTANCE.md

**2ijk G2 ring_embed RO prep:** result=`G2_RING_EMBED_RO_PREP_HIT` · INLINE_BLOB reaffirm server_vt_match=True · cap_like=0x10 · seq=49386 · day_index=213 UI=1936-08-01 drain=182898 exec=49293 · SAFE Post needs catalogued (offsets/VT/size/factory) · ring_embed live STUBBED · allow_post=False.










- **2ijk:** G2 ring_embed RO prep INLINE_BLOB + SAFE needs catalog; NO Post; Instant PARKED; PathC ~60–62% honesty (≤+1–2pp readiness clarity; ~70% NOT crossed; G2 live/G4+ still block).
- **2ijl:** agent card fold G1 ACCEPTABLE + G2 RO prep; NO Post; Instant PARKED; PathC ~60–62% honesty (≤+1–2pp; ~70% NOT crossed).
- **2ijm:** factory/Post-ABI/clock RO reaffirm; NO Post; Instant PARKED; PathC ~60–62% honesty (≤+1–2pp; ~70% NOT crossed).

*Phase 2ijk · G2 ring_embed RO prep · 2026-11-01 Asia/Shanghai*

*Phase 2ijl · agent card G1+G2 fold · 2026-11-01 Asia/Shanghai*

*Phase 2ijm · factory/Post-ABI/clock RO · 2026-11-01 Asia/Shanghai*
