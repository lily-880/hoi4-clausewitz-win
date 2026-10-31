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

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2ib `PATH200_ALL_REVERSE_HIT`); retry GitHub push when reachable. Still **NO ALLOW_POST**.



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

**Midflight ceiling:** 2gt+2gv both `MIDFLIGHT_HONEST_EMPTY` — stop non-interactive midflight re-polls until human leave or plan-dense Assign window.

## 6f. ONE agent-facing readiness summary (2hc)

**Status: CLOSED — allow_post False · tool-gate CLOSED · recipes NOT executed · never 5x.**
Folds §6b–§6e + **2ha** Assign FN/factory + **2hb** MOVE-family FN/factory + OG50 into one land-agent card.

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
| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ib PATH200 denser path_armies=20 hit=20 new_ois=[] oi_scanned=1200 oi_with_arr50=373 (name STUBBED) |
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
[ ] A  Ordinary CMove (+ embed) live midflight hex  — OR Strategic-only + human SAFE Post for ring_embed
[ ] B  Ring-embed recreate proof on captured buffer
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

Docs: `docs/PHASE2GJ_MOVE_OFFLINE_LAYOUT.md`, `docs/PHASE2GK_STRATEGIC_RING_EMBED_DESIGN.md`.  
Recipes: `reports/phase2fb_ring_embed_recipe.json`, `reports/phase2gk_ring_embed_recipe_v2.json` — **DESIGN ONLY, never execute from agent slices.**

HARD_DENY unchanged: `allow_post` False · tool-gate CLOSED · no Post inject · no ask-user right-click · never 5x.


*Phase 2ib · PATH200 denser all→OG50 reverse · 2026-10-31 Asia/Shanghai*
