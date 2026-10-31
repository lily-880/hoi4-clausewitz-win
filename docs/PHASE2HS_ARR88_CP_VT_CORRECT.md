# Phase 2hs — Instant+0x88 CP_VT false-gate correction

**Result:** `ARR88_CP_VT_CORRECT_HIT`

**False gate:** 2hr/2hp/2gm used `CP_VT=0x29D3C68` (+ id@+0x18) → arr88 other=32.

**Correct (2fx):** `CP_VT=0x29EE248` · id@`+0xA4`.

**PE demangle CP:** `CProvince`

**Live oi=481:** inst_ok=True · ids88=54 · kinds={'CProvince_correct': 54, 'CProvince_false_vt': 0, 'CArmy': 0, 'COrderInstance': 0, 'other': 0, 'nullish': 0} · vt_hist={'0x29ee248': 54}

**Cross:** path∩88=[] · 70∩88_n=13 · focus_in_88=[] · focus_in_70=[915, 3816]

**ids88 sample:** [10063, 7068, 1176, 7068, 1090, 7068, 1090, 7198, 10111, 7198, 10111, 6744, 3871, 6744, 875, 6744, 875, 1178, 875, 9891, 875, 879, 3871, 879, 3810, 879, 3810, 809, 3810, 3930, 3810, 6948, 6832, 6948, 9881, 6948, 9881, 3986, 858, 3986, 896, 3986, 896, 11820, 939, 11820, 939, 3845]

**pairs (hub,neighbor) sample:** [[10063, 7068], [1176, 7068], [1090, 7068], [1090, 7198], [10111, 7198], [10111, 6744], [3871, 6744], [875, 6744], [875, 1178], [875, 9891], [875, 879], [3871, 879], [3810, 879], [3810, 809], [3810, 3930], [3810, 6948]]

**Live:** pid 30352 · hours=203 UI=1936-01-09 11:00 · drain=487043 · allow_post=False · speed untouched

**Semantics:** One-shot CP_VT correction + cross; not endless Instant poll. Field name STUBBED. No invent. No Post / midflight / oi≠0.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2hs · 2026-10-31 Asia/Shanghai · sha_base 27c0971*
