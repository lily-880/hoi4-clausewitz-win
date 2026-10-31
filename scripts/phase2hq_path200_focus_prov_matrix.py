#!/usr/bin/env python3
"""Phase 2hq: PATH200 denser multi-army keyed on 2hp focus provinces (RO).

One-shot: scan ITA CArmy PATH200@+0x60 for shared dests {3816,3938,915}
(from 2hp path_union + out-of-OG 1039). Also one-shot dump oi=481
OG+0x98 Instant ptr VT RVAs (catalog why inst_vt_ok=False) — NOT an
Instant re-poll of +0x70/+0x88 maps. No midflight; no Assign oi≠0;
no Post; never 5x; no speed write; no field invent.
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

OUT = ROOT / "reports" / "phase2hq_path200_focus_prov_matrix.json"
SUMMARY = ROOT / "reports" / "phase2hq_summary.json"
DOC = ROOT / "docs" / "PHASE2HQ_PATH200_FOCUS_PROV_MATRIX.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A84A38
FOCUS_OI = 481
FOCUS_PROVS = (3816, 3938, 915)
ARMY_SCAN_LO = 1
ARMY_SCAN_HI = 2000
SHA_BASE = "b1ddfbf"


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
            "ITA PATH200 denser @focus {3816,3938,915} + oi=481 Instant VT dump "
            "(no Post, no midflight, no oi≠0, no Instant map re-poll)"
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
        return {"n": 0, "province_ids": [], "tag_fp": True}
    return {"n": len(vals), "province_ids": vals[:12], "tag_fp": False}


def read_cpdx_ptrs(b, base, arr_addr, max_n=8):
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
    ptrs = [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(n)]
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs, "data": hex(data)}


def dump_oi481_inst_vt(b, base):
    """One-shot VT dump of OG+0x98 ptrs — not Instant map re-poll."""
    try:
        hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    except Exception:
        hdr = None
    if not hdr:
        return {"ok": False, "reason": "og_unresolved"}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 8)
    ptrs = (arr98 or {}).get("ptrs") or []
    rows = []
    any_inst = False
    for p in ptrs:
        if not p or p < 0x10000:
            rows.append({"ptr": hex(p) if p else None, "vt_rva": None, "is_inst_vt": False})
            continue
        vt = try_u64(b, p)
        rva = (vt - base) if vt else None
        is_inst = bool(rva is not None and rva == INST_VT)
        if is_inst:
            any_inst = True
        rows.append(
            {
                "ptr": hex(p),
                "vt_rva": hex(rva) if rva is not None else None,
                "is_inst_vt": is_inst,
            }
        )
    return {
        "ok": True,
        "oi": FOCUS_OI,
        "arr98_size": (arr98 or {}).get("size"),
        "ptr_n": len(rows),
        "any_inst_vt": any_inst,
        "ptrs": rows,
        "note": "one-shot VT catalog; no +0x70/+0x88 Instant map re-poll",
    }


def scan_ita_paths(b, base, tag):
    focus = set(FOCUS_PROVS)
    ita_ok = 0
    empty_n = nonempty_n = multi_n = 0
    focus_hits = []  # armies intersecting focus set
    other_nonempty = []  # nonempty not intersecting focus (cap)
    by_prov = defaultdict(list)
    for idx in range(ARMY_SCAN_LO, ARMY_SCAN_HI + 1):
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            continue
        if not army:
            continue
        vt = try_u64(b, army)
        if not vt or (vt - base) != CA_VT_RVA:
            continue
        atag = try_u32(b, army + CA_TAG)
        if atag != tag:
            continue
        ita_ok += 1
        p = path60(b, base, army, tag)
        n = p.get("n") or 0
        ids = p.get("province_ids") or []
        if n > 1:
            multi_n += 1
            bucket = "multi"
        elif n == 1:
            nonempty_n += 1
            bucket = "nonempty"
        else:
            empty_n += 1
            bucket = "empty"
        inter = sorted(set(ids) & focus)
        rec = {
            "index": idx,
            "army": hex(army),
            "bucket": bucket,
            "path_n": n,
            "path_ids": ids,
            "focus_hit": inter,
        }
        if inter:
            focus_hits.append(rec)
            for pid in inter:
                by_prov[pid].append(idx)
        elif n > 0 and len(other_nonempty) < 24:
            other_nonempty.append(rec)
    return {
        "scan_lo": ARMY_SCAN_LO,
        "scan_hi": ARMY_SCAN_HI,
        "ita_ok": ita_ok,
        "counts": {
            "empty": empty_n,
            "nonempty": nonempty_n,
            "multi": multi_n,
            "nonempty_total": nonempty_n + multi_n,
        },
        "focus_provs": list(FOCUS_PROVS),
        "focus_hit_n": len(focus_hits),
        "focus_hits": focus_hits,
        "by_focus_prov": {str(k): v for k, v in sorted(by_prov.items())},
        "other_nonempty_sample": other_nonempty,
        "other_nonempty_n": len(other_nonempty),
    }


def patch_docs(meta, result, matrix, vt_dump):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hq `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2hp `OG481_MEMBERS_PATH_ONLY`",
        "2hq `PATH200_FOCUS_PROV_HIT`",
        "2hq `PATH200_FOCUS_PROV_PARTIAL`",
        "2hq `PATH200_FOCUS_PROV_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    cnt = matrix.get("counts") or {}
    byp = matrix.get("by_focus_prov") or {}
    byp_s = ",".join(f"{k}:{len(v)}" for k, v in byp.items()) or "none"
    t = re.sub(
        r"\| `PATH200` \| multi-prov candidates \| [^\n]*\|\n",
        f"| `PATH200` | multi-prov candidates | 2hq focus "
        f"hits={matrix.get('focus_hit_n')} by_prov=[{byp_s}] "
        f"nonempty={cnt.get('nonempty_total')} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hq** | `{result}` | PATH200 denser focus {{3816,3938,915}} + oi=481 Instant VT dump | "
        f"oi≠0 / midflight / Instant-map-repoll / Post HARD_DENY |\n"
    )
    if "| **2hq** |" not in t and "| **2hp** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hp** |"):
                out.append(row)
        t = "".join(out)
    hits_s = "; ".join(
        f"idx={h.get('index')}→{h.get('path_ids')}" for h in (matrix.get("focus_hits") or [])[:6]
    ) or "none"
    any_inst = (vt_dump or {}).get("any_inst_vt")
    note = (
        f"**2hq PATH200 focus-prov denser:** result=`{result}` · "
        f"focus_hit_n={matrix.get('focus_hit_n')} by_prov=[{byp_s}] · "
        f"ita_ok={matrix.get('ita_ok')} nonempty={cnt.get('nonempty_total')} · "
        f"oi481_any_inst_vt={any_inst} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
        f"allow_post=False. hits=[{hits_s}]\n"
    )
    if "**2hq PATH200 focus-prov denser:**" not in t and "**2hp oi=481 Inst×PATH cross:**" in t:
        idx = t.find("**2hp oi=481 Inst×PATH cross:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hp · oi=481 OG50×Inst×PATH cross · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hq · PATH200 focus-prov denser · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hp — checklist polish (CLOSED)",
        "## Phase 2gj … 2hq — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hq | PATH200 denser focus {{3816,3938,915}} + Instant VT dump | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hq |" not in t2 and "| 2hp |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hp |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hp — oi=481 Inst×PATH cross. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hq — PATH200 focus-prov denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    vt_ptrs = (vt_dump or {}).get("ptrs") or []
    vt_s = "; ".join(
        f"{r.get('ptr')} vt={r.get('vt_rva')} inst={r.get('is_inst_vt')}" for r in vt_ptrs[:4]
    ) or "none"
    DOC.write_text(
        (
            f"# Phase 2hq — PATH200 denser focus provinces {{3816,3938,915}}\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Focus hits:** n={matrix.get('focus_hit_n')} · by_prov={byp}\n\n"
            f"**ITA scan:** ita_ok={matrix.get('ita_ok')} · "
            f"empty={cnt.get('empty')} nonempty={cnt.get('nonempty')} multi={cnt.get('multi')}\n\n"
            f"**Focus hit rows:** {json.dumps(matrix.get('focus_hits') or [], ensure_ascii=False)}\n\n"
            f"**oi=481 Instant VT dump (one-shot, no map re-poll):** any_inst={any_inst} · {vt_s}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** PATH200@+0x60 denser keyed on 2hp provinces; Instant VT catalog only. "
            f"Field name STUBBED. No invent. No Post / midflight / oi≠0 / Instant-map re-poll.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hq · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hq",
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

    matrix = scan_ita_paths(b, base, tag)
    vt_dump = dump_oi481_inst_vt(b, base)

    hit_n = matrix.get("focus_hit_n") or 0
    nonempty = (matrix.get("counts") or {}).get("nonempty_total") or 0
    if hit_n >= 2:
        result = "PATH200_FOCUS_PROV_HIT"
    elif hit_n == 1:
        result = "PATH200_FOCUS_PROV_PARTIAL"
    elif nonempty > 0:
        result = "PATH200_FOCUS_PROV_MISS_OTHER_NONEMPTY"
    else:
        result = "PATH200_FOCUS_PROV_EMPTY"

    report = {
        "phase": "2hq",
        "result": result,
        "allow_post": False,
        "live": meta,
        "matrix": matrix,
        "oi481_inst_vt_dump": vt_dump,
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
            "Instant +0x70/+0x88 re-poll",
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hq PATH200 focus denser); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "PATH200@+0x60 denser keyed on 2hp focus provinces; "
            "oi=481 Instant VT one-shot dump only; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hq",
                "result": result,
                "allow_post": False,
                "focus_hit_n": hit_n,
                "by_focus_prov": matrix.get("by_focus_prov"),
                "ita_ok": matrix.get("ita_ok"),
                "nonempty_total": nonempty,
                "oi481_any_inst_vt": (vt_dump or {}).get("any_inst_vt"),
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
        patch_docs(meta, result, matrix, vt_dump)
    except Exception as e:
        report["doc_patch_error"] = str(e)

    print(
        json.dumps(
            {
                "phase": "2hq",
                "result": result,
                "allow_post": False,
                "live": meta,
                "focus_hit_n": hit_n,
                "by_focus_prov": matrix.get("by_focus_prov"),
                "ita_ok": matrix.get("ita_ok"),
                "counts": matrix.get("counts"),
                "focus_hits": [
                    {"index": h["index"], "path_ids": h["path_ids"], "focus_hit": h["focus_hit"]}
                    for h in (matrix.get("focus_hits") or [])
                ],
                "oi481_any_inst_vt": (vt_dump or {}).get("any_inst_vt"),
                "oi481_ptrs": (vt_dump or {}).get("ptrs"),
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
