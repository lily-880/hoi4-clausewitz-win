# Phase 2ia — mid-band OG575 dig

**Result:** `MIDBAND_OG575_DIG_HIT`

**Constants:** INST_VT=0x2A02558 · OG+0x50 name STUBBED · expect idx=2640 path=3938

**Ref OG481 Inst70:** {"ok": true, "inst_ok": true, "arr70_n": 30}

**Dig:** {"oi": 575, "ok": true, "inst_ok": true, "inst_vt_rva": "0x2a02558", "arr98_size": 1, "arr70_n": 0, "u32s_head": [], "og50_size": 3, "walk_ok": 3, "expect_idx": 2640, "expect_in_og50": true, "expect_path_hit": true, "members": [{"index": 2640, "tag": 15, "ita": true, "walkback_ok": true, "path_ids": [3938], "path_n": 1, "dest_in_70": [], "triangle": false}, {"index": 1043, "tag": 15, "ita": true, "walkback_ok": true, "path_ids": [], "path_n": 0, "dest_in_70": [], "triangle": false}, {"index": 1039, "tag": 15, "ita": true, "walkback_ok": true, "path_ids": [], "path_n": 0, "dest_in_70": [], "triangle": false}], "triangle_n": 0, "ita_n": 3, "path_mem_n": 1}

**Cross Inst70 ∩ OG481:** {"shared_n": 0, "shared_head": [], "only_575_n": 0, "only_481_n": 30}

**Live:** pid 30352 · hours=320 UI=1936-01-14 08:00 · drain=586507 · allow_post=False · speed untouched

**Semantics:** Mid-band OG575 home of 2hz 2640→575 path[3938]. Instant may be empty (honest membership shell). Field name STUBBED. No invent. No Post / 463 Inst70 re-poll.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2ia · 2026-10-31 Asia/Shanghai · sha_base 8862357*
