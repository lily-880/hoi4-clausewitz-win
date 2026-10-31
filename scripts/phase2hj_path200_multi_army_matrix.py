#!/usr/bin/env python3
"""Phase 2hj: PATH200 multi-army matrix one-shot (RO).

Per-army path-candidate matrix across all tag-FP ITA CArmy rows (empty +
nonempty + multi). Extends 2hi densify (nonempty-only) with full army roster
at known cand offs (esp. +0x60). ≤5s early-exit. NO midflight / no oi≠0 poll /
no Post / never 5x / no speed write.
"""
from __future__ import annotations

import json
import re
import struct
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hj_path200_multi_army_matrix.json"
SUMMARY = ROOT / "reports" / "phase2hj_summary.json"
DOC = ROOT / "docs" / "PHASE2HJ_PATH200_MULTI_ARMY_MATRIX.md"

PATH_S = 5.0
GS_PLAYER_TAG = 0x518
SHA_BASE = "58b465c"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


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
        "scenario": "ITA PATH200 multi-army matrix one-shot (no Post, no midflight, no oi≠0 poll)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def load_gm():
    path = ROOT / "scripts" / "phase2gm_carmy_path_instance_ro.py"
    src = path.read_text(encoding="utf-8")
    marker = '\nif __name__ == "__main__":'
    if marker in src:
        src = src.split(marker)[0]
    mod = types.ModuleType("phase2gm_helpers_hj")
    mod.__file__ = str(path)
    sys.modules["phase2gm_helpers_hj"] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def army_matrix(paths: dict) -> dict:
    """Full per-army roster: empty / nonempty / multi with +0x60 focus."""
    armies = paths.get("armies_sample") or []
    rows = []
    off_hist = {}
    empty_n = nonempty_n = multi_n = 0
    off60_hits = []
    for a in armies:
        status = a.get("movement_dest_status") or "unknown"
        cands = a.get("vector_cands") or []
        compact = [
            {
                "kind": c.get("kind"),
                "off": c.get("off"),
                "n": c.get("n"),
                "province_ids": (c.get("province_ids") or [])[:12],
            }
            for c in cands
        ]
        is_multi = any((c.get("n") or 0) > 1 for c in compact)
        if status == "nonempty_candidate":
            nonempty_n += 1
            if is_multi:
                multi_n += 1
                bucket = "multi"
            else:
                bucket = "nonempty"
        else:
            empty_n += 1
            bucket = "empty"
        off60 = next((c for c in compact if c.get("off") == "0x60"), None)
        if off60:
            off60_hits.append(
                {
                    "index": a.get("index"),
                    "province_id": a.get("province_id"),
                    "n": off60.get("n"),
                    "province_ids": off60.get("province_ids"),
                }
            )
        for c in compact:
            off = c.get("off")
            if off:
                off_hist[off] = off_hist.get(off, 0) + 1
        rows.append(
            {
                "index": a.get("index"),
                "handle": a.get("handle"),
                "province_id": a.get("province_id"),
                "army": a.get("army"),
                "bucket": bucket,
                "status": status,
                "cands": compact,
                "off60": off60,
            }
        )
    return {
        "army_rows": rows[:24],
        "counts": {
            "total": len(rows),
            "empty": empty_n,
            "nonempty": nonempty_n,
            "multi": multi_n,
        },
        "off60_hits": off60_hits[:8],
        "cand_off_histogram": off_hist,
        "note": (
            "Full tag-FP CArmy matrix (empty+nonempty+multi); "
            "province-vector cands NOT demangled movement_dest; NOT midflight"
        ),
    }


