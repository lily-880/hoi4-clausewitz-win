# t186 checkpoint — world.wars.a / b / state promoted; front_invalidated not promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, CInGameIdler, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Date 1936-01-01 12, hour tick 60759371, speed notch 1. 21 own divisions. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change.

## Official war ABI

CRelation writer `0xd8f520` (vtable 0x29dcb48 +0x10):

- `first` (0x28de): country index at +0x10, formatted via `0xc08170`
- `second` (0x28df): country index at +0x14
- `cancel` (0x28e5): byte +0x48, written iff nonzero
- `start_date` (0x28e0): CGameDate (secondary vtable at +0x28, hour tick at +0x20), written when cancel==0
- `end_date` (0x28e1): CGameDate at +0x40, written iff dword [+0x38] > dword [+0x20]

CWarRelation writer `0xd8f900` (vtable 0x29dcc08 +0x10) calls `0xd8f520`, then casualties, war scores, `first_was_instigator` byte +0x158, wargoal arrays, and `hostility_reason_instigator` / `_defender` from dwords +0x160 / +0x15c (enum 0=`war`, 1=`puppet`, 2=`ally`, 3=`asked_to_join`, 4=`guarantee`, 5=`not_applicable`). Hostility reason is **not** War.state.

CDiplomacyStatus lives at CCountry+0xf88. Writer `0xdad1a0` starts with `active_relations` (0x2e43): data +0x8, size +0x14, 440 `CRelationStatus*` (slot 0 is the null object; index is country index). This array is **not** a war list and was not treated as one.

The official war pointer is **CRelationStatus+0x2e8** (`CWarRelation*`). Getters `0xd7db8b` / `0xd7deb0` / `0xd7da30` resolve first country's diplomacy (`CCountry+0xf88`), index the second country in `active_relations`, and return `[status+0x2e8]`. Reader `0xd82c10` also skips the pointer when it is null or when **byte +0x49 is nonzero**.

CGameDate stores an hour tick at primary +0x8 (add-day = +24, add-year = +8760). On this snapshot the start_date tick at CRelation+0x20 equals the current campaign hour 60759371 (1936-01-01 12), so the historical outbreak day is **not** claimed.

## Live snapshot

A full scan of every country's `CRelationStatus+0x2e8` found **exactly one** `CWarRelation`, object `0x26c70b635d0`, shared by ITA→ETH and ETH→ITA:

- first = 16 ITA, second = 44 ETH
- cancel = 0, byte +0x49 = 0
- end_date gate [+0x38] > [+0x20] is false, so the official writer omits `end_date`
- first_was_instigator = 1 (ITA)
- hostility reasons = 0 (`war`)

This is the 1936 Italo-Ethiopian war. The player (ETH) is a participant, so the war is player-visible. No other world war was present to leak through fog.

Schema mapping: `a` = official first, `b` = official second, `state` = `at_war` from the official active-war encoding above. `ceasefire` / `capitulated` / `puppeted` / `not_at_war` encodings are not proven (do not use hostility_reason, and do not use the country-level `capitulated` byte at CDiplomacyStatus+0x328). `front_invalidated` has no named token and stays unverified.

## Inventory

D drive official table **was updated**. Still 116 fields, 14 tables, 3 columns (`字段名 | 已验证/未验证 | 说明`). 46 verified / 70 unverified (was 43/73). Promoted `world.wars.a`, `world.wars.b`, `world.wars.state`. `world.wars.front_invalidated` remains 未验证. SHA256 `2bf707a0a097487bb6e17797ab6cde12e6dcaf9203c90a3f984c222474299d62` (previous `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254`). `complete_input` remains false. Offset key `war_relation_t186`. 77 and [1835] were not promoted. No produced=min(need, stock). t181–t185 inventory tests were frozen so they no longer pin the live D SHA to the t181 hash.

## Tests

181 prior + 6 new = 187 expected (`research/test_t186_input_wars.py`).

## Next

Independent ABI can continue on other unverified inventory fields that do not need the already-blocked samples: official **pause** flag (`meta.speed` still lacks a proven pause bit), **plans** (the six CTheatre fronts remain border structures, not player-drawn plans), **crises**, **visibility / FoW**, and building damaged / extra effective levels (1552CF0 remains a string formatter). Do not spin on in_combat / order.type / leaders.assigned_to / empty formation groups / empty combats / in_supply.
