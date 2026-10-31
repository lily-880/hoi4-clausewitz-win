#!/usr/bin/env python3
"""Phase 2hu: PATH army × OG+0x50 membership × Instant+0x70 covering-oi triangle (RO).

Closes agent perception: army ∈ OG(oi) via +0x50≡CArmy+0xB8 AND path dest ∈
Instant+0x70(oi). Corrected INST_VT=0x2A02558. Field name at OG+0x50 STUBBED
(no invent). One-shot; no Post; never 5x; no speed write; no midflight;
no Assign oi≠0; no endless Instant poll.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hu_path_og50_inst70_triangle.json"
SUMMARY = ROOT / "reports" / "phase2hu_summary.json"
DOC = ROOT / "docs" / "PHASE2HU_PATH_OG50_INST70_TRIANGLE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
OI_LO, OI_HI = 1, 511
ARMY_LO, ARMY_HI = 1, 2000
SHA_BASE = "b4fe74e"


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
            "ITA PATH×OG+0x50×Inst70 triangle (INST_VT corrected; "
            "no Post, no midflight, no oi≠0, no endless Instant poll; OG50 name STUBBED)"
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


def read_cpdx_ptrs(b, base, arr_addr, max_n=32):
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


def scan_ita_paths(b, base, tag):
    rows = []
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
        if try_u32(b, army + CA_TAG) != tag:
            continue
        mi = army + CA_MI_OFF
        mi_vt = try_u64(b, mi)
        mi_ok = bool(mi_vt and (mi_vt - base) == CA_MI_VT)
        p = path60(b, base, army, tag)
        if p["n"] <= 0:
            continue
        rows.append(
            {
                "index": idx,
                "army": hex(army),
                "mi": hex(mi),
                "mi_ok": mi_ok,
                "path_ids": p["province_ids"],
                "path_n": p["n"],
            }
        )
    return rows


def build_prov_to_ois(b, base):
    """oi1..511 Instant+0x70 → prov→[oi]."""
    prov_to_ois = defaultdict(list)
    oi_inst_ok = 0
    oi_70_shaped = 0
    oi_70 = {}
    for oi in range(OI_LO, OI_HI + 1):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        if not hdr:
            continue
        og = hdr + 0x10
        arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
        ptrs = (arr98 or {}).get("ptrs") or []
        if not ptrs:
            continue
        inst = ptrs[0]
        vt = try_u64(b, inst)
        if not vt or (vt - base) != INST_VT:
            continue
        oi_inst_ok += 1
        a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
        if not a70 or a70.get("in_image_sentinel"):
            continue
        u32s = a70.get("u32s") or []
        if not u32s or not all(looks_like_province(v) for v in u32s):
            continue
        oi_70_shaped += 1
        oi_70[oi] = set(u32s)
        for pid in u32s:
            prov_to_ois[pid].append(oi)
    return {
        "oi_inst_ok": oi_inst_ok,
        "oi_70_shaped": oi_70_shaped,
        "prov_to_ois": prov_to_ois,
        "oi_70": oi_70,
    }


def og50_member_mis(b, base, oi):
    """Return set of MI addrs (and walkback army addrs) in OG+0x50."""
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        return {"ok": False, "mi_set": set(), "army_set": set(), "size": 0, "walk_ok": 0}
    if not hdr:
        return {"ok": False, "mi_set": set(), "army_set": set(), "size": 0, "walk_ok": 0}
    og = hdr + 0x10
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
    if not arr50 or arr50.get("in_image_sentinel"):
        return {
            "ok": False,
            "mi_set": set(),
            "army_set": set(),
            "size": (arr50 or {}).get("size") or 0,
            "walk_ok": 0,
        }
    mi_set = set()
    army_set = set()
    walk_ok = 0
    for p in arr50.get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        mi_set.add(p)
        primary = p - CA_MI_OFF
        vt = try_u64(b, primary)
        mi_vt = try_u64(b, p)
        if vt and (vt - base) == CA_VT_RVA and mi_vt and (mi_vt - base) == CA_MI_VT:
            army_set.add(primary)
            walk_ok += 1
    return {
        "ok": True,
        "mi_set": mi_set,
        "army_set": army_set,
        "size": arr50.get("size") or 0,
        "walk_ok": walk_ok,
    }


def triangle(b, base, path_rows, maps):
    prov_to_ois = maps["prov_to_ois"]
    # candidate ois = union of covering ois for all path dests
    cand_ois = sorted({oi for row in path_rows for pid in row["path_ids"] for oi in (prov_to_ois.get(pid) or [])})
    og50_cache = {}
    for oi in cand_ois:
        og50_cache[oi] = og50_member_mis(b, base, oi)

    army_hits = []
    triangle_n = 0
    member_only_n = 0
    cover_only_n = 0
    for row in path_rows:
        army = int(row["army"], 16)
        mi = int(row["mi"], 16)
        covered = {}
        for pid in row["path_ids"]:
            ois = prov_to_ois.get(pid) or []
            if ois:
                covered[str(pid)] = ois[:12]
        cover_ois = sorted({oi for ois in covered.values() for oi in ois})
        member_ois = []
        for oi in cand_ois:
            info = og50_cache.get(oi) or {}
            if army in (info.get("army_set") or set()) or mi in (info.get("mi_set") or set()):
                member_ois.append(oi)
        # triangle: same oi in member_ois and cover_ois
        tri = sorted(set(member_ois) & set(cover_ois))
        if tri:
            triangle_n += 1
        elif member_ois:
            member_only_n += 1
        elif cover_ois:
            cover_only_n += 1
        army_hits.append(
            {
                "index": row["index"],
                "path_ids": row["path_ids"],
                "mi_ok": row["mi_ok"],
                "dest_cover_ois": covered,
                "cover_ois": cover_ois,
                "member_ois": member_ois,
                "triangle_ois": tri,
                "triangle": bool(tri),
            }
        )
    og50_pub = {
        str(oi): {
            "size": v["size"],
            "walk_ok": v["walk_ok"],
            "ok": v["ok"],
        }
        for oi, v in og50_cache.items()
    }
    return {
        "cand_ois": cand_ois,
        "og50": og50_pub,
        "army_path_n": len(path_rows),
        "triangle_n": triangle_n,
        "member_only_n": member_only_n,
        "cover_only_n": cover_only_n,
        "army_hits": army_hits,
    }


def patch_docs(meta, result, maps, cross):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hu `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2ht `MULTI_OI_INST70_PATH_HIT`",
        "2hu `PATH_OG50_INST70_TRIANGLE_HIT`",
        "2hu `PATH_OG50_INST70_TRIANGLE_PARTIAL`",
        "2hu `PATH_OG50_INST70_TRIANGLE_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hu triangle "
        f"tri={cross.get('triangle_n')}/{cross.get('army_path_n')} "
        f"cand_ois={cross.get('cand_ois')} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hu** | `{result}` | PATH×OG+0x50×Inst70 triangle (corrected INST_VT) | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hu** |" not in t and "| **2ht** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ht** |"):
                out.append(row)
        t = "".join(out)
    hits = "; ".join(
        f"idx={a['index']} tri={a['triangle_ois']} cover={a['cover_ois']} mem={a['member_ois']}"
        for a in (cross.get("army_hits") or [])
        if a.get("triangle")
    )[:220] or "none"
    note = (
        f"**2hu PATH×OG50×Inst70 triangle:** result=`{result}` · "
        f"tri={cross.get('triangle_n')}/{cross.get('army_path_n')} · "
        f"member_only={cross.get('member_only_n')} cover_only={cross.get('cover_only_n')} · "
        f"cand_ois={cross.get('cand_ois')} · "
        f"inst_ok={maps.get('oi_inst_ok')} shaped70={maps.get('oi_70_shaped')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False. hits=[{hits}]\n"
    )
    if "**2hu PATH×OG50×Inst70 triangle:**" not in t and "**2ht multi-oi Inst70×PATH:**" in t:
        idx = t.find("**2ht multi-oi Inst70×PATH:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ht · multi-oi Inst70×PATH · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hu · PATH×OG50×Inst70 triangle · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ht — checklist polish (CLOSED)",
        "## Phase 2gj … 2hu — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hu | PATH×OG+0x50×Inst70 triangle | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hu |" not in t2 and "| 2ht |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ht |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ht — multi-oi Inst70×PATH. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hu — PATH×OG50×Inst70 triangle. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hu — PATH × OG+0x50 × Instant+0x70 triangle\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Constants:** INST_VT=0x2A02558 · OG+0x50 ≡ CArmy+0xB8 MI (name STUBBED) · "
            f"CA_MI_VT=0x29D6FB8\n\n"
            f"**OG Instant scan:** inst_ok={maps.get('oi_inst_ok')} · "
            f"shaped70={maps.get('oi_70_shaped')}\n\n"
            f"**Candidate covering ois:** {cross.get('cand_ois')}\n\n"
            f"**OG+0x50 (candidates):** {json.dumps(cross.get('og50'), ensure_ascii=False)}\n\n"
            f"**Triangle:** {cross.get('triangle_n')}/{cross.get('army_path_n')} · "
            f"member_only={cross.get('member_only_n')} · cover_only={cross.get('cover_only_n')}\n\n"
            f"**Army hits:** {json.dumps(cross.get('army_hits'), ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Perception closure: army ∈ OG(oi) via +0x50 walkback AND path dest ∈ "
            f"Instant+0x70(oi). Field name STUBBED. No invent. No Post / midflight / oi≠0 / "
            f"endless Instant poll.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hu · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hu",
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

    path_rows = scan_ita_paths(b, base, tag)
    maps = build_prov_to_ois(b, base)
    cross = triangle(b, base, path_rows, maps)

    tri = cross.get("triangle_n") or 0
    path_n = cross.get("army_path_n") or 0
    if tri >= 2 or (tri >= 1 and path_n <= 2):
        result = "PATH_OG50_INST70_TRIANGLE_HIT"
    elif tri >= 1 or (cross.get("member_only_n") or 0) >= 1:
        result = "PATH_OG50_INST70_TRIANGLE_PARTIAL"
    else:
        result = "PATH_OG50_INST70_TRIANGLE_EMPTY"

    # drop large set maps from report
    maps_pub = {
        "oi_inst_ok": maps["oi_inst_ok"],
        "oi_70_shaped": maps["oi_70_shaped"],
    }

    report = {
        "phase": "2hu",
        "result": result,
        "allow_post": False,
        "live": meta,
        "maps": maps_pub,
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
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hu PATH×OG50×Inst70 triangle); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "semantics": (
            "PATH dest∈Inst70(oi) ∧ army∈OG+0x50(oi); OG50 name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hu",
                "result": result,
                "allow_post": False,
                "triangle_n": tri,
                "army_path_n": path_n,
                "member_only_n": cross.get("member_only_n"),
                "cover_only_n": cross.get("cover_only_n"),
                "cand_ois": cross.get("cand_ois"),
                "oi_inst_ok": maps["oi_inst_ok"],
                "oi_70_shaped": maps["oi_70_shaped"],
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
        patch_docs(meta, result, maps_pub, cross)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hu",
                "result": result,
                "allow_post": False,
                "live": meta,
                "triangle_n": tri,
                "army_path_n": path_n,
                "member_only_n": cross.get("member_only_n"),
                "cover_only_n": cross.get("cover_only_n"),
                "cand_ois": cross.get("cand_ois"),
                "og50": cross.get("og50"),
                "army_hits": cross.get("army_hits"),
                "oi_inst_ok": maps["oi_inst_ok"],
                "oi_70_shaped": maps["oi_70_shaped"],
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