def patch_docs(meta, result, paths, matrix):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hi `PATH200_DENSE_MULTI_HIT`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hj `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    offs = ",".join(sorted((matrix.get("cand_off_histogram") or {}).keys())) or "?"
    cnt = matrix.get("counts") or {}
    t = re.sub(
        r"\| `PATH200` \| multi-prov candidates \| denser 2hi[^\n]*\|\n",
        f"| `PATH200` | multi-prov candidates | 2hj matrix empty={cnt.get('empty')} "
        f"nonempty={cnt.get('nonempty')} multi={cnt.get('multi')} offs=[{offs}] |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hj** | `{result}` | PATH200 multi-army matrix (empty+nonempty+multi @+0x60) | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hj** |" not in t and "| **2hi** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hi** |"):
                out.append(row)
        t = "".join(out)
    off60 = matrix.get("off60_hits") or []
    off60_s = "; ".join(
        f"idx={h.get('index')}→{h.get('province_ids')}" for h in off60[:3]
    ) or "none"
    note = (
        f"**2hj PATH200 multi-army matrix:** result=`{result}` · "
        f"carmy={paths.get('carmy_rows')} empty={cnt.get('empty')} "
        f"nonempty={cnt.get('nonempty')} multi={cnt.get('multi')} · "
        f"off60=[{off60_s}] · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
        f"allow_post=False.\n"
    )
    if "**2hj PATH200 multi-army matrix:**" not in t and "**2hi PATH200 denser:**" in t:
        idx = t.find("**2hi PATH200 denser:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hi · PATH200 denser sample · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hj · PATH200 multi-army matrix · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hi — checklist polish (CLOSED)",
        "## Phase 2gj … 2hj — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hj | PATH200 multi-army matrix (empty+nonempty+multi) | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hj |" not in t2 and "| 2hi |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hi |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hi — PATH200 denser sample. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hj — PATH200 multi-army matrix. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hj",
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

    gm = load_gm()
    paths = gm.bounded_path_poll(
        b, base, tag, seconds=PATH_S, interval=getattr(gm, "PATH_INTERVAL_S", 1.0)
    )
    matrix = army_matrix(paths)

    cnt = matrix.get("counts") or {}
    nonempty = cnt.get("nonempty") or 0
    multi = cnt.get("multi") or 0
    off60_n = len(matrix.get("off60_hits") or [])
    if multi > 0 and off60_n > 0:
        result = "PATH200_MULTI_ARMY_MATRIX_HIT"
    elif nonempty > 0:
        result = "PATH200_MULTI_ARMY_NONEMPTY"
    else:
        result = "PATH200_MULTI_ARMY_EMPTY"

    report = {
        "phase": "2hj",
        "result": result,
        "allow_post": False,
        "live": meta,
        "path": {
            "window_s": PATH_S,
            "carmy_rows": paths.get("carmy_rows"),
            "movement_dest_nonempty_count": paths.get("movement_dest_nonempty_count"),
            "multi_province_cand_count": paths.get("multi_province_cand_count"),
            "poll_ticks": paths.get("poll_ticks"),
            "elapsed_s": paths.get("elapsed_s"),
            "tag_singleton_fps_filtered": paths.get("tag_singleton_fps_filtered"),
        },
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
            "named movement_dest invent",
        ],
        "semantics": (
            "Full ITA CArmy PATH200 matrix (empty+nonempty+multi); "
            "not demangled dest; not midflight; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hj",
        "result": result,
        "allow_post": False,
        "live": meta,
        "carmy_rows": paths.get("carmy_rows"),
        "matrix_counts": cnt,
        "off60_n": off60_n,
        "cand_offs": list((matrix.get("cand_off_histogram") or {}).keys()),
        "poll_ticks": paths.get("poll_ticks"),
        "elapsed_s": paths.get("elapsed_s"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hj PATH200 multi-army matrix); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "PATH200 multi-army matrix one-shot; no oi≠0 poll; no midflight; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hj — PATH200 multi-army matrix",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Matrix (≤{PATH_S:.0f}s):** carmy={paths.get('carmy_rows')} · "
                f"empty={cnt.get('empty')} · nonempty={cnt.get('nonempty')} · "
                f"multi={cnt.get('multi')} · off60_hits={off60_n} · "
                f"ticks={paths.get('poll_ticks')} · elapsed={paths.get('elapsed_s')}s",
                "",
                f"**Cand offs:** {sorted((matrix.get('cand_off_histogram') or {}).keys())}",
                "",
                f"**off60 hits:** {matrix.get('off60_hits')}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Full tag-FP CArmy path-candidate matrix. "
                "NOT named movement_dest / NOT midflight hex / no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hj · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, paths, matrix)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
