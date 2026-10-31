#!/usr/bin/env python3
"""Phase 2hw: path∉Inst70 dest covering-oi + cover_only OG50 reverse widen (RO).

Explains 2hv gaps: (1) which oi Instant+0x70 contains path-outlier dests
(e.g. 3938) while army remains OG481 member; (2) widen cover_only reverse
membership scan oi512..1023 (oi1..511 was empty for 1046). Corrected
INST_VT=0x2A02558. OG+0x50 name STUBBED. One-shot; no Post; never 5x;
no speed write; no midflight; no Assign oi≠0; no endless Instant poll.
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

OUT = ROOT / "reports" / "phase2hw_path_outlier_cover_widen.json"
SUMMARY = ROOT / "reports" / "phase2hw_summary.json"
DOC = ROOT / "docs" / "PHASE2HW_PATH_OUTLIER_COVER_WIDEN.md"

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
WIDEN_LO, WIDEN_HI = 512, 1023
ARMY_LO, ARMY_HI = 1, 2000
SHA_BASE = "aef0b09"
SEED_OUTLIERS = (3938,)  # from 2hv; live scan may add more


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
            "ITA path∉Inst70 covering-oi + cover_only reverse widen "
            f"oi{WIDEN_LO}..{WIDEN_HI} (INST_VT corrected; no Post; OG50 name STUBBED)"
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


def dig_focus70(b, base):
    hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    if not hdr:
        return None, set(), set(), set()
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    set70 = set()
    inst_ok = False
    if ptrs:
        inst = ptrs[0]
        vt = try_u64(b, inst)
        inst_ok = bool(vt and (vt - base) == INST_VT)
        if inst_ok:
            a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
            if a70 and not a70.get("in_image_sentinel"):
                u32s = a70.get("u32s") or []
                if u32s and all(looks_like_province(v) for v in u32s):
                    set70 = set(u32s)
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
    member_armies = set()
    member_mis = set()
    for p in (arr50 or {}).get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        member_mis.add(p)
        primary = p - CA_MI_OFF
        avt = try_u64(b, primary)
        mi_vt = try_u64(b, p)
        if avt and (avt - base) == CA_VT_RVA and mi_vt and (mi_vt - base) == CA_MI_VT:
            member_armies.add(primary)
    return {
        "inst_ok": inst_ok,
        "arr70_n": len(set70),
        "og50_size": (arr50 or {}).get("size") or 0,
        "member_n": len(member_armies),
    }, set70, member_armies, member_mis


def scan_ita(b, base, tag, set70, member_armies):
    path_rows = []
    outliers = []
    cover_only = []
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
        if try_u32(b, army + CA_TAG) != tag:
            continue
        p = path60(b, base, army, tag)
        if p["n"] <= 0:
            continue
        dests = p["province_ids"]
        in70 = sorted(set(dests) & set70)
        out70 = sorted(set(dests) - set70)
        row = {
            "index": idx,
            "army": hex(army),
            "mi": hex(army + CA_MI_OFF),
            "path_ids": dests,
            "dest_in_70": in70,
            "dest_out_70": out70,
            "in_og481": army in member_armies,
        }
        path_rows.append(row)
        if out70 and army in member_armies:
            outliers.append(row)
        if in70 and army not in member_armies:
            cover_only.append(row)
    return path_rows, outliers, cover_only, ptr_to_idx


def scan_prov_ois(b, base, targets: set, oi_lo, oi_hi):
    """Map province → [oi] for Instant+0x70 containing any target."""
    prov_to_ois = defaultdict(list)
    oi_inst_ok = 0
    oi_hit_rows = []
    for oi in range(oi_lo, oi_hi + 1):
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
        hit = sorted(set(u32s) & targets)
        if not hit:
            continue
        for pid in hit:
            prov_to_ois[pid].append(oi)
        oi_hit_rows.append({"oi": oi, "arr70_n": len(u32s), "targets_hit": hit, "band": "lo" if oi <= OI_HI else "hi"})
    return {
        "oi_lo": oi_lo,
        "oi_hi": oi_hi,
        "oi_inst_ok": oi_inst_ok,
        "prov_to_ois": {str(k): v for k, v in sorted(prov_to_ois.items())},
        "oi_hit_rows": oi_hit_rows[:32],
        "_raw": prov_to_ois,
    }


def reverse_widen(b, base, cover_only, oi_lo, oi_hi):
    if not cover_only:
        return {"cover_only_n": 0, "reverse_hit_n": 0, "rows": [], "oi_band": [oi_lo, oi_hi]}
    mi_targets = {int(r["mi"], 16): r["index"] for r in cover_only}
    army_targets = {int(r["army"], 16): r["index"] for r in cover_only}
    found = defaultdict(list)
    for oi in range(oi_lo, oi_hi + 1):
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
    rows = []
    hit_n = 0
    for r in cover_only:
        ois = sorted(set(found.get(r["index"]) or []))
        if ois:
            hit_n += 1
        rows.append(
            {
                "index": r["index"],
                "path_ids": r["path_ids"],
                "dest_in_70": r["dest_in_70"],
                "member_ois_widen": ois,
                "reverse_hit": bool(ois),
            }
        )
    return {
        "cover_only_n": len(cover_only),
        "reverse_hit_n": hit_n,
        "rows": rows,
        "oi_band": [oi_lo, oi_hi],
    }


def patch_docs(meta, result, focus_meta, outlier_map, widen, outliers, cover_only):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hw `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2hv `OG481_MEMBER_ROLLUP_COVER_REVERSE_HIT`",
        "2hw `PATH_OUTLIER_COVER_WIDEN_HIT`",
        "2hw `PATH_OUTLIER_COVER_WIDEN_PARTIAL`",
        "2hw `PATH_OUTLIER_COVER_WIDEN_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    t = re.sub(
        r"\| `INST7088` \| order/front maps \| Instance`\+0x70`/`\+0x88` — [^\n]*\|\n",
        f"| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` — 2hw outlier "
        f"prov→oi={outlier_map.get('prov_to_ois')} widen_rev="
        f"{widen.get('reverse_hit_n')}/{widen.get('cover_only_n')} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hw** | `{result}` | path∉Inst70 covering-oi + cover_only reverse widen | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hw** |" not in t and "| **2hv** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hv** |"):
                out.append(row)
        t = "".join(out)
    ob = "; ".join(
        f"idx={o['index']} out={o['dest_out_70']}→{outlier_map.get('prov_to_ois')}"
        for o in outliers
    )[:200] or "none"
    wb = "; ".join(
        f"idx={r['index']}→{r['member_ois_widen']}" for r in (widen.get("rows") or [])
    )[:160] or "none"
    note = (
        f"**2hw path∉Inst70 + cover widen:** result=`{result}` · "
        f"outliers={len(outliers)} cover_only={len(cover_only)} · "
        f"prov→oi={outlier_map.get('prov_to_ois')} · "
        f"widen_rev={widen.get('reverse_hit_n')}/{widen.get('cover_only_n')} "
        f"band={widen.get('oi_band')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False. "
        f"out=[{ob}] widen=[{wb}]\n"
    )
    if "**2hw path∉Inst70 + cover widen:**" not in t and "**2hv OG481 member rollup + cover reverse:**" in t:
        idx = t.find("**2hv OG481 member rollup + cover reverse:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hv · OG481 member rollup + cover reverse · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hw · path∉Inst70 + cover widen · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hv — checklist polish (CLOSED)",
        "## Phase 2gj … 2hw — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hw | path∉Inst70 covering-oi + cover_only reverse widen | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hw |" not in t2 and "| 2hv |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hv |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hv — OG481 member rollup + cover reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hw — path∉Inst70 + cover widen. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hw — path∉Inst70 covering-oi + cover_only reverse widen\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Constants:** INST_VT=0x2A02558 · OG+0x50 name STUBBED\n\n"
            f"**Focus OG{FOCUS_OI}:** {json.dumps(focus_meta, ensure_ascii=False)}\n\n"
            f"**Outlier armies (∈OG481 ∧ path∉Inst70):** {json.dumps(outliers, ensure_ascii=False)}\n\n"
            f"**Outlier dest → covering oi (Inst70 oi{OI_LO}..{OI_HI}):** "
            f"{json.dumps(outlier_map.get('prov_to_ois'), ensure_ascii=False)}\n\n"
            f"**oi_hit_rows:** {json.dumps(outlier_map.get('oi_hit_rows'), ensure_ascii=False)}\n\n"
            f"**Cover_only reverse widen oi{WIDEN_LO}..{WIDEN_HI}:** "
            f"{json.dumps(widen, ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Path dest outside focus Instant+0x70 may still appear in other orders' "
            f"+0x70; cover_only may live in oi>511. Field name STUBBED. No invent. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hw · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hw",
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

    packed = dig_focus70(b, base)
    if packed[0] is None:
        focus_meta, set70, member_armies, member_mis = {}, set(), set(), set()
    else:
        focus_meta, set70, member_armies, member_mis = packed

    path_rows, outliers, cover_only, _ptr = scan_ita(b, base, tag, set70, member_armies)

    targets = set(SEED_OUTLIERS)
    for o in outliers:
        targets.update(o.get("dest_out_70") or [])
    # also include seed even if no live outlier (documents absence)
    outlier_map = scan_prov_ois(b, base, targets, OI_LO, OI_HI)
    # strip raw
    outlier_pub = {k: v for k, v in outlier_map.items() if not k.startswith("_")}

    # annotate outliers with covering ois
    raw = outlier_map.get("_raw") or {}
    for o in outliers:
        o["out_cover_ois"] = {
            str(pid): (raw.get(pid) or [])[:12] for pid in (o.get("dest_out_70") or [])
        }

    widen = reverse_widen(b, base, cover_only, WIDEN_LO, WIDEN_HI)

    outlier_covered_n = sum(
        1
        for o in outliers
        if any((raw.get(pid) or []) for pid in (o.get("dest_out_70") or []))
    )
    seed_hit = any((raw.get(pid) or []) for pid in SEED_OUTLIERS)

    if outlier_covered_n >= 1 or widen.get("reverse_hit_n", 0) >= 1 or seed_hit:
        result = "PATH_OUTLIER_COVER_WIDEN_HIT"
    elif outliers or cover_only or focus_meta.get("inst_ok"):
        # documented honest empty on widen / no covering oi for outliers
        result = "PATH_OUTLIER_COVER_WIDEN_PARTIAL"
    else:
        result = "PATH_OUTLIER_COVER_WIDEN_EMPTY"

    report = {
        "phase": "2hw",
        "result": result,
        "allow_post": False,
        "live": meta,
        "focus": focus_meta,
        "targets": sorted(targets),
        "path_n": len(path_rows),
        "outliers": outliers,
        "outlier_map": outlier_pub,
        "cover_only": [
            {
                "index": r["index"],
                "path_ids": r["path_ids"],
                "dest_in_70": r["dest_in_70"],
            }
            for r in cover_only
        ],
        "widen_reverse": widen,
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
            "plan-dense Assign oi≠0 (2hw path∉Inst70 + cover widen); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "semantics": (
            "outlier dest covering Instant+0x70 oi + cover_only OG50 reverse "
            f"oi{WIDEN_LO}..{WIDEN_HI}; OG50 name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hw",
                "result": result,
                "allow_post": False,
                "targets": sorted(targets),
                "outlier_n": len(outliers),
                "outlier_covered_n": outlier_covered_n,
                "prov_to_ois": outlier_pub.get("prov_to_ois"),
                "cover_only_n": len(cover_only),
                "widen_reverse_hit_n": widen.get("reverse_hit_n"),
                "widen_rows": widen.get("rows"),
                "outliers_brief": [
                    {
                        "index": o["index"],
                        "dest_out_70": o["dest_out_70"],
                        "out_cover_ois": o.get("out_cover_ois"),
                    }
                    for o in outliers
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
        patch_docs(meta, result, focus_meta, outlier_pub, widen, outliers, cover_only)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hw",
                "result": result,
                "allow_post": False,
                "live": meta,
                "focus": focus_meta,
                "targets": sorted(targets),
                "outlier_n": len(outliers),
                "outlier_covered_n": outlier_covered_n,
                "prov_to_ois": outlier_pub.get("prov_to_ois"),
                "oi_hit_rows": outlier_pub.get("oi_hit_rows"),
                "outliers": outliers,
                "cover_only_n": len(cover_only),
                "widen_reverse": widen,
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
