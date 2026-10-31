#!/usr/bin/env python3
"""Phase 2hz: non-hiband 2hy focus-path armies → OG+0x50 reverse (RO).

Targets from 2hy focus hits with empty hiband_ois: idx 455/461/463/2640
(path 1176/3816/3938/3938). One-shot scan oi1..1200 OG+0x50 for their MI /
army ptrs. No Instant map / hi-band Instant-empty / 463 Inst70 / Assign /
midflight / Post; never 5x; no speed write; OG+0x50 name STUBBED.
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

OUT = ROOT / "reports" / "phase2hz_nonhiband_path_og50_reverse.json"
SUMMARY = ROOT / "reports" / "phase2hz_summary.json"
DOC = ROOT / "docs" / "PHASE2HZ_NONHIBAND_PATH_OG50_REVERSE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
# 2hy focus_hits with hiband_ois=[]
TARGETS = (
    {"index": 455, "expect_path": [1176]},
    {"index": 461, "expect_path": [3816]},
    {"index": 463, "expect_path": [3938]},
    {"index": 2640, "expect_path": [3938]},
)
HIBAND_OIS = (962, 976)
OI_LO, OI_HI = 1, 1200
SHA_BASE = "d86ec87"


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
            "ITA non-hiband 2hy focus-path armies → OG+0x50 reverse oi1..1200 "
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


def resolve_targets(b, base, tag):
    rows = []
    mi_targets = {}
    army_targets = {}
    for t in TARGETS:
        idx = t["index"]
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            army = None
        if not army:
            rows.append({"index": idx, "ok": False, "error": "resolve_fail", "expect_path": t["expect_path"]})
            continue
        vt = try_u64(b, army)
        if not vt or (vt - base) != CA_VT_RVA:
            rows.append({"index": idx, "ok": False, "error": "bad_vt", "expect_path": t["expect_path"]})
            continue
        atag = try_u32(b, army + CA_TAG)
        mi = army + CA_MI_OFF
        mi_vt = try_u64(b, mi)
        mi_ok = bool(mi_vt and (mi_vt - base) == CA_MI_VT)
        p = path60(b, base, army, tag)
        row = {
            "index": idx,
            "ok": True,
            "army": hex(army),
            "mi": hex(mi),
            "mi_ok": mi_ok,
            "tag": atag,
            "ita": atag == tag,
            "path_ids": p.get("province_ids") or [],
            "path_n": p.get("n") or 0,
            "expect_path": t["expect_path"],
            "path_match_expect": sorted(p.get("province_ids") or []) == sorted(t["expect_path"]),
            "member_ois": [],
            "in_hiband": False,
            "in_og481": False,
            "reverse_hit": False,
        }
        rows.append(row)
        if mi_ok:
            mi_targets[mi] = idx
        army_targets[army] = idx
    return rows, mi_targets, army_targets


def reverse_scan(b, base, mi_targets, army_targets):
    found = defaultdict(list)
    oi_scanned = 0
    oi_with_arr = 0
    for oi in range(OI_LO, OI_HI + 1):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        if not hdr:
            continue
        oi_scanned += 1
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
        if not arr50 or arr50.get("in_image_sentinel"):
            continue
        ptrs = arr50.get("ptrs") or []
        if not ptrs:
            continue
        oi_with_arr += 1
        for p in ptrs:
            if p in mi_targets:
                found[mi_targets[p]].append(oi)
            else:
                primary = p - CA_MI_OFF
                if primary in army_targets:
                    found[army_targets[primary]].append(oi)
    return found, {"oi_scanned": oi_scanned, "oi_with_arr50": oi_with_arr, "oi_band": [OI_LO, OI_HI]}


def patch_docs(meta, result, rows, scan_meta):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hz `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2hy `PATH200_HXFOCUS_DENSE_HIT`",
        "2hz `NONHIBAND_PATH_OG50_REVERSE_HIT`",
        "2hz `NONHIBAND_PATH_OG50_REVERSE_PARTIAL`",
        "2hz `NONHIBAND_PATH_OG50_REVERSE_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = "; ".join(
        f"idx={r.get('index')}→ois={r.get('member_ois')} path={r.get('path_ids')}"
        for r in rows
        if r.get("ok")
    ) or "none"
    hit_n = sum(1 for r in rows if r.get("reverse_hit"))
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hz nonhiband reverse "
        f"hit={hit_n}/{sum(1 for r in rows if r.get('ok'))} {brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hz** | `{result}` | non-hiband 2hy path armies → OG+0x50 reverse oi1..1200 | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2hz** |" in t:
        t = re.sub(r"^\| \*\*2hz\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2hy** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hy** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hz non-hiband path→OG50 reverse:** result=`{result}` · hit={hit_n} · {brief} · "
        f"oi_band={scan_meta.get('oi_band')} oi_with_arr50={scan_meta.get('oi_with_arr50')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2hz non-hiband path→OG50 reverse:**" in t:
        t = re.sub(r"^\*\*2hz non-hiband path→OG50 reverse:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2hy PATH200 hxfocus denser:**" in t:
        idx = t.find("**2hy PATH200 hxfocus denser:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hy · PATH200 hxfocus denser · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hz · non-hiband path→OG50 reverse · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hy — checklist polish (CLOSED)",
        "## Phase 2gj … 2hz — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hz | non-hiband 2hy path armies → OG+0x50 reverse oi1..1200 | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hz |" in t2:
        t2 = re.sub(r"^\| 2hz \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2hy |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hy |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hy — PATH200 hxfocus denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hz — non-hiband path→OG50 reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hz — non-hiband 2hy focus-path → OG+0x50 reverse\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Targets:** idx 455/461/463/2640 (2hy focus_hits with hiband_ois=[])\n\n"
            f"**Rows:** {json.dumps(rows, ensure_ascii=False)}\n\n"
            f"**Scan:** {json.dumps(scan_meta, ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** OG+0x50 membership reverse for non-hiband PATH200 focus carriers. "
            f"No Instant. Field name STUBBED. No invent. No Post / midflight / oi≠0.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hz · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hz",
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

    rows, mi_targets, army_targets = resolve_targets(b, base, tag)
    found, scan_meta = reverse_scan(b, base, mi_targets, army_targets)

    for r in rows:
        if not r.get("ok"):
            continue
        ois = sorted(set(found.get(r["index"]) or []))
        r["member_ois"] = ois
        r["reverse_hit"] = bool(ois)
        r["in_hiband"] = any(oi in HIBAND_OIS for oi in ois)
        r["in_og481"] = 481 in ois

    ok_n = sum(1 for r in rows if r.get("ok"))
    hit_n = sum(1 for r in rows if r.get("reverse_hit"))
    path_live_n = sum(1 for r in rows if r.get("ok") and (r.get("path_n") or 0) > 0)
    non_hiband_hit = sum(1 for r in rows if r.get("reverse_hit") and not r.get("in_hiband"))

    if hit_n >= 2 or (hit_n >= 1 and non_hiband_hit >= 1):
        result = "NONHIBAND_PATH_OG50_REVERSE_HIT"
    elif hit_n == 1:
        result = "NONHIBAND_PATH_OG50_REVERSE_PARTIAL"
    elif ok_n >= 1 and path_live_n >= 1:
        result = "NONHIBAND_PATH_OG50_REVERSE_EMPTY"  # armies live+path but no OG50 in band
    else:
        result = "NONHIBAND_PATH_OG50_REVERSE_EMPTY"

    report = {
        "phase": "2hz",
        "result": result,
        "allow_post": False,
        "live": meta,
        "targets": [t["index"] for t in TARGETS],
        "rows": rows,
        "scan": scan_meta,
        "hit_n": hit_n,
        "ok_n": ok_n,
        "path_live_n": path_live_n,
        "non_hiband_hit_n": non_hiband_hit,
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
            "plan-dense Assign oi≠0 (2hz non-hiband path→OG50 reverse); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "OG+0x50 reverse membership for 2hy non-hiband PATH200 focus carriers; "
            "no Instant; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hz",
                "result": result,
                "allow_post": False,
                "hit_n": hit_n,
                "ok_n": ok_n,
                "path_live_n": path_live_n,
                "non_hiband_hit_n": non_hiband_hit,
                "rows_brief": [
                    {
                        "index": r.get("index"),
                        "path_ids": r.get("path_ids"),
                        "member_ois": r.get("member_ois"),
                        "in_hiband": r.get("in_hiband"),
                        "in_og481": r.get("in_og481"),
                        "reverse_hit": r.get("reverse_hit"),
                    }
                    for r in rows
                ],
                "scan": scan_meta,
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
        patch_docs(meta, result, rows, scan_meta)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hz",
                "result": result,
                "allow_post": False,
                "live": meta,
                "hit_n": hit_n,
                "ok_n": ok_n,
                "path_live_n": path_live_n,
                "non_hiband_hit_n": non_hiband_hit,
                "rows_brief": [
                    {
                        "index": r.get("index"),
                        "ok": r.get("ok"),
                        "path_ids": r.get("path_ids"),
                        "member_ois": r.get("member_ois"),
                        "in_hiband": r.get("in_hiband"),
                        "in_og481": r.get("in_og481"),
                        "reverse_hit": r.get("reverse_hit"),
                        "mi_ok": r.get("mi_ok"),
                    }
                    for r in rows
                ],
                "scan": scan_meta,
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
