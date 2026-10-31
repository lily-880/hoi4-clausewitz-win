# Phase 2hl — OG50NAME demangle attempt

**Result:** `OG50NAME_CLASS_HIT_FIELD_STUBBED`

**MI VT `0x29d6fb8` RTTI:** raw=.?AVCArmy@@ · demangled=CArmy

**Live MI check:** [{'index': 1039, 'army': '0x1eac93f3690', 'tag': 15, 'primary_vt_rva': '0x29d6d68', 'sec_vt_rva': '0x29d6f48', 'mi_vt_rva': '0x29d6fb8', 'mi_vt_match': True}, {'index': 1042, 'army': '0x1eac93f5df0', 'tag': 15, 'primary_vt_rva': '0x29d6d68', 'sec_vt_rva': '0x29d6f48', 'mi_vt_rva': '0x29d6fb8', 'mi_vt_match': True}, {'index': 1043, 'army': '0x1eac93f4a40', 'tag': 15, 'primary_vt_rva': '0x29d6d68', 'sec_vt_rva': '0x29d6f48', 'mi_vt_rva': '0x29d6fb8', 'mi_vt_match': True}, {'index': 1046, 'army': '0x1eac9428150', 'tag': 15, 'primary_vt_rva': '0x29d6d68', 'sec_vt_rva': '0x29d6f48', 'mi_vt_rva': '0x29d6fb8', 'mi_vt_match': True}]

**Field needles with hits:** ['m_armies', 'm_units', 'm_members', 'COrderGroup']

**PE error:** None

**Live:** pid 30352 · hours=99 UI=1936-01-05 03:00 · drain=397534 · allow_post=False · speed untouched

**Semantics:** Class demangle of MI VT ≠ demangled OG+0x50 *field* name. Inventing a field name without PE/RTTI evidence is HARD_DENY. No Post.

**Catalog fold:** 2hk walkback 387/387 ita=21; 2hj matrix 1042/1048 @+0x60.

**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.

*Phase 2hl · 2026-10-31 Asia/Shanghai · sha_base 7e5ec1e*
