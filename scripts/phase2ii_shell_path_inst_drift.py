#!/usr/bin/env python3
"""Phase 2ii: shell-member PATH × 481 Inst70/ARR88 drift denser (RO).

Focused polish after 2ih triangle_481_n=0: for known shell member idxs
(481/575/962/976), re-read PATH@+0x60 and cross vs one Instant hub on
populated OG481 (INST_VT=0x2A02558 Inst70 + CP_VT=0x29EE248 arr88).
Documents path dest drift vs Instant coverage. No Instant on 575/962/976;
no Assign / midflight / Post; never 5x; no speed write; OG+0x50 name STUBBED.
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

OUT = ROOT / "reports" / "phase2ii_shell_path_inst_drift.json"
SUMMARY = ROOT / "reports" / "phase2ii_summary.json"
DOC = ROOT / "docs" / "PHASE2II_SHELL_PATH_INST_DRIFT.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
REF_OI = 481
CA_VT_RVA = 0x29D6D68
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
CP_VT = 0x29EE248
CP_ID = 0xA4
CP_VT_FALSE = 0x29D3C68
FOCUS_PROVS = (1176, 3938, 3816, 915, 875)
# frozen from 2ih HIT
SHELL_MEMBERS = {
    481: [461, 410, 455, 445, 382, 463],
    575: [2640, 1049, 2678, 2671],
    962: [2648, 2664, 2680, 2673, 2660, 2641, 2666, 2665, 2642, 2652, 2644, 2681, 2669, 2649, 2654, 2655],
    976: [2645, 2662, 2672, 2679, 2646, 2667, 2647, 2675, 2670, 2674, 1046, 2643, 2677, 2661, 2663, 2639, 2676],
}
KIND = {481: "focus", 575: "midband", 962: "hiband", 976: "hiband"}
SHA_BASE = "65798dd"


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
    clock_class = "RELOAD_OR_NEW_CAMPAIGN" if int(hours) < 48 else "CONTINUOUS"
    return {
        "pid": pid,
        "hours": hours,
        "year_at_0x478": year,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "clock_class": clock_class,
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": tag,
        "scenario": (
            "ITA shell-member PATH × 481 Inst70/ARR88 drift denser "
            "(Instant only on 481; no Post; OG50 name STUBBED)"
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


def read_cpdx_ptrs(b, base, arr_addr, max_n=64):
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


def dig_481_hub(b, base):
    try:
        hdr = resolve_handle(b, TYPE_OG, REF_OI, base)
    except Exception:
        return None, {"ok": False}
    if not hdr:
        return None, {"ok": False}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    if not ptrs:
        return None, {"ok": False, "reason": "no_inst"}
    inst = ptrs[0]
    vt = try_u64(b, inst)
    if not vt or (vt - base) != INST_VT:
        return None, {"ok": False, "inst_ok": False, "inst_vt": hex(vt - base) if vt else None}
    a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
    set70 = set()
    arr70_n = 0
    u32s_head = []
    if a70 and not a70.get("in_image_sentinel"):
        u32s = a70.get("u32s") or []
        if u32s and all(looks_like_province(v) for v in u32s):
            set70 = set(u32s)
            arr70_n = len(u32s)
            u32s_head = u32s[:12]
    a88 = read_cpdx_ptrs(b, base, inst + 0x88, 96)
    set88 = set()
    kinds = {"CProvince_correct": 0, "CProvince_false_vt": 0, "other": 0, "nullish": 0}
    ids_head = []
    arr88_size = (a88 or {}).get("size") or 0
    arr88_sentinel = bool(a88 and a88.get("in_image_sentinel"))
    if a88 and not arr88_sentinel:
        for p in a88.get("ptrs") or []:
            if not p or p < 0x10000:
                kinds["nullish"] += 1
                continue
            cvt = try_u64(b, p)
            if not cvt:
                kinds["nullish"] += 1
                continue
            rva = cvt - base
            if rva == CP_VT:
                kinds["CProvince_correct"] += 1
                pid = try_u32(b, p + CP_ID)
                if pid and looks_like_province(pid):
                    set88.add(pid)
                    if len(ids_head) < 16:
                        ids_head.append(pid)
            elif rva == CP_VT_FALSE:
                kinds["CProvince_false_vt"] += 1
            else:
                kinds["other"] += 1
    hub = {"set70": set70, "set88": set88}
    meta = {
        "ok": True,
        "inst_ok": True,
        "inst_vt_rva": "0x2a02558",
        "arr70_n": arr70_n,
        "u32s_head": u32s_head,
        "arr88_size": arr88_size,
        "arr88_sentinel": arr88_sentinel,
        "arr88_kinds": kinds,
        "arr88_ids_n": len(set88),
        "arr88_ids_head": ids_head,
    }
    return hub, meta


def scan_shell_members(b, base, tag, set70, set88):
    focus = set(FOCUS_PROVS)
    by_oi = {}
    all_rows = []
    by_class = defaultdict(list)
    path_union = set()
    path_n = 0
    for oi, idxs in SHELL_MEMBERS.items():
        rows = []
        for idx in idxs:
            try:
                army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
            except Exception:
                rows.append({"index": idx, "ok": False, "error": "resolve"})
                continue
            if not army:
                rows.append({"index": idx, "ok": False, "error": "null"})
                continue
            vt = try_u64(b, army)
            if not vt or (vt - base) != CA_VT_RVA:
                rows.append({"index": idx, "ok": False, "error": "bad_vt"})
                continue
            atag = try_u32(b, army + CA_TAG)
            p = path60(b, base, army, tag)
            n = p.get("n") or 0
            ids = p.get("province_ids") or []
            in70 = sorted(set(ids) & set70)
            in88 = sorted(set(ids) & set88)
            focus_hit = sorted(set(ids) & focus)
            if n <= 0:
                cls = "empty_path"
            elif in70 and in88:
                cls = "tri70_88"
            elif in70:
                cls = "tri70"
            elif in88:
                cls = "hub88"
            else:
                cls = "path_only"
            if n > 0:
                path_n += 1
                path_union.update(ids)
                by_class[cls].append(idx)
            rec = {
                "index": idx,
                "ok": True,
                "tag": atag,
                "ita": atag == tag,
                "path_ids": ids,
                "path_n": n,
                "focus_hit": focus_hit,
                "in70": in70,
                "in88": in88,
                "class": cls,
                "shell_oi": oi,
            }
            rows.append(rec)
            all_rows.append(rec)
        by_oi[str(oi)] = {
            "kind": KIND.get(oi),
            "member_n": len(idxs),
            "path_mem_n": sum(1 for r in rows if (r.get("path_n") or 0) > 0),
            "by_class_n": {
                c: sum(1 for r in rows if r.get("class") == c)
                for c in ("tri70_88", "tri70", "hub88", "path_only", "empty_path")
            },
            "rows": rows,
        }
    return {
        "by_oi": by_oi,
        "path_n": path_n,
        "path_union": sorted(path_union),
        "cross70_path": sorted(path_union & set70),
        "cross88_path": sorted(path_union & set88),
        "focus_in_70": sorted(focus & set70),
        "focus_in_88": sorted(focus & set88),
        "prov_3938_in_70": 3938 in set70,
        "prov_3938_in_88": 3938 in set88,
        "prov_3816_in_70": 3816 in set70,
        "prov_3816_in_88": 3816 in set88,
        "by_class_n": {k: len(v) for k, v in by_class.items()},
        "by_class_idx": {k: v[:16] for k, v in by_class.items()},
        "path_only_rows": [r for r in all_rows if r.get("class") == "path_only"][:20],
        "tri_rows": [r for r in all_rows if r.get("class") in ("tri70", "tri70_88")][:16],
    }


def patch_docs(meta, result, hub_meta, scan_pub):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ii `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2ih `KNOWN_OG_PATH_SHELLS_HIT`",
        "2ii `SHELL_PATH_INST_DRIFT_HIT`",
        "2ii `SHELL_PATH_INST_DRIFT_PARTIAL`",
        "2ii `SHELL_PATH_INST_DRIFT_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = (
        f"path={scan_pub.get('path_n')} arr70={hub_meta.get('arr70_n')} "
        f"arr88={hub_meta.get('arr88_ids_n')} cls={scan_pub.get('by_class_n')} "
        f"cross70={scan_pub.get('cross70_path')} cross88={scan_pub.get('cross88_path')} "
        f"clock={meta.get('clock_class')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ii shell PATH×Inst drift "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ii** | `{result}` | shell-member PATH × 481 Inst70/ARR88 drift | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2ii** |" in t:
        t = re.sub(r"^\| \*\*2ii\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2ih** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ih** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ii shell PATH×Inst drift denser:** result=`{result}` · {brief} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2ii shell PATH×Inst drift denser:**" in t:
        t = re.sub(r"^\*\*2ii shell PATH×Inst drift denser:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2ih known-OG PATH shells denser:**" in t:
        idx = t.find("**2ih known-OG PATH shells denser:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ih · known-OG PATH shells denser · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ii · shell PATH×Inst drift denser · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ih — checklist polish (CLOSED)",
        "## Phase 2gj … 2ii — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ii | shell-member PATH × 481 Inst70/ARR88 drift | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ii |" in t2:
        t2 = re.sub(r"^\| 2ii \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2ih |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ih |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ih — known-OG PATH shells denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ii — shell PATH×Inst drift denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    # slim by_oi for doc
    by_oi_slim = {
        oi: {k: v for k, v in d.items() if k != "rows"}
        for oi, d in (scan_pub.get("by_oi") or {}).items()
    }
    DOC.write_text(
        (
            f"# Phase 2ii — shell-member PATH × 481 Inst70/ARR88 drift denser\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Clock:** {meta.get('clock_class')} · hours={meta.get('hours')} · "
            f"year@+0x478={meta.get('year_at_0x478')} · UI={meta.get('ui_date')}\n\n"
            f"**Constants:** INST_VT=0x2A02558 · CP_VT=0x29EE248 id@+0xA4\n\n"
            f"**Hub:** {json.dumps(hub_meta, ensure_ascii=False)}\n\n"
            f"**Scan:** path_n={scan_pub.get('path_n')} by_class={scan_pub.get('by_class_n')} "
            f"cross70={scan_pub.get('cross70_path')} cross88={scan_pub.get('cross88_path')} "
            f"3938_in70={scan_pub.get('prov_3938_in_70')} 3938_in88={scan_pub.get('prov_3938_in_88')} "
            f"3816_in70={scan_pub.get('prov_3816_in_70')} 3816_in88={scan_pub.get('prov_3816_in_88')}\n\n"
            f"**By OG:** {json.dumps(by_oi_slim, ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** documents 2ih triangle_481_n=0 drift — path dests vs Instant coverage "
            f"on populated 481 only. No Instant on mid/hi-band. Field name STUBBED. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2ii · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ii",
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

    hub, hub_meta = dig_481_hub(b, base)
    set70 = (hub or {}).get("set70") or set()
    set88 = (hub or {}).get("set88") or set()
    scan = scan_shell_members(b, base, tag, set70, set88)
    scan_pub = dict(scan)

    inst_ok = bool(hub_meta.get("inst_ok"))
    arr70 = hub_meta.get("arr70_n") or 0
    arr88 = hub_meta.get("arr88_ids_n") or 0
    path_n = scan["path_n"]
    cls = scan["by_class_n"]
    tri_n = cls.get("tri70", 0) + cls.get("tri70_88", 0)
    po_n = cls.get("path_only", 0)

    # HIT if hub shaped and we catalogued shell paths (tri or honest path_only drift)
    if inst_ok and arr70 > 0 and arr88 > 0 and path_n >= 1 and (tri_n >= 1 or po_n >= 1):
        result = "SHELL_PATH_INST_DRIFT_HIT"
    elif inst_ok and path_n >= 1:
        result = "SHELL_PATH_INST_DRIFT_PARTIAL"
    else:
        result = "SHELL_PATH_INST_DRIFT_EMPTY"

    by_oi_slim = {
        oi: {k: v for k, v in d.items() if k != "rows"}
        for oi, d in scan["by_oi"].items()
    }

    report = {
        "phase": "2ii",
        "result": result,
        "allow_post": False,
        "live": meta,
        "hub": hub_meta,
        "scan": {
            "path_n": path_n,
            "by_class_n": cls,
            "cross70_path": scan["cross70_path"],
            "cross88_path": scan["cross88_path"],
            "focus_in_70": scan["focus_in_70"],
            "focus_in_88": scan["focus_in_88"],
            "prov_3938_in_70": scan["prov_3938_in_70"],
            "prov_3938_in_88": scan["prov_3938_in_88"],
            "prov_3816_in_70": scan["prov_3816_in_70"],
            "prov_3816_in_88": scan["prov_3816_in_88"],
            "by_oi": by_oi_slim,
            "path_only_rows": scan["path_only_rows"],
            "tri_rows": scan["tri_rows"],
        },
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
            "Instant map re-poll",
            "hi-band Instant-empty re-poll",
            "463 Inst70 oi1..511 re-poll",
            "OG575 Instant-empty re-poll",
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2ii shell PATH×Inst drift); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "shell-member PATH × 481 Inst70/ARR88 drift denser; "
            "Instant only on 481; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ii",
                "result": result,
                "allow_post": False,
                "inst_ok": inst_ok,
                "arr70_n": arr70,
                "arr88_ids_n": arr88,
                "path_n": path_n,
                "by_class_n": cls,
                "tri_n": tri_n,
                "path_only_n": po_n,
                "cross70_path": scan["cross70_path"],
                "cross88_path": scan["cross88_path"],
                "focus_in_70": scan["focus_in_70"],
                "focus_in_88": scan["focus_in_88"],
                "prov_3938_in_70": scan["prov_3938_in_70"],
                "prov_3938_in_88": scan["prov_3938_in_88"],
                "prov_3816_in_70": scan["prov_3816_in_70"],
                "prov_3816_in_88": scan["prov_3816_in_88"],
                "by_oi": by_oi_slim,
                "path_only_rows": scan["path_only_rows"][:12],
                "tri_rows": scan["tri_rows"][:8],
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "clock_class": meta.get("clock_class"),
                    "year_at_0x478": meta.get("year_at_0x478"),
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
        patch_docs(meta, result, hub_meta, scan_pub)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2ii",
                "result": result,
                "allow_post": False,
                "live": meta,
                "hub": hub_meta,
                "path_n": path_n,
                "by_class_n": cls,
                "tri_n": tri_n,
                "path_only_n": po_n,
                "cross70_path": scan["cross70_path"],
                "cross88_path": scan["cross88_path"],
                "focus_in_70": scan["focus_in_70"],
                "focus_in_88": scan["focus_in_88"],
                "prov_3938_in_70": scan["prov_3938_in_70"],
                "prov_3938_in_88": scan["prov_3938_in_88"],
                "prov_3816_in_70": scan["prov_3816_in_70"],
                "prov_3816_in_88": scan["prov_3816_in_88"],
                "by_oi": by_oi_slim,
                "path_only_rows": scan["path_only_rows"][:12],
                "tri_rows": scan["tri_rows"][:8],
                "clock_class": meta.get("clock_class"),
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
