#!/usr/bin/env python3
"""Phase 2hy: PATH200 denser multi-army @ 2hx focus provinces (RO).

One-shot: scan ITA CArmy PATH200@+0x60 for focus {1176,3938,3816,915}
(1176 new from 2hx path_mem; keep 3938/3816/915). Tag hits that sit in
hi-band OG962/976 OG+0x50 membership (no Instant). Widen army scan 1..3000.
No Instant map / hi-band Instant-empty / 463 Inst70 / Assign / midflight /
Post; never 5x; no speed write; OG+0x50 name STUBBED.
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

OUT = ROOT / "reports" / "phase2hy_path200_hxfocus_dense.json"
SUMMARY = ROOT / "reports" / "phase2hy_summary.json"
DOC = ROOT / "docs" / "PHASE2HY_PATH200_HXFOCUS_DENSE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
HIBAND_OIS = (962, 976)
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
FOCUS_PROVS = (1176, 3938, 3816, 915)  # 1176 new from 2hx
EXPECT_COVER = (1042, 1046, 1049)  # 2hw/2hx cover_only / seen
ARMY_SCAN_LO = 1
ARMY_SCAN_HI = 3000
SHA_BASE = "c1f3d15"


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
            "ITA PATH200 denser @2hx focus {1176,3938,3816,915} × hiband OG50 tag "
            "(no Instant; no Post; OG50 name STUBBED)"
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


def hiband_army_sets(b, base):
    """OG+0x50 MI → CArmy walkback for oi962/976. No Instant."""
    army_to_ois = defaultdict(list)
    meta = {}
    for oi in HIBAND_OIS:
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            meta[oi] = {"ok": False, "error": "resolve_fail"}
            continue
        if not hdr:
            meta[oi] = {"ok": False, "error": "null_hdr"}
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
        ptrs = (arr50 or {}).get("ptrs") or []
        armies = []
        for mi in ptrs:
            if not mi or mi < 0x10000:
                continue
            vt = try_u64(b, mi)
            if not vt or (vt - base) != CA_MI_VT:
                continue
            army = mi - CA_MI_OFF
            avt = try_u64(b, army)
            if not avt or (avt - base) != CA_VT_RVA:
                continue
            armies.append(army)
            if oi not in army_to_ois[army]:
                army_to_ois[army].append(oi)
        meta[oi] = {
            "ok": True,
            "og50_size": (arr50 or {}).get("size"),
            "walk_ok": len(armies),
        }
    return army_to_ois, meta


def scan_ita_paths(b, base, tag, army_to_ois):
    focus = set(FOCUS_PROVS)
    expect = set(EXPECT_COVER)
    ita_ok = 0
    empty_n = nonempty_n = multi_n = 0
    focus_hits = []
    other_nonempty = []
    by_prov = defaultdict(list)
    expect_seen = []
    hiband_path_n = 0
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
        ois = army_to_ois.get(army) or []
        if ois and n > 0:
            hiband_path_n += 1
        rec = {
            "index": idx,
            "army": hex(army),
            "bucket": bucket,
            "path_n": n,
            "path_ids": ids,
            "focus_hit": inter,
            "hiband_ois": ois,
            "expect_cover": idx in expect,
        }
        if idx in expect:
            expect_seen.append(
                {
                    "index": idx,
                    "path_ids": ids,
                    "focus_hit": inter,
                    "hiband_ois": ois,
                    "bucket": bucket,
                }
            )
        if inter:
            focus_hits.append(rec)
            for pid in inter:
                by_prov[pid].append(idx)
        elif n > 0 and len(other_nonempty) < 24:
            other_nonempty.append(
                {
                    "index": idx,
                    "path_ids": ids,
                    "hiband_ois": ois,
                    "bucket": bucket,
                }
            )
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
        "focus_hiband_n": sum(1 for h in focus_hits if h.get("hiband_ois")),
        "by_focus_prov": {str(k): v for k, v in sorted(by_prov.items())},
        "new_focus_1176_n": len(by_prov.get(1176, [])),
        "expect_cover_seen": expect_seen,
        "hiband_path_n": hiband_path_n,
        "other_nonempty_sample": other_nonempty,
        "other_nonempty_n": len(other_nonempty),
    }


def patch_docs(meta, result, matrix, hiband_meta):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hy `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2hx `HIBAND_OG962_976_DIG_HIT`",
        "2hy `PATH200_HXFOCUS_DENSE_HIT`",
        "2hy `PATH200_HXFOCUS_DENSE_PARTIAL`",
        "2hy `PATH200_HXFOCUS_DENSE_EMPTY`",
        "2hy `PATH200_HXFOCUS_DENSE_MISS_OTHER_NONEMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    cnt = matrix.get("counts") or {}
    byp = matrix.get("by_focus_prov") or {}
    byp_s = ",".join(f"{k}:{len(v)}" for k, v in byp.items()) or "none"
    t = re.sub(
        r"\| `PATH200` \| multi-prov candidates \| [^\n]*\|\n",
        f"| `PATH200` | multi-prov candidates | 2hy hxfocus "
        f"hits={matrix.get('focus_hit_n')} by_prov=[{byp_s}] "
        f"hiband={matrix.get('focus_hiband_n')} "
        f"nonempty={cnt.get('nonempty_total')} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hy** | `{result}` | PATH200 denser @2hx focus {{1176,3938,3816,915}} × hiband OG50 | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2hy** |" in t:
        t = re.sub(r"^\| \*\*2hy\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2hx** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hx** |"):
                out.append(row)
        t = "".join(out)
    hits_s = "; ".join(
        f"idx={h.get('index')}→{h.get('path_ids')} hb={h.get('hiband_ois')}"
        for h in (matrix.get("focus_hits") or [])[:8]
    ) or "none"
    note = (
        f"**2hy PATH200 hxfocus denser:** result=`{result}` · "
        f"focus_hit_n={matrix.get('focus_hit_n')} by_prov=[{byp_s}] · "
        f"new1176={matrix.get('new_focus_1176_n')} focus_hiband={matrix.get('focus_hiband_n')} · "
        f"ita_ok={matrix.get('ita_ok')} nonempty={cnt.get('nonempty_total')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False. hits=[{hits_s}]\n"
    )
    if "**2hy PATH200 hxfocus denser:**" in t:
        t = re.sub(r"^\*\*2hy PATH200 hxfocus denser:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2hx hi-band OG962/976 dig:**" in t:
        idx = t.find("**2hx hi-band OG962/976 dig:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hx · hi-band OG962/976 dig · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hy · PATH200 hxfocus denser · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hx — checklist polish (CLOSED)",
        "## Phase 2gj … 2hy — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hy | PATH200 denser @2hx focus {{1176,3938,3816,915}} × hiband OG50 | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hy |" in t2:
        t2 = re.sub(r"^\| 2hy \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2hx |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hx |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hx — hi-band OG962/976 dig. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hy — PATH200 hxfocus denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hy — PATH200 denser @ 2hx focus {{1176,3938,3816,915}}\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Focus hits:** n={matrix.get('focus_hit_n')} · by_prov={byp} · "
            f"new1176={matrix.get('new_focus_1176_n')} · focus_hiband={matrix.get('focus_hiband_n')}\n\n"
            f"**ITA scan:** ita_ok={matrix.get('ita_ok')} scan={matrix.get('scan_lo')}..{matrix.get('scan_hi')} · "
            f"empty={cnt.get('empty')} nonempty={cnt.get('nonempty')} multi={cnt.get('multi')}\n\n"
            f"**Hiband OG50 (no Instant):** {json.dumps(hiband_meta, ensure_ascii=False)}\n\n"
            f"**Focus hit rows:** {json.dumps(matrix.get('focus_hits') or [], ensure_ascii=False)}\n\n"
            f"**Expect cover (1042/1046/1049):** {json.dumps(matrix.get('expect_cover_seen') or [], ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** PATH200@+0x60 denser keyed on 2hx path_mem (+1176) × hiband OG50 tag. "
            f"No Instant re-poll. Field name STUBBED. No invent. No Post / midflight / oi≠0.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hy · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hy",
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

    army_to_ois, hiband_meta = hiband_army_sets(b, base)
    matrix = scan_ita_paths(b, base, tag, army_to_ois)

    hit_n = matrix.get("focus_hit_n") or 0
    nonempty = (matrix.get("counts") or {}).get("nonempty_total") or 0
    new1176 = matrix.get("new_focus_1176_n") or 0
    if hit_n >= 2 or (hit_n >= 1 and new1176 >= 1):
        result = "PATH200_HXFOCUS_DENSE_HIT"
    elif hit_n == 1:
        result = "PATH200_HXFOCUS_DENSE_PARTIAL"
    elif nonempty > 0:
        result = "PATH200_HXFOCUS_DENSE_MISS_OTHER_NONEMPTY"
    else:
        result = "PATH200_HXFOCUS_DENSE_EMPTY"

    report = {
        "phase": "2hy",
        "result": result,
        "allow_post": False,
        "live": meta,
        "hiband_og50": hiband_meta,
        "matrix": matrix,
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
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hy PATH200 hxfocus denser); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "PATH200@+0x60 denser keyed on 2hx focus provinces (+1176) × hiband OG50 tag; "
            "no Instant; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hy",
                "result": result,
                "allow_post": False,
                "focus_hit_n": hit_n,
                "by_focus_prov": matrix.get("by_focus_prov"),
                "new_focus_1176_n": new1176,
                "focus_hiband_n": matrix.get("focus_hiband_n"),
                "ita_ok": matrix.get("ita_ok"),
                "nonempty_total": nonempty,
                "expect_cover_seen": matrix.get("expect_cover_seen"),
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
        patch_docs(meta, result, matrix, hiband_meta)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hy",
                "result": result,
                "allow_post": False,
                "live": meta,
                "focus_hit_n": hit_n,
                "by_focus_prov": matrix.get("by_focus_prov"),
                "new_focus_1176_n": new1176,
                "focus_hiband_n": matrix.get("focus_hiband_n"),
                "ita_ok": matrix.get("ita_ok"),
                "counts": matrix.get("counts"),
                "focus_hits": [
                    {
                        "index": h["index"],
                        "path_ids": h["path_ids"],
                        "focus_hit": h["focus_hit"],
                        "hiband_ois": h["hiband_ois"],
                        "expect_cover": h["expect_cover"],
                    }
                    for h in (matrix.get("focus_hits") or [])
                ],
                "expect_cover_seen": matrix.get("expect_cover_seen"),
                "hiband_og50": hiband_meta,
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
