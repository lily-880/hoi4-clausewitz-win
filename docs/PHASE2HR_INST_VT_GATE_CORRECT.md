# Phase 2hr — INST_VT false-gate correction

**Result:** `INST_VT_GATE_CORRECT_CROSS_HIT`

**False gate:** scripts used `INST_VT=0x2A84A38` (2hp/2hq/2gm) → `inst_vt_ok=False` despite live VT `0x2a02558`.

**Correct:** `INST_VT=0x2A02558` (2fu/2fv/2fx/2fy/2fz/2ga) = COrderInstance.

**PE demangle:** correct→`COrderInstance` · false→`None`

**Live oi=481:** vt=0x2a02558 · matches_correct=True · cross70=1 cross88=0 · path_union=[3816, 3938] · focus_in_70=[915, 3816] focus_in_88=[]

**arr70:** {"size": 25, "shaped": true, "u32s": [10063, 1176, 1090, 10111, 3871, 3810, 6832, 9881, 858, 896, 939, 3794, 9767, 6841, 11806, 3859, 857, 3887, 11766, 813, 3816, 9813, 11793, 11819, 915]}

**arr88 kinds:** {'CProvince': 0, 'CArmy': 0, 'COrderInstance': 0, 'other': 32, 'nullish': 0} · ids=[]

**Live:** pid 30352 · hours=190 UI=1936-01-08 22:00 · drain=475851 · allow_post=False · speed untouched

**Semantics:** One-shot gate correction + Instant×PATH; not endless Instant poll. Field name STUBBED. No invent. No Post / midflight / oi≠0.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2hr · 2026-10-31 Asia/Shanghai · sha_base 31ace87*
