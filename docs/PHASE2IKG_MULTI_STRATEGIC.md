# Phase 2ikg — Multi-army Strategic concentration (Retreat PARKED)

**Result:** `G6_MULTI_STRATEGIC_CONCENTRATE_HIT` HIT=True
**Primary choice:** B (Retreat `PARKED_NOT_PROVEN_CHEAP`)
**War:** WARTIME_ETH_CONTINUATION
**Speed:** pause/1x NEVER 5x
**Auth:** t52u

## Retreat proof

- retreat_order.py exists: False
- proven_post_abi: False → **PARKED_NOT_PROVEN_CHEAP**
- RO-only candidates: ['COrderNewFallbackCommand (factory ~4271) — RO', 'COrderReplaceFallbackCommands — RO', 'CWithdrawArmyHqCommand — RO', 'CSetSelectedArmyGroupFallback — RO']

## Multi-army Strategic 4753

- Anchor army 1042 dest province 6906
- Movers: [{'army': 1037, 'src_province': 3931}, {'army': 1038, 'src_province': 11838}]
- Posts: [{'army': 1037, 'src_province': 3931, 'dest': 6906, 'dry': {'ok': True, 'result': 'DRY_RUN_VALID', 'army': 1037, 'province': 6906, 'path_before': []}, 'post': {'ok': True, 'result': 'PATH_CONTAINS_DEST', 'army': 1037, 'province': 6906, 'post_rax': 1, 'path_before': [9857, 6901, 3816, 3954, 13223, 6966, 3873, 6817, 9896, 6906], 'path_after': [9857, 6901, 3816, 3954, 13223, 6966, 3873, 6817, 9896, 6906]}}, {'army': 1038, 'src_province': 11838, 'dest': 6906, 'dry': {'ok': True, 'result': 'DRY_RUN_VALID', 'army': 1038, 'province': 6906, 'path_before': []}, 'post': {'ok': True, 'result': 'PATH_CONTAINS_DEST', 'army': 1038, 'province': 6906, 'post_rax': 1, 'path_before': [11821, 9813, 3816, 3954, 13223, 6966, 3873, 6817, 9896, 6906], 'path_after': [11821, 9813, 3816, 3954, 13223, 6966, 3873, 6817, 9896, 6906]}}]
- Recheck: [{'army': 1037, 'province': 3931, 'path': [9857, 6901, 3816, 3954, 13223, 6966, 3873, 6817, 9896, 6906], 'dest_in_path': True, 'at_dest': False}, {'army': 1038, 'province': 11838, 'path': [11821, 9813, 3816, 3954, 13223, 6966, 3873, 6817, 9896, 6906], 'dest_in_path': True, 'at_dest': False}]
- Hits: ['HIT', 'HIT']
- Stability: {'seconds': 30.0, 'responding_stayed': True, 'alive_final': True, 'heap_exit': False, 'samples_n': 30}

## Gates

allow_post final=False; markers absent; Instant PARKED.

## Path C

~92-94%; crossed_70=YES; +~2pp multi-army Strategic concentration after 2ikf

*2026-11-01 23:27:09 Asia/Shanghai*


### Fold (2026-11-01 23:27 Asia/Shanghai)

## PHASE2IKG — multi-army Strategic concentration HIT (Retreat PARKED) — 2026-11-01 23:27 Asia/Shanghai

**Result:** G6_MULTI_STRATEGIC_CONCENTRATE_HIT HIT=true
**Primary choice:** B (Retreat PARKED_NOT_PROVEN_CHEAP — no retreat_order Post ABI; NewFallback/ReplaceFallback/WithdrawArmyHq RO/DISABLED only)

| Army | Strategic 4753 | path_after (tail→dest 6906 anchor 1042) |
|------|----------------|------------------------------------------|
| 1037 | PATH_CONTAINS_DEST | …→6906 (10-prov strategic path) |
| 1038 | PATH_CONTAINS_DEST | …→6906 (10-prov strategic path) |

**Bias:** MULTI_ARMY_FRIENDLY_COLOC_CONCENTRATE onto anchor province 6906; adjacency HONEST_EMPTY.
**Stability ~30s:** responding_stayed=True alive_final=True heap_exit=False.
**Gates:** allow_post False; markers absent. Instant PARKED. Cancel not needed.
**Path-C:** ~92–94% (crossed_70=YES; +~2pp vs 2ikf ~90–92%).
**Script:** scripts/phase2ikg_multi_strategic.py

