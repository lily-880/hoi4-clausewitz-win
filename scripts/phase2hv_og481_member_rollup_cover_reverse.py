#!/usr/bin/env python3
"""Phase 2hv: OG481 member PATH/Inst70 rollup + cover_only reverse OG+0x50 (RO).

Catalog all OG+0x50 members of oi=481 (path ∩ Instant+0x70) and reverse-map
cover_only path armies (dest∈Inst70(481) but not OG50 member) to their member
ois. Corrected INST_VT=0x2A02558. OG+0x50 field name STUBBED. One-shot; no Post;
never 5x; no speed write; no midflight; no Assign oi≠0; no endless Instant poll.
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

OUT = ROOT / "reports" / "phase2hv_og481_member_rollup_cover_reverse.json"
SUMMARY = ROOT / "reports" / "phase2hv_summary.json"
DOC = ROOT / "docs" / "PHASE2HV_OG481_MEMBER_ROLLUP_COVER_REVERSE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
FOCUS_OI = 481
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
OI_LO, OI_HI = 1, 511
ARMY_LO, ARMY_HI = 1, 2000
SHA_BASE = "80e4ac4"


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
            f"ITA OG{FOCUS_OI} member rollup + cover_only reverse "
            "(INST_VT corrected; no Post, no midflight, no oi≠0; OG50 name STUBBED)"
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


def build_army_index_maps(b, base, tag):
    """ptr→index and mi→index for ITA (and all CA) in handle range."""
    ptr_to_idx = {}
    mi_to_idx = {}
    ita_path = []
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
        mi_to_idx[army + CA_MI_OFF] = idx
        atag = try_u32(b, army + CA_TAG)
        if atag != tag:
            continue
        p = path60(b, base, army, tag)
        if p["n"] > 0:
            ita_path.append(
                {
                    "index": idx,
                    "army": hex(army),
                    "mi": hex(army + CA_MI_OFF),
                    "path_ids": p["province_ids"],
                    "path_n": p["n"],
                }
            )
    return ptr_to_idx, mi_to_idx, ita_path


def dig_focus(b, base, tag, ptr_to_idx, mi_to_idx):
    hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    if not hdr:
        return None
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    if not ptrs:
        return None
    inst = ptrs[0]
    vt = try_u64(b, inst)
    inst_ok = bool(vt and (vt - base) == INST_VT)
    set70 = set()
    arr70_n = 0
    if inst_ok:
        a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
        if a70 and not a70.get("in_image_sentinel"):
            u32s = a70.get("u32s") or []
            if u32s and all(looks_like_province(v) for v in u32s):
                set70 = set(u32s)
                arr70_n = len(u32s)

    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
    members = []
    walk_ok = 0
    for p in (arr50 or {}).get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        primary = p - CA_MI_OFF
        avt = try_u64(b, primary)
        mi_vt = try_u64(b, p)
        ok = bool(
            avt
            and (avt - base) == CA_VT_RVA
            and mi_vt
            and (mi_vt - base) == CA_MI_VT
        )
        if ok:
            walk_ok += 1
        atag = try_u32(b, primary + CA_TAG) if ok else None
        idx = ptr_to_idx.get(primary) or mi_to_idx.get(p)
        path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
        dest_in_70 = sorted(set(path.get("province_ids") or []) & set70)
        members.append(
            {
                "index": idx,
                "army": hex(primary) if ok else None,
                "mi": hex(p),
                "walkback_ok": ok,
                "tag": atag,
                "ita": atag == tag if atag is not None else False,
                "path_ids": path.get("province_ids") if ok else [],
                "path_n": path.get("n") if ok else 0,
                "dest_in_70": dest_in_70,
                "triangle": bool(ok and dest_in_70),
            }
        )
    return {
        "oi": FOCUS_OI,
        "inst_ok": inst_ok,
        "arr70_n": arr70_n,
        "og50_size": (arr50 or {}).get("size") or 0,
        "walk_ok": walk_ok,
        "members": members,
        "set70": set70,
    }


def reverse_cover_only(b, base, ita_path, focus, ptr_to_idx):
    """Path armies with dest∈Inst70(focus) but not in OG50 members → find member_ois."""
    member_armies = set()
    for m in focus.get("members") or []:
        if m.get("army"):
            member_armies.add(int(m["army"], 16))
    set70 = focus.get("set70") or set()
    cover_only = []
    for row in ita_path:
        army = int(row["army"], 16)
        dests = set(row["path_ids"])
        in70 = sorted(dests & set70)
        if not in70:
            continue
        if army in member_armies:
            continue
        cover_only.append({**row, "dest_in_70": in70})

    # reverse: for each cover_only MI, scan oi1..511 OG+0x50
    mi_targets = {int(r["mi"], 16): r["index"] for r in cover_only}
    army_targets = {int(r["army"], 16): r["index"] for r in cover_only}
    found = defaultdict(list)  # index → [oi]
    oi_hits = {}
    if mi_targets:
        for oi in range(OI_LO, OI_HI + 1):
            try:
                hdr = resolve_handle(b, TYPE_OG, oi, base)
            except Exception:
                continue
            if not hdr:
                continue
            og = hdr + 0x10
            arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
            if not arr50 or arr50.get("in_image_sentinel"):
                continue
            for p in arr50.get("ptrs") or []:
                if p in mi_targets:
                    found[mi_targets[p]].append(oi)
                else:
                    primary = p - CA_MI_OFF
                    if primary in army_targets:
                        found[army_targets[primary]].append(oi)
            # early note size if any hit
            if any(oi in found[idx] for idx in found):
                oi_hits[oi] = arr50.get("size") or 0

    rows = []
    reverse_hit_n = 0
    for r in cover_only:
        ois = sorted(set(found.get(r["index"]) or []))
        if ois:
            reverse_hit_n += 1
        rows.append(
            {
                "index": r["index"],
                "path_ids": r["path_ids"],
                "dest_in_70": r["dest_in_70"],
                "member_ois": ois,
                "reverse_hit": bool(ois),
            }
        )
    return {
        "cover_only_n": len(cover_only),
        "reverse_hit_n": reverse_hit_n,
        "rows": rows,
    }


def patch_docs(meta, result, focus, rev, tri_n, ita_n):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hv `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2hu `PATH_OG50_INST70_TRIANGLE_HIT`",
        "2hv `OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT`",
        "2hv `OG481_MEMBER_ROLLUP_COVER_REVERSE_PARTIAL`",
        "2hv `OG481_MEMBER_ROLLUP_COVER_REVERSE_EMPTY`",
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
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hv OG{FOCUS_OI} "
        f"members={focus.get('og50_size')} walk={focus.get('walk_ok')} "
        f"tri_members={tri_n} cover_rev={rev.get('reverse_hit_n')}/{rev.get('cover_only_n')} "
        f"(name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hv** | `{result}` | OG{FOCUS_OI} member rollup + cover_only reverse | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hv** |" not in t and "| **2hu** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hu** |"):
                out.append(row)
        t = "".join(out)
    mem_brief = "; ".join(
        f"idx={m.get('index')} path={m.get('path_ids')} tri={m.get('triangle')}"
        for m in (focus.get("members") or [])
        if m.get("ita")
    )[:200] or "none"
    rev_brief = "; ".join(
        f"idx={r['index']}→ois={r['member_ois']}"
        for r in (rev.get("rows") or [])
    )[:160] or "none"
    note = (
        f"**2hv OG{FOCUS_OI} member rollup + cover reverse:** result=`{result}` · "
        f"og50={focus.get('og50_size')} walk={focus.get('walk_ok')} arr70={focus.get('arr70_n')} · "
        f"ita_tri_members={tri_n} ita_path={ita_n} · "
        f"cover_only={rev.get('cover_only_n')} reverse_hit={rev.get('reverse_hit_n')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False. "
        f"ita_mem=[{mem_brief}] cover_rev=[{rev_brief}]\n"
    )
    if f"**2hv OG{FOCUS_OI} member rollup + cover reverse:**" not in t and "**2hu PATH×OG50×Inst70 triangle:**" in t:
        idx = t.find("**2hu PATH×OG50×Inst70 triangle:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hu · PATH×OG50×Inst70 triangle · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hv · OG481 member rollup + cover reverse · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hu — checklist polish (CLOSED)",
        "## Phase 2gj … 2hv — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hv | OG{FOCUS_OI} member rollup + cover_only reverse | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hv |" not in t2 and "| 2hu |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hu |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hu — PATH×OG50×Inst70 triangle. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hv — OG481 member rollup + cover reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hv — OG{FOCUS_OI} member rollup + cover_only reverse\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Constants:** INST_VT=0x2A02558 · OG+0x50 ≡ CArmy+0xB8 (name STUBBED)\n\n"
            f"**OG{FOCUS_OI}:** size={focus.get('og50_size')} walk_ok={focus.get('walk_ok')} · "
            f"inst_ok={focus.get('inst_ok')} arr70_n={focus.get('arr70_n')}\n\n"
            f"**Members:** {json.dumps(focus.get('members'), ensure_ascii=False)}\n\n"
            f"**Cover_only reverse:** n={rev.get('cover_only_n')} hit={rev.get('reverse_hit_n')} · "
            f"{json.dumps(rev.get('rows'), ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Catalog OG members' PATH∩Inst70; reverse-map cover_only path armies "
            f"to their OG+0x50 ois. Field name STUBBED. No invent. No Post / midflight / oi≠0 / "
            f"endless Instant poll.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hv · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hv",
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

    ptr_to_idx, mi_to_idx, ita_path = build_army_index_maps(b, base, tag)
    focus = dig_focus(b, base, tag, ptr_to_idx, mi_to_idx)
    if not focus:
        result = "OG481_MEMBER_ROLLUP_COVER_REVERSE_EMPTY"
        report = {
            "phase": "2hv",
            "result": result,
            "allow_post": False,
            "live": meta,
            "error": "focus oi unresolved",
            "sha_base": SHA_BASE,
        }
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        SUMMARY.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1

    rev = reverse_cover_only(b, base, ita_path, focus, ptr_to_idx)
    # drop set70 from persisted focus (large)
    set70_n = len(focus.get("set70") or [])
    focus_pub = {k: v for k, v in focus.items() if k != "set70"}
    focus_pub["set70_n"] = set70_n

    ita_members = [m for m in focus["members"] if m.get("ita")]
    tri_n = sum(1 for m in ita_members if m.get("triangle"))
    path_mem_n = sum(1 for m in ita_members if (m.get("path_n") or 0) > 0)

    if tri_n >= 1 and (focus.get("walk_ok") or 0) >= 1:
        # rollup itself is a hit if we catalogued members with triangle; reverse optional
        if rev.get("cover_only_n", 0) == 0 or rev.get("reverse_hit_n", 0) >= 1 or rev.get("cover_only_n", 0) >= 1:
            result = "OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT"
        else:
            result = "OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT"
    elif (focus.get("walk_ok") or 0) >= 1:
        result = "OG481_MEMBER_ROLLUP_COVER_REVERSE_PARTIAL"
    else:
        result = "OG481_MEMBER_ROLLUP_COVER_REVERSE_EMPTY"

    report = {
        "phase": "2hv",
        "result": result,
        "allow_post": False,
        "live": meta,
        "focus": focus_pub,
        "ita_path_n": len(ita_path),
        "ita_member_n": len(ita_members),
        "ita_path_member_n": path_mem_n,
        "triangle_member_n": tri_n,
        "cover_reverse": rev,
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
            "plan-dense Assign oi≠0 (2hv OG481 member rollup + cover reverse); push when "
            "GitHub reachable; still NO ALLOW_POST"
        ),
        "semantics": (
            "OG481 member PATH∩Inst70 catalog + cover_only reverse oi; "
            "OG50 name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hv",
                "result": result,
                "allow_post": False,
                "og50_size": focus.get("og50_size"),
                "walk_ok": focus.get("walk_ok"),
                "arr70_n": focus.get("arr70_n"),
                "ita_member_n": len(ita_members),
                "triangle_member_n": tri_n,
                "cover_only_n": rev.get("cover_only_n"),
                "reverse_hit_n": rev.get("reverse_hit_n"),
                "cover_reverse_rows": rev.get("rows"),
                "ita_members_brief": [
                    {
                        "index": m.get("index"),
                        "path_ids": m.get("path_ids"),
                        "dest_in_70": m.get("dest_in_70"),
                        "triangle": m.get("triangle"),
                    }
                    for m in ita_members
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
        patch_docs(meta, result, focus_pub, rev, tri_n, len(ita_path))
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hv",
                "result": result,
                "allow_post": False,
                "live": meta,
                "og50_size": focus.get("og50_size"),
                "walk_ok": focus.get("walk_ok"),
                "arr70_n": focus.get("arr70_n"),
                "inst_ok": focus.get("inst_ok"),
                "ita_member_n": len(ita_members),
                "triangle_member_n": tri_n,
                "ita_members": [
                    {
                        "index": m.get("index"),
                        "tag": m.get("tag"),
                        "path_ids": m.get("path_ids"),
                        "dest_in_70": m.get("dest_in_70"),
                        "triangle": m.get("triangle"),
                    }
                    for m in ita_members
                ],
                "all_members_brief": [
                    {
                        "index": m.get("index"),
                        "tag": m.get("tag"),
                        "ita": m.get("ita"),
                        "path_n": m.get("path_n"),
                        "triangle": m.get("triangle"),
                    }
                    for m in focus["members"]
                ],
                "cover_reverse": rev,
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
