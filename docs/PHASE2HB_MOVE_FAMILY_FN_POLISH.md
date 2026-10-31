# Phase 2hb — MOVE/SA/Cancel/Strategic FN polish

**Result:** `MOVE_FAMILY_FN_FACTORY_MATCH`

**FN:** all_fn_match=True · all_factory_match=True

| cmd | vt | factory_idx | isvalid (cat/live) | execute (cat/live) |
|-----|-----|-------------|--------------------|--------------------|
| MOVE | 0x2a2c790 | 1402 | 0x14002f0 / live 0x14002f0 match=True | 0x13fc990 / live 0x13fc990 match=True |
| CANCEL | 0x2a2c9b8 | 1415 | 0x13fed40 / live 0x13fed40 match=True | 0x13fbbd0 / live 0x13fbbd0 match=True |
| SUPPORT_ATTACK | 0x2a2cb28 | 3620 | 0x1402270 / live 0x1402270 match=True | 0x13fdd00 / live 0x13fdd00 match=True |
| STRATEGIC | 0x2a2d818 | 4753 | 0x1402260 / live 0x1402260 match=True | 0x13fc990 / live 0x13fc990 match=True |

Note: MOVE and STRATEGIC share catalog execute RVA (documented).

**Live:** pid 30352 · hours=338 · UI 1936-01-15 02:00 · pending=0 stage=0 · allow_post=False

**Semantics:** Live VT+0x48 IsValid / VT+0x50 Execute MATCH catalog for MOVE/SupportAttack/Cancel/Strategic; factory slot reaffirm. No midflight / no Post / never 5x.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2hb · 2026-10-31 Asia/Shanghai · sha_base 7488820*
