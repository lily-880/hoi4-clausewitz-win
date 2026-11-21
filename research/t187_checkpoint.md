# t187 checkpoint — meta.speed promoted from official CInGameIdler+0x6c1 pause flag

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, CInGameIdler, ETH index 44, country 0x26c4b672530, gs 0x26c259d0ff0. Date 1936-01-01 12, hour tick 60759371, GS+0x4BC speed index 0 (1x setting), GS+0x4B8 hour progress 0.0. Read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change.

## Official pause flag

CPauseGame (vtable 0x29e6e10) command token is `pausegame` (0x29ec, getter `0xe56c30`). Execute at vtable +0x50 (`0xe55060`) loads the idler singleton `G_IDLER` (RVA 0x33ddb08), calls **vtable +0x2f0**, then `jmp` **vtable +0x298** with `edx = command+0x48`.

On the live CInGameIdler (vtable 0x29e58d8, ptr 0x26cae443710):

- **Getter** `0xe46300` (vt+0x2f0): `movzx eax, byte ptr [rcx + 0x6c1]; ret`
- **Setter** `0xe487f0` (vt+0x298): takes the bool in `dl`; the force-pause path writes `[+0x6c1]=1` (and a sibling +0x6c3); a later path writes `[+0x6c1]=0`

Live **CInGameIdler+0x6c1 = 1**, so `meta.speed = pause`. This is the official flag, not an inference from hour progress.

Explicitly **not** the pause flag:

- `GS+0x4B8` f32 hour progress (0.0 here because the clock is paused; previously used only as a sampling hint)
- `GS+0x4BC` i32 speed index (0 = 1x setting, still 0 while paused)
- token `paused` 0x3691 belongs to the national-focus writer `0x2f52a0` (with `activate_shine_on_focus` / `completed` / `progress`)
- `unit_controller_pause` 0x35ba belongs to the CArmy secondary writer `0xced2e0`

Schema `meta.speed` is only `pause` | `1x`. This snapshot is `pause`. An unpaused 5x game is outside the standing pause/1x constraint and was not used to invent a value.

## Inventory

D drive official table **was updated**. Still 116 fields, 14 tables, 3 columns (`字段名 | 已验证/未验证 | 说明`). 47 verified / 69 unverified (was 46/70). Promoted `meta.speed`. SHA256 `98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201` (previous `2bf707a0a097487bb6e17797ab6cde12e6dcaf9203c90a3f984c222474299d62`). `complete_input` remains false. Offset key `pause_flag_t187`. 77 and [1835] were not promoted. t186 inventory test was frozen so it no longer pins the live D SHA to the t186 hash.

## Tests

187 prior + 6 new = 193 expected (`research/test_t187_input_pause.py`).

## Next

Independent ABI can continue, still without the six blocked samples: **plans** (do not promote the six CTheatre CFront border structures as player-drawn plans), **crises**, **visibility / FoW** spotted+confidence (foreign-army samples may prove structure, do not export fog-hidden situation), and building damaged / extra effective levels (1552CF0 remains a string formatter). `world.wars.front_invalidated` still has no named token.
