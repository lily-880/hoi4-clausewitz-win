# Phase 2iki — Multi-army Attack after concentrate arrive-poll

**Result:** `G6_MULTI_ATTACK_CONCENTRATE_HIT` HIT=True
**Primary:** B (Retreat `HARD_DENY_PARKED_NOT_PROVEN_CHEAP`)
**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x

## Arrive poll (bounded ~8s)

- movers_arrived=False anchor_at_dest=True gate_open=True
- Last: {'t': 6.97, '1037': {'army': 1037, 'ok': True, 'province': 3931, 'path': [], 'path_len': 0, 'at_concentrate': False, 'dest_in_path': False}, '1038': {'army': 1038, 'ok': True, 'province': 11838, 'path': [], 'path_len': 0, 'at_concentrate': False, 'dest_in_path': False}, '1042': {'army': 1042, 'ok': True, 'province': 6906, 'path': [], 'path_len': 0, 'at_concentrate': True, 'dest_in_path': False}}

## Multi SupportAttack 3620 → 1886

- Attackers: [1042, 1037]
- Posts: [{'army': 1042, 'src_province': 6906, 'at_concentrate': True, 'target': 1886, 'dry': {'ok': True, 'result': 'DRY_RUN_VALID', 'province': 1886}, 'post': {'ok': True, 'result': 'ATTACK_POSTED_STABLE', 'army': 1042, 'province': 1886, 'post_rax': 1, 'post_wait': 0, 'path_before': [], 'path_after': [], 'factory_idx': 3620, 'buf_kind': 'inline_none', 'stub_meta': {'wait': 0, 'stub_leaked_on_timeout': False, 'stub_freed': True, 'elapsed_ms': 500}}}, {'army': 1037, 'src_province': 3931, 'at_concentrate': False, 'target': 1886, 'dry': {'ok': True, 'result': 'DRY_RUN_VALID', 'province': 1886}, 'post': {'ok': True, 'result': 'ATTACK_POSTED_STABLE', 'army': 1037, 'province': 1886, 'post_rax': 1, 'post_wait': 0, 'path_before': [], 'path_after': [], 'factory_idx': 3620, 'buf_kind': 'inline_none', 'stub_meta': {'wait': 0, 'stub_leaked_on_timeout': False, 'stub_freed': True, 'elapsed_ms': 500}}}]
- Hits: ['HIT', 'HIT']
- Stability: {'seconds': 30.0, 'responding_stayed': True, 'alive_final': True, 'heap_exit': False, 'samples_n': 30}

## Gates

allow_post=False; Instant PARKED; combat densify HONEST_EMPTY.

## Path C

~96-98%; crossed_70=YES; +~2pp multi-army Attack after concentrate arrive-poll gate

*2026-11-01 23:34:24 Asia/Shanghai*
