#!/usr/bin/env python3
"""Phase 2hx: hi-band OG962/976 dig (Inst70 + OG50 + PATH) (RO).

Homes of 2hw cover_only reverse hits (1042→962, 1046→976). Catalog members,
Instant+0x70, PATH triangles; cross shared dests with OG481 Inst70. Corrected
INST_VT=0x2A02558. OG+0x50 name STUBBED. One-shot; no Post; never 5x; no speed
write; no midflight; no Assign oi≠0; no endless Instant poll; no 463 Inst70
re-poll of oi1..511.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hx_hiband_og962_976_dig.json"
SUMMARY = ROOT / "reports" / "phase2hx_summary.json"
DOC = ROOT / "docs" / "PHASE2HX_HIBAND_OG962_976_DIG.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
FOCUS_OIS = (962, 976)
REF_OI = 481
EXPECT = {962: 1042, 976: 1046}  # from 2hw; live may differ
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
ARMY_LO, ARMY_HI = 1, 2000
SHA_BASE = "182f670"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def looks_like_province(v: int) -> bool:
    return 1 <= v <= 20000


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    year = i32(b, gs + 0x478)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "year_at_0x478": year,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": tag,
        "scenario": (
            "ITA hi-band OG962/976 dig Inst70+OG50+PATH "
            "(INST_VT corrected; no Post; OG50 name STUBBED; no 463 Inst70 re-poll)"
        ),
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def path60(b, base, army, tag):
    blob = try_read(b, army + PATH_OFF, 24)
    if not blob or len(blob) < 24:
        return {"n": 0, "province_ids": []}
    begin, end, _cap = struct.unpack_from("<QQQ", blob, 0)
    vals = []
    if begin >= 0x10000 and end >= begin and (end - begin) // 4 <= 64:
        n = (end - begin) // 4
        raw = try_read(b, begin, n * 4)
        if raw and len(raw) >= n * 4:
            vals = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(n)]
            if not (vals and all(looks_like_province(v) for v in vals)):
                vals = []
    if not vals:
        data, _c, size = struct.unpack_from("<Qii", blob, 0)
        if data >= 0x10000 and 0 < size <= 64 and not (base <= data < base + 0x4000000):
            raw = try_read(b, data, size * 4)
            if raw and len(raw) >= size * 4:
                vals = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(size)]
                if not (vals and all(looks_like_province(v) for v in vals)):
                    vals = []
    if len(vals) == 1 and vals[0] == tag:
        return {"n": 0, "province_ids": []}
    return {"n": len(vals), "province_ids": vals[:12]}


def read_cpdx_ptrs(b, base, arr_addr, max_n=48):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
    except Exception:
        return None
    if not data or size <= 0 or size > 4096:
        return None
    if base <= data < base + 0x4000000:
        return {"size": size, "in_image_sentinel": True, "ptrs": []}
    n = min(size, max_n)
    blob = try_read(b, data, n * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    return {
        "size": size,
        "in_image_sentinel": False,
        "ptrs": [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(n)],
    }


def read_cpdx_u32(b, base, arr_addr, max_n=64):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
    except Exception:
        return None
    if not data or size <= 0 or size > 4096:
        return None
    if base <= data < base + 0x4000000:
        return {"size": size, "in_image_sentinel": True, "u32s": []}
    n = min(size, max_n)
    blob = try_read(b, data, n * 4)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "u32s": []}
    return {
        "size": size,
        "in_image_sentinel": False,
        "u32s": [struct.unpack_from("<I", blob, j * 4)[0] for j in range(n)],
    }


def build_ptr_index(b, base):
    ptr_to_idx = {}
    for idx in range(ARMY_LO, ARMY_HI + 1):
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            continue
        if not army:
            continue
        vt = try_u64(b, army)
        if not vt or (vt - base) != CA_VT_RVA:
            continue
        ptr_to_idx[army] = idx
    return ptr_to_idx


def dig_oi(b, base, tag, oi, ptr_to_idx):
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        return {"oi": oi, "ok": False, "error": "resolve_fail"}
    if not hdr:
        return {"oi": oi, "ok": False, "error": "null_hdr"}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    inst_ok = False
    set70 = set()
    arr70_n = 0
    u32s_head = []
    inst_vt_rva = None
    arr98_size = (arr98 or {}).get("size")
    if ptrs:
        inst = ptrs[0]
        vt = try_u64(b, inst)
        if vt:
            inst_vt_rva = vt - base
        inst_ok = bool(vt and (vt - base) == INST_VT)
        if inst_ok:
            a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
            if a70 and not a70.get("in_image_sentinel"):
                u32s = a70.get("u32s") or []
                if u32s and all(looks_like_province(v) for v in u32s):
                    set70 = set(u32s)
                    arr70_n = len(u32s)
                    u32s_head = u32s[:8]

    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
    members = []
    walk_ok = 0
    expect_idx = EXPECT.get(oi)
    expect_in = False
    for p in (arr50 or {}).get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        primary = p - CA_MI_OFF
        avt = try_u64(b, primary)
        mi_vt = try_u64(b, p)
        ok = bool(
            avt and (avt - base) == CA_VT_RVA and mi_vt and (mi_vt - base) == CA_MI_VT
        )
        if ok:
            walk_ok += 1
        atag = try_u32(b, primary + CA_TAG) if ok else None
        idx = ptr_to_idx.get(primary)
        if expect_idx is not None and idx == expect_idx:
            expect_in = True
        path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
        dest_in_70 = sorted(set(path.get("province_ids") or []) & set70)
        members.append(
            {
                "index": idx,
                "tag": atag,
                "ita": atag == tag if atag is not None else False,
                "walkback_ok": ok,
                "path_ids": path.get("province_ids") if ok else [],
                "path_n": path.get("n") if ok else 0,
                "dest_in_70": dest_in_70,
                "triangle": bool(ok and dest_in_70),
            }
        )
    return {
        "oi": oi,
        "ok": True,
        "inst_ok": inst_ok,
        "inst_vt_rva": hex(inst_vt_rva) if inst_vt_rva is not None else None,
        "arr98_size": arr98_size,
        "arr70_n": arr70_n,
        "u32s_head": u32s_head,
        "og50_size": (arr50 or {}).get("size") or 0,
        "walk_ok": walk_ok,
        "expect_idx": expect_idx,
        "expect_in_og50": expect_in,
        "members": members,
        "set70": set70,
        "triangle_n": sum(1 for m in members if m.get("triangle")),
        "ita_n": sum(1 for m in members if m.get("ita")),
    }


def dig_ref70(b, base):
    """OG481 Instant+0x70 only (for cross); no full member rollup."""
    try:
        hdr = resolve_handle(b, TYPE_OG, REF_OI, base)
    except Exception:
        return set(), {"ok": False}
    if not hdr:
        return set(), {"ok": False}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    if not ptrs:
        return set(), {"ok": False}
    inst = ptrs[0]
    vt = try_u64(b, inst)
    if not vt or (vt - base) != INST_VT:
        return set(), {"ok": False, "inst_ok": False}
    a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
    if not a70 or a70.get("in_image_sentinel"):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    u32s = a70.get("u32s") or []
    if not u32s or not all(looks_like_province(v) for v in u32s):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    return set(u32s), {"ok": True, "inst_ok": True, "arr70_n": len(u32s)}


def patch_docs(meta, result, digs_pub, cross, ref_meta):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hx `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2hw `PATH_OUTLIER_COVER_WIDEN_HIT`",
        "2hx `HIBAND_OG962_976_DIG_HIT`",
        "2hx `HIBAND_OG962_976_DIG_PARTIAL`",
        "2hx `HIBAND_OG962_976_DIG_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = ", ".join(
        f"oi{d['oi']} size={d.get('og50_size')} walk={d.get('walk_ok')} "
        f"arr70={d.get('arr70_n')} expect_in={d.get('expect_in_og50')} tri={d.get('triangle_n')}"
        for d in digs_pub
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hx hi-band "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hx** | `{result}` | hi-band OG962/976 dig Inst70+OG50+PATH | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hx** |" in t:
        t = re.sub(r"^\| \*\*2hx\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2hw** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hw** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hx hi-band OG962/976 dig:** result=`{result}` · {brief} · "
        f"cross70_n={cross.get('shared_n')} shared={cross.get('shared_head')} · "
        f"ref481_arr70={ref_meta.get('arr70_n')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2hx hi-band OG962/976 dig:**" in t:
        t = re.sub(r"^\*\*2hx hi-band OG962/976 dig:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2hw path∉Inst70 + cover widen:**" in t:
        idx = t.find("**2hw path∉Inst70 + cover widen:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hw · path∉Inst70 + cover widen · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hx · hi-band OG962/976 dig · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hw — checklist polish (CLOSED)",
        "## Phase 2gj … 2hx — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hx | hi-band OG962/976 dig Inst70+OG50+PATH | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hx |" in t2:
        t2 = re.sub(r"^\| 2hx \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2hw |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hw |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hw — path∉Inst70 + cover widen. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hx — hi-band OG962/976 dig. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hx — hi-band OG962/976 dig\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Constants:** INST_VT=0x2A02558 · OG+0x50 name STUBBED\n\n"
            f"**Ref OG{REF_OI} Inst70:** {json.dumps(ref_meta, ensure_ascii=False)}\n\n"
            f"**Digs:** {json.dumps(digs_pub, ensure_ascii=False)}\n\n"
            f"**Cross Inst70 ∩ OG481:** {json.dumps(cross, ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Cover_only armies live in hi-band OGs that may share Instant+0x70 "
            f"dests with OG481. Field name STUBBED. No invent. No Post / 463 Inst70 re-poll.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hx · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hx",
            "result": "NO_LIVE_PROCESS",
            "allow_post": False,
            "next_shortest_blocker": "NON-Post: restore live; still NO ALLOW_POST",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    b = Backend()
    base = b.image_base
    tag = player_tag(b, base)
    meta = live_meta(b, base, pid, tag)
    ptr_to_idx = build_ptr_index(b, base)

    ref70, ref_meta = dig_ref70(b, base)
    digs = [dig_oi(b, base, tag, oi, ptr_to_idx) for oi in FOCUS_OIS]

    digs_pub = []
    for d in digs:
        pub = {k: v for k, v in d.items() if k != "set70"}
        digs_pub.append(pub)

    cross_rows = []
    for d in digs:
        s70 = d.get("set70") or set()
        shared = sorted(s70 & ref70)
        cross_rows.append(
            {
                "oi": d["oi"],
                "shared_n": len(shared),
                "shared_head": shared[:12],
                "only_hiband_n": len(s70 - ref70),
                "only_481_n": len(ref70 - s70),
            }
        )
    cross = {
        "shared_n": sum(r["shared_n"] for r in cross_rows),
        "shared_head": sorted({p for r in cross_rows for p in r["shared_head"]})[:16],
        "per_oi": cross_rows,
    }

    dig_ok_n = sum(1 for d in digs if d.get("ok"))
    inst_ok_n = sum(1 for d in digs if d.get("inst_ok"))
    expect_n = sum(1 for d in digs if d.get("expect_in_og50"))
    walk_n = sum(d.get("walk_ok") or 0 for d in digs)
    tri_n = sum(d.get("triangle_n") or 0 for d in digs)
    shared_any = cross["shared_n"] > 0
    path_mem_n = sum(
        1
        for d in digs
        for m in (d.get("members") or [])
        if (m.get("path_n") or 0) > 0
    )

    # OG50 membership + expect army presence is the primary hit; Instant may be
    # non-COrderInstance / empty on hi-band OGs (document inst_vt_rva honestly).
    if dig_ok_n >= 2 and expect_n >= 2 and walk_n >= 2:
        result = "HIBAND_OG962_976_DIG_HIT"
    elif dig_ok_n >= 1 and (expect_n >= 1 or walk_n >= 1 or inst_ok_n >= 1 or tri_n or shared_any):
        result = "HIBAND_OG962_976_DIG_PARTIAL"
    else:
        result = "HIBAND_OG962_976_DIG_EMPTY"
    ok_n = dig_ok_n  # keep summary field meaning = digs resolved

    report = {
        "phase": "2hx",
        "result": result,
        "allow_post": False,
        "live": meta,
        "ref481": ref_meta,
        "digs": digs_pub,
        "cross": cross,
        "sha_base": SHA_BASE,
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "speed write",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 long poll",
            "endless Instant map re-poll",
            "463 Inst70 oi1..511 re-poll",
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hx hi-band OG962/976 dig); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "semantics": (
            "hi-band OG962/976 Inst70+OG50+PATH; cross∩OG481 Inst70; "
            "OG50 name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hx",
                "result": result,
                "allow_post": False,
                "ok_n": ok_n,
                "inst_ok_n": inst_ok_n,
                "walk_n": walk_n,
                "path_mem_n": path_mem_n,
                "expect_in_n": expect_n,
                "triangle_n": tri_n,
                "cross_shared_n": cross["shared_n"],
                "cross_shared_head": cross["shared_head"],
                "digs_brief": [
                    {
                        "oi": d["oi"],
                        "inst_ok": d.get("inst_ok"),
                        "og50_size": d.get("og50_size"),
                        "walk_ok": d.get("walk_ok"),
                        "arr70_n": d.get("arr70_n"),
                        "expect_idx": d.get("expect_idx"),
                        "expect_in_og50": d.get("expect_in_og50"),
                        "triangle_n": d.get("triangle_n"),
                        "ita_n": d.get("ita_n"),
                        "members_path": [
                            {
                                "index": m.get("index"),
                                "path_ids": m.get("path_ids"),
                                "dest_in_70": m.get("dest_in_70"),
                                "triangle": m.get("triangle"),
                            }
                            for m in (d.get("members") or [])
                            if (m.get("path_n") or 0) > 0 or m.get("triangle")
                        ],
                    }
                    for d in digs_pub
                ],
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "drain": meta.get("drain"),
                    "exec": meta.get("exec"),
                    "allow_post": False,
                },
                "sha_base": SHA_BASE,
                "next_shortest_blocker": report["next_shortest_blocker"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        patch_docs(meta, result, digs_pub, cross, ref_meta)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hx",
                "result": result,
                "allow_post": False,
                "live": meta,
                "ref481": ref_meta,
                "ok_n": ok_n,
                "inst_ok_n": inst_ok_n,
                "walk_n": walk_n,
                "path_mem_n": path_mem_n,
                "expect_in_n": expect_n,
                "triangle_n": tri_n,
                "cross": cross,
                "digs_brief": [
                    {
                        "oi": d["oi"],
                        "ok": d.get("ok"),
                        "inst_ok": d.get("inst_ok"),
                        "og50_size": d.get("og50_size"),
                        "walk_ok": d.get("walk_ok"),
                        "arr70_n": d.get("arr70_n"),
                        "u32s_head": d.get("u32s_head"),
                        "expect_idx": d.get("expect_idx"),
                        "expect_in_og50": d.get("expect_in_og50"),
                        "triangle_n": d.get("triangle_n"),
                        "ita_n": d.get("ita_n"),
                        "members": d.get("members"),
                    }
                    for d in digs_pub
                ],
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
