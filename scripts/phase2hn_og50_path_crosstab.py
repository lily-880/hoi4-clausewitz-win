#!/usr/bin/env python3
"""Phase 2hn: ITA-wide OG+0x50 × PATH200@+0x60 crosstab (RO).

Tests 2hm hypothesis: path-bearing armies absent from OG+0x50 while
path-empty may sit in OGs (oi=48). One-shot; no field invent; no midflight;
no Assign oi≠0 poll; no Post; never 5x; no speed write.
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

OUT = ROOT / "reports" / "phase2hn_og50_path_crosstab.json"
SUMMARY = ROOT / "reports" / "phase2hn_summary.json"
DOC = ROOT / "docs" / "PHASE2HN_OG50_PATH_CROSSTAB.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
SHA_BASE = "b113501"
ARMY_SCAN = range(900, 1200)


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


def try_i32(b, a):
    try:
        return i32(b, a)
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
        "scenario": "ITA OG+0x50 × PATH200@+0x60 crosstab (no Post, no midflight, no oi≠0)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


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
    blob = try_read(b, data, min(size, max_n) * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    ptrs = [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(min(size, max_n))]
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs}


def path60(b, base, army, tag):
    """Read CArmy+0x60 as stdvec<u32> or cpdx u32; filter tag singleton FP."""
    blob = try_read(b, army + PATH_OFF, 24)
    if not blob or len(blob) < 24:
        return {"n": 0, "province_ids": [], "kind": None}
    begin, end, cap = struct.unpack_from("<QQQ", blob, 0)
    vals = []
    kind = None
    if begin >= 0x10000 and end >= begin and (end - begin) // 4 <= 64:
        n = (end - begin) // 4
        raw = try_read(b, begin, n * 4)
        if raw and len(raw) >= n * 4:
            vals = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(n)]
            if vals and all(looks_like_province(v) for v in vals):
                kind = "stdvec_u32"
    if kind is None:
        data, _cap, size = struct.unpack_from("<Qii", blob, 0)
        if data >= 0x10000 and 0 < size <= 64 and not (base <= data < base + 0x4000000):
            raw = try_read(b, data, size * 4)
            if raw and len(raw) >= size * 4:
                vals = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(size)]
                if vals and all(looks_like_province(v) for v in vals):
                    kind = "cpdx_u32"
                else:
                    vals = []
    # tag-singleton FP filter (2gm/2hj)
    if len(vals) == 1 and vals[0] == tag:
        return {"n": 0, "province_ids": [], "kind": kind, "tag_fp": True}
    return {
        "n": len(vals),
        "province_ids": vals[:12],
        "kind": kind,
        "tag_fp": False,
    }


def enum_ita_armies(b, base, tag):
    rows = []
    mi_map = {}
    for idx in ARMY_SCAN:
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
        mi = army + CA_MI_OFF
        mi_vt = try_u64(b, mi)
        mi_ok = bool(mi_vt and (mi_vt - base) == CA_MI_VT)
        p = path60(b, base, army, tag)
        if p["n"] > 1:
            bucket = "multi"
        elif p["n"] == 1:
            bucket = "nonempty"
        else:
            bucket = "empty"
        row = {
            "index": idx,
            "army": hex(army),
            "mi": hex(mi),
            "mi_vt_match": mi_ok,
            "bucket": bucket,
            "path_n": p["n"],
            "path_ids": p["province_ids"],
            "path_kind": p.get("kind"),
            "ois": [],
        }
        rows.append(row)
        if mi_ok:
            mi_map[mi] = row
    return rows, mi_map


def reverse_og(b, base, mi_map):
    elems = 0
    og_hits = []
    for oi in range(1, 128):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        if not hdr:
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
        if not arr50 or arr50.get("in_image_sentinel") or not arr50.get("ptrs"):
            continue
        matched = []
        for p in arr50["ptrs"]:
            if not p:
                continue
            elems += 1
            if p in mi_map:
                row = mi_map[p]
                if oi not in row["ois"]:
                    row["ois"].append(oi)
                matched.append({"index": row["index"], "bucket": row["bucket"]})
        if matched:
            og_hits.append({"oi": oi, "n": len(matched), "indices": [m["index"] for m in matched]})
    return {"og_hit_n": len(og_hits), "og_hits": og_hits[:24], "elems_scanned": elems}


def crosstab(rows):
    cells = {
        "multi_in_og": 0,
        "multi_out": 0,
        "nonempty_in_og": 0,
        "nonempty_out": 0,
        "empty_in_og": 0,
        "empty_out": 0,
    }
    samples = {"multi": [], "nonempty": [], "empty_in": [], "empty_out": []}
    for r in rows:
        in_og = bool(r["ois"])
        bkt = r["bucket"]
        key = f"{bkt}_{'in_og' if in_og else 'out'}"
        if bkt == "empty":
            cells["empty_in_og" if in_og else "empty_out"] += 1
            bucket_s = samples["empty_in" if in_og else "empty_out"]
        else:
            cells[key] += 1
            bucket_s = samples[bkt]
        if len(bucket_s) < 6:
            bucket_s.append({"index": r["index"], "ois": list(r["ois"]), "path_n": r["path_n"], "path_ids": r["path_ids"]})
    path_in = cells["multi_in_og"] + cells["nonempty_in_og"]
    path_out = cells["multi_out"] + cells["nonempty_out"]
    hyp = None
    if path_in == 0 and path_out > 0 and cells["empty_in_og"] > 0:
        hyp = "PATH_BEARING_ABSENT_FROM_OG50"
    elif path_in > 0 and path_out > 0:
        hyp = "PATH_BEARING_MIXED_OG50"
    elif path_in > 0 and path_out == 0:
        hyp = "PATH_BEARING_ALL_IN_OG50"
    elif path_out == 0 and path_in == 0:
        hyp = "NO_PATH_BEARING"
    else:
        hyp = "PATH_BEARING_ABSENT_EMPTY_ALSO_OUT"
    return {"cells": cells, "samples": samples, "hypothesis": hyp, "path_in_og": path_in, "path_out_og": path_out}


def patch_docs(meta, result, ct, rev, counts):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hn `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2hm `OG50_REVERSE_EMPTY_COHORT_ONLY`",
        "2hn `OG50_PATH_CROSSTAB_HONEST_EMPTY`",
        "2hn `OG50_PATH_CROSSTAB_ALL_OUT`",
        "2hn `OG50_PATH_CROSSTAB_PATH_ABSENT`",
        "2hn `OG50_PATH_CROSSTAB_PARTIAL`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    cells = ct["cells"]
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hn crosstab "
        f"path_in={ct['path_in_og']} path_out={ct['path_out_og']} "
        f"empty_in={cells['empty_in_og']} hyp={ct['hypothesis']} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hn** | `{result}` | OG+0x50 × PATH200@+0x60 ITA crosstab | "
        f"field name / oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hn** |" in t:
        t = re.sub(r"\| \*\*2hn\*\* \|[^\n]*\n", row, t, count=1)
    elif "| **2hm** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hm** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hn OG×PATH crosstab:** result=`{result}` · hyp={ct['hypothesis']} · "
        f"ita={counts.get('ita')} multi={counts.get('multi')} nonempty={counts.get('nonempty')} "
        f"empty={counts.get('empty')} · path_in={ct['path_in_og']} path_out={ct['path_out_og']} "
        f"empty_in={cells['empty_in_og']} · og_hits={rev.get('og_hit_n')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hn OG×PATH crosstab:**" not in t and "**2hm OG↔path-army reverse:**" in t:
        idx = t.find("**2hm OG↔path-army reverse:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hm · OG↔path-army reverse membership · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hn · OG+0x50 × PATH200 crosstab · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hm — checklist polish (CLOSED)",
        "## Phase 2gj … 2hn — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hn | OG+0x50 × PATH200@+0x60 ITA crosstab | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hn |" in t2:
        t2 = re.sub(
            r"\| 2hn \|[^\n]*\n",
            row2,
            t2,
            count=1,
        )
    elif "| 2hm |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hm |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hm — OG↔path-army reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hn — OG×PATH crosstab. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hn",
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

    rows, mi_map = enum_ita_armies(b, base, tag)
    rev = reverse_og(b, base, mi_map)
    ct = crosstab(rows)

    counts = {
        "ita": len(rows),
        "multi": sum(1 for r in rows if r["bucket"] == "multi"),
        "nonempty": sum(1 for r in rows if r["bucket"] == "nonempty"),
        "empty": sum(1 for r in rows if r["bucket"] == "empty"),
        "in_og": sum(1 for r in rows if r["ois"]),
    }

    hyp = ct["hypothesis"]
    if hyp == "PATH_BEARING_ABSENT_FROM_OG50" and counts["multi"] + counts["nonempty"] > 0:
        result = "OG50_PATH_CROSSTAB_PATH_ABSENT"
    elif hyp == "PATH_BEARING_MIXED_OG50":
        result = "OG50_PATH_CROSSTAB_MIXED"
    elif hyp == "PATH_BEARING_ALL_IN_OG50":
        result = "OG50_PATH_CROSSTAB_PATH_IN"
    elif hyp == "PATH_BEARING_ABSENT_EMPTY_ALSO_OUT" and counts["ita"] > 0:
        # Dynamic: path still readable; no ITA MI in OG+0x50 this clock (vs 2hm oi=48)
        result = "OG50_PATH_CROSSTAB_ALL_OUT"
    elif counts["ita"] > 0 and rev.get("og_hit_n", 0) > 0:
        result = "OG50_PATH_CROSSTAB_PARTIAL"
    elif counts["ita"] > 0:
        result = "OG50_PATH_CROSSTAB_HONEST_EMPTY"
    else:
        result = "OG50_PATH_CROSSTAB_NO_ARMIES"

    report = {
        "phase": "2hn",
        "result": result,
        "allow_post": False,
        "live": meta,
        "counts": counts,
        "crosstab": ct,
        "reverse": rev,
        "armies": [
            {
                "index": r["index"],
                "bucket": r["bucket"],
                "ois": r["ois"],
                "path_n": r["path_n"],
                "path_ids": r["path_ids"],
                "mi_vt_match": r["mi_vt_match"],
            }
            for r in rows
        ],
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
            "invent OG+0x50 field name",
        ],
        "semantics": (
            "ITA-wide OG+0x50 × PATH200@+0x60 crosstab; membership proxy only; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hn",
        "result": result,
        "allow_post": False,
        "live": meta,
        "counts": counts,
        "hypothesis": hyp,
        "cells": ct["cells"],
        "path_in_og": ct["path_in_og"],
        "path_out_og": ct["path_out_og"],
        "samples": ct["samples"],
        "og_hit_n": rev.get("og_hit_n"),
        "elems_scanned": rev.get("elems_scanned"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hn OG×PATH crosstab); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "ITA OG×PATH crosstab; no field invent; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hn — OG+0x50 × PATH200@+0x60 ITA crosstab",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Hypothesis:** `{hyp}`",
                "",
                f"**Counts:** ita={counts['ita']} multi={counts['multi']} "
                f"nonempty={counts['nonempty']} empty={counts['empty']} in_og={counts['in_og']}",
                "",
                f"**Cells:** {ct['cells']}",
                "",
                f"**OG hits:** {rev.get('og_hit_n')} · elems_scanned={rev.get('elems_scanned')}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Crosstab membership proxy (OG+0x50[i]==CArmy+0xB8) × "
                "PATH200@+0x60 (tag-FP filtered). Field name still STUBBED. No invent. "
                "No Post / midflight / oi≠0 poll.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for "
                "ring_embed OR later Assign oi≠0; retry GitHub push when reachable. "
                "Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hn · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, ct, rev, counts)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
