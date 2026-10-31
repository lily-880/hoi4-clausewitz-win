# Phase 2hw — path∉Inst70 covering-oi + cover_only reverse widen

**Result:** `PATH_OUTLIER_COVER_WIDEN_HIT`

**Constants:** INST_VT=0x2A02558 · OG+0x50 name STUBBED

**Focus OG481:** {"inst_ok": true, "arr70_n": 28, "og50_size": 6, "member_n": 6}

**Outlier armies (∈OG481 ∧ path∉Inst70):** [{"index": 463, "army": "0x1eac8d31520", "mi": "0x1eac8d315d8", "path_ids": [3938], "dest_in_70": [], "dest_out_70": [3938], "in_og481": true, "out_cover_ois": {"3938": []}}]

**Outlier dest → covering oi (Inst70 oi1..511):** {}

**oi_hit_rows:** []

**Cover_only reverse widen oi512..1023:** {"cover_only_n": 2, "reverse_hit_n": 2, "rows": [{"index": 1042, "path_ids": [1176], "dest_in_70": [1176], "member_ois_widen": [962], "reverse_hit": true}, {"index": 1046, "path_ids": [3816], "dest_in_70": [3816], "member_ois_widen": [976], "reverse_hit": true}], "oi_band": [512, 1023]}

**Live:** pid 30352 · hours=260 UI=1936-01-11 20:00 · drain=535395 · allow_post=False · speed untouched

**Semantics:** Path dest outside focus Instant+0x70 may still appear in other orders' +0x70; cover_only may live in oi>511. Field name STUBBED. No invent. No Post.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2hw · 2026-10-31 Asia/Shanghai · sha_base aef0b09*
