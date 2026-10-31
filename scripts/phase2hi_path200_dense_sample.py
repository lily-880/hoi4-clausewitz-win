#!/usr/bin/env python3
"""Phase 2hi: PATH200 denser one-shot sample (RO).

Deepen nonempty/multi CArmy+0x200 province-vector candidates post-2hh.
One-shot (≤5s early-exit on multi). NO midflight / no oi≠0 poll / no Post /
never 5x / no speed write.
"""
from __future__ import annotations

import json
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

OUT = ROOT / "reports" / "phase2hi_path200_dense_sample.json"
SUMMARY = ROOT / "reports" / "phase2hi_summary.json"
DOC = ROOT / "docs" / "PHASE2HI_PATH200_DENSE_SAMPLE.md"

PATH_S = 5.0  # early-exit when multi>0; not a long poll
GS_PLAYER_TAG = 0x518


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
        "scenario": "ITA PATH200 denser one-shot (no Post, no midflight, no oi≠0 poll)",
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
    mod = types.ModuleType("phase2gm_helpers_hi")
    mod.__file__ = str(path)
    sys.modules["phase2gm_helpers_hi"] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def densify(paths: dict) -> dict:
    """Extract compact nonempty/multi army detail for agent feed."""
    armies = paths.get("armies_sample") or []
    nonempty_rows = []
    multi_rows = []
    off_hist = {}
    for a in armies:
        status = a.get("movement_dest_status")
        cands = a.get("vector_cands") or []
        compact_cands = [
            {
                "kind": c.get("kind"),
                "off": c.get("off"),
                "n": c.get("n"),
                "province_ids": (c.get("province_ids") or [])[:12],
            }
            for c in cands
        ]
        row = {
            "index": a.get("index"),
            "handle": a.get("handle"),
            "province_id": a.get("province_id"),
            "army": a.get("army"),
            "status": status,
            "cands": compact_cands,
        }
        if status == "nonempty_candidate":
            nonempty_rows.append(row)
            if any((c.get("n") or 0) > 1 for c in compact_cands):
                multi_rows.append(row)
            for c in compact_cands:
                off = c.get("off")
                if off:
                    off_hist[off] = off_hist.get(off, 0) + 1
    return {
        "nonempty_detail": nonempty_rows[:8],
        "multi_detail": multi_rows[:4],
        "cand_off_histogram": off_hist,
        "note": (
            "Province-vector candidates at CArmy offsets (tag-FP filtered); "
            "NOT demangled named movement_dest; NOT midflight hex"
        ),
    }


def patch_docs(meta, result, paths, dense):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hh `POST_RELOAD_PERCEPTION_HIT`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hi `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    import re

    offs = ",".join(sorted((dense.get("cand_off_histogram") or {}).keys())) or "?"
    t = re.sub(
        r"\| `PATH200` \| multi-prov candidates \| CArmy`\+0x200` tag-FP — LIVE 2hh[^\n]*\|\n",
        f"| `PATH200` | multi-prov candidates | denser 2hi nonempty="
        f"{paths.get('movement_dest_nonempty_count')} multi="
        f"{paths.get('multi_province_cand_count')} offs=[{offs}] |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hi** | `{result}` | PATH200 denser one-shot (nonempty/multi province vectors) | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hi** |" not in t and "| **2hh** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hh** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hi PATH200 denser:** result=`{result}` · "
        f"carmy={paths.get('carmy_rows')} nonempty={paths.get('movement_dest_nonempty_count')} "
        f"multi={paths.get('multi_province_cand_count')} · offs=[{offs}] · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hi PATH200 denser:**" not in t and "**2hh post-reload perception:**" in t:
        idx = t.find("**2hh post-reload perception:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hh · post-reload PATH200+OG50 · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hi · PATH200 denser sample · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hh — checklist polish (CLOSED)",
        "## Phase 2gj … 2hi — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hi | PATH200 denser one-shot nonempty/multi sample | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hi |" not in t2 and "| 2hh |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hh |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hh — post-reload PATH200+OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hi — PATH200 denser sample. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hi",
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
    dense = densify(paths)

    nonempty = paths.get("movement_dest_nonempty_count") or 0
    multi = paths.get("multi_province_cand_count") or 0
    if nonempty > 0 and multi > 0 and dense.get("multi_detail"):
        result = "PATH200_DENSE_MULTI_HIT"
    elif nonempty > 0:
        result = "PATH200_DENSE_NONEMPTY"
    else:
        result = "PATH200_DENSE_EMPTY"

    report = {
        "phase": "2hi",
        "result": result,
        "allow_post": False,
        "live": meta,
        "path": {
            "window_s": PATH_S,
            "carmy_rows": paths.get("carmy_rows"),
            "movement_dest_nonempty_count": nonempty,
            "multi_province_cand_count": multi,
            "poll_ticks": paths.get("poll_ticks"),
            "elapsed_s": paths.get("elapsed_s"),
            "tag_singleton_fps_filtered": paths.get("tag_singleton_fps_filtered"),
        },
        "dense": dense,
        "sha_base": "3ea48fd",
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
            "Denser PATH200 province-vector sample; not demangled dest; "
            "not midflight; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hi",
        "result": result,
        "allow_post": False,
        "live": meta,
        "carmy_rows": paths.get("carmy_rows"),
        "path_nonempty": nonempty,
        "path_multi": multi,
        "poll_ticks": paths.get("poll_ticks"),
        "elapsed_s": paths.get("elapsed_s"),
        "cand_offs": list((dense.get("cand_off_histogram") or {}).keys()),
        "multi_n": len(dense.get("multi_detail") or []),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hi PATH200 denser); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": "3ea48fd",
        "semantics": "PATH200 denser one-shot; no oi≠0 poll; no midflight; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    multi0 = (dense.get("multi_detail") or [{}])[0]
    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hi — PATH200 denser one-shot sample",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Path (≤{PATH_S:.0f}s early-exit):** carmy={paths.get('carmy_rows')} · "
                f"nonempty={nonempty} · multi={multi} · ticks={paths.get('poll_ticks')} · "
                f"elapsed={paths.get('elapsed_s')}s",
                "",
                f"**Cand offs:** {sorted((dense.get('cand_off_histogram') or {}).keys())}",
                "",
                f"**Multi sample0:** index={multi0.get('index')} · prov={multi0.get('province_id')} · "
                f"cands={multi0.get('cands')}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Denser CArmy province-vector candidates (tag-FP filtered). "
                "NOT named movement_dest / NOT midflight hex / no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hi · 2026-10-31 Asia/Shanghai · sha_base 3ea48fd*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, paths, dense)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
