# Phase 2hu — PATH × OG+0x50 × Instant+0x70 triangle

**Result:** `PATH_OG50_INST70_TRIANGLE_HIT`

**Constants:** INST_VT=0x2A02558 · OG+0x50 ≡ CArmy+0xB8 MI (name STUBBED) · CA_MI_VT=0x29D6FB8

**OG Instant scan:** inst_ok=327 · shaped70=164

**Candidate covering ois:** [481]

**OG+0x50 (candidates):** {"481": {"size": 6, "walk_ok": 6, "ok": true}}

**Triangle:** 1/2 · member_only=0 · cover_only=1

**Army hits:** [{"index": 461, "path_ids": [3816], "mi_ok": true, "dest_cover_ois": {"3816": [481]}, "cover_ois": [481], "member_ois": [481], "triangle_ois": [481], "triangle": true}, {"index": 1042, "path_ids": [1176], "mi_ok": true, "dest_cover_ois": {"1176": [481]}, "cover_ois": [481], "member_ois": [], "triangle_ois": [], "triangle": false}]

**Live:** pid 30352 · hours=233 UI=1936-01-10 17:00 · drain=512273 · allow_post=False · speed untouched

**Semantics:** Perception closure: army ∈ OG(oi) via +0x50 walkback AND path dest ∈ Instant+0x70(oi). Field name STUBBED. No invent. No Post / midflight / oi≠0 / endless Instant poll.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2hu · 2026-10-31 Asia/Shanghai · sha_base b4fe74e*
