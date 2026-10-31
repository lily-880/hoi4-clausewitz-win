#!/usr/bin/env python3
"""Phase 2ic: PATH200 ∩ OG481 Instant+0x70 triangle denser (RO).

One Instant read on focus OG481 only (known populated Inst70; INST_VT=
0x2A02558). Cross all ITA nonempty PATH@+0x60 (army1..3000) with set70.
Tag OG50 membership vs known {481,575,962,976} only (no Instant on those).
No Instant map / hi-band Instant-empty / 463 Inst70 / OG575 Instant-empty /
Assign / midflight / Post; never 5x; no speed write; OG+0x50 name STUBBED.
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

OUT = ROOT / "reports" / "phase2ic_path_og481_inst70_triangle.json"
SUMMARY = ROOT / "reports" / "phase2ic_summary.json"
DOC = ROOT / "docs" / "PHASE2IC_PATH_OG481_INST70_TRIANGLE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
FOCUS_OI = 481
KNOWN_OIS = (481, 575, 962, 976)
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
ARMY_LO, ARMY_HI = 1, 3000
SHA_BASE = "7824726"


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
            "ITA PATH200 ∩ OG481 Inst70 triangle denser "
            "(INST_VT corrected; no Instant-empty re-poll; no Post; OG50 name STUBBED)"
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


def dig_481_inst70(b, base):
    try:
        hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    except Exception:
        return set(), {"ok": False, "error": "resolve_fail"}
    if not hdr:
        return set(), {"ok": False, "error": "null_hdr"}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    if not ptrs:
        return set(), {"ok": True, "inst_ok": False, "arr98_size": (arr98 or {}).get("size"), "arr70_n": 0}
    inst = ptrs[0]
    vt = try_u64(b, inst)
    inst_vt_rva = (vt - base) if vt else None
    inst_ok = bool(vt and (vt - base) == INST_VT)
    if not inst_ok:
        return set(), {
            "ok": True,
            "inst_ok": False,
            "inst_vt_rva": hex(inst_vt_rva) if inst_vt_rva is not None else None,
            "arr98_size": (arr98 or {}).get("size"),
            "arr70_n": 0,
        }
    a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
    if not a70 or a70.get("in_image_sentinel"):
        return set(), {
            "ok": True,
            "inst_ok": True,
            "inst_vt_rva": hex(INST_VT),
            "arr98_size": (arr98 or {}).get("size"),
            "arr70_n": 0,
        }
    u32s = a70.get("u32s") or []
    if not u32s or not all(looks_like_province(v) for v in u32s):
        return set(), {
            "ok": True,
            "inst_ok": True,
            "inst_vt_rva": hex(INST_VT),
            "arr98_size": (arr98 or {}).get("size"),
            "arr70_n": 0,
        }
    return set(u32s), {
        "ok": True,
        "inst_ok": True,
        "inst_vt_rva": hex(INST_VT),
        "arr98_size": (arr98 or {}).get("size"),
        "arr70_n": len(u32s),
        "u32s_head": u32s[:12],
    }


def known_og50_sets(b, base):
    """OG+0x50 membership for known ois only. No Instant."""
    army_to_ois = defaultdict(list)
    meta = {}
    for oi in KNOWN_OIS:
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            meta[str(oi)] = {"ok": False}
            continue
        if not hdr:
            meta[str(oi)] = {"ok": False}
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
        ptrs = (arr50 or {}).get("ptrs") or []
        walk = 0
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
            walk += 1
            if oi not in army_to_ois[army]:
                army_to_ois[army].append(oi)
        meta[str(oi)] = {
            "ok": True,
            "og50_size": (arr50 or {}).get("size"),
            "walk_ok": walk,
        }
    return army_to_ois, meta


def scan_triangle(b, base, tag, set70, army_to_ois):
    ita_ok = empty_n = path_n = tri_n = 0
    rows = []
    by_dest = defaultdict(list)
    path_only = []
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
        atag = try_u32(b, army + CA_TAG)
        if atag != tag:
            continue
        ita_ok += 1
        p = path60(b, base, army, tag)
        n = p.get("n") or 0
        ids = p.get("province_ids") or []
        if n <= 0:
            empty_n += 1
            continue
        path_n += 1
        dest = sorted(set(ids) & set70)
        ois = army_to_ois.get(army) or []
        tri = bool(dest)
        if tri:
            tri_n += 1
            for d in dest:
                by_dest[d].append(idx)
        rec = {
            "index": idx,
            "path_ids": ids,
            "dest_in_70": dest,
            "triangle": tri,
            "known_ois": ois,
            "in_481": 481 in ois,
        }
        rows.append(rec)
        if not tri:
            path_only.append(rec)
    return {
        "ita_ok": ita_ok,
        "empty_n": empty_n,
        "path_n": path_n,
        "triangle_n": tri_n,
        "path_only_n": len(path_only),
        "rows": rows,
        "path_only_head": path_only[:16],
        "by_dest_head": {str(k): v[:10] for k, v in sorted(by_dest.items(), key=lambda kv: -len(kv[1]))[:16]},
        "tri_in_481": sum(1 for r in rows if r["triangle"] and r["in_481"]),
        "tri_not_481": sum(1 for r in rows if r["triangle"] and not r["in_481"]),
        "path_only_in_481": sum(1 for r in path_only if r["in_481"]),
    }


def patch_docs(meta, result, inst_meta, scan_pub, og_meta):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ic `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2ib `PATH200_ALL_REVERSE_HIT`",
        "2ic `PATH_OG481_INST70_TRIANGLE_HIT`",
        "2ic `PATH_OG481_INST70_TRIANGLE_PARTIAL`",
        "2ic `PATH_OG481_INST70_TRIANGLE_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = (
        f"path={scan_pub.get('path_n')} tri={scan_pub.get('triangle_n')} "
        f"path_only={scan_pub.get('path_only_n')} arr70={inst_meta.get('arr70_n')} "
        f"tri_in_481={scan_pub.get('tri_in_481')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ic PATH∩481 Inst70 "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ic** | `{result}` | PATH200 ∩ OG481 Inst70 triangle denser | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2ic** |" in t:
        t = re.sub(r"^\| \*\*2ic\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2ib** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ib** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ic PATH∩OG481 Inst70 triangle:** result=`{result}` · {brief} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2ic PATH∩OG481 Inst70 triangle:**" in t:
        t = re.sub(r"^\*\*2ic PATH∩OG481 Inst70 triangle:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2ib PATH200 denser→OG50 reverse:**" in t:
        idx = t.find("**2ib PATH200 denser→OG50 reverse:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ib · PATH200 denser all→OG50 reverse · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ic · PATH∩OG481 Inst70 triangle · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ib — checklist polish (CLOSED)",
        "## Phase 2gj … 2ic — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ic | PATH200 ∩ OG481 Inst70 triangle denser | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ic |" in t2:
        t2 = re.sub(r"^\| 2ic \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2ib |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ib |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ib — PATH200 denser all→OG50 reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ic — PATH∩OG481 Inst70 triangle. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2ic — PATH ∩ OG481 Inst70 triangle denser\n\n"
            f"**Result:** `{result}`\n\n"
            f"**OG481 Inst70:** {json.dumps(inst_meta, ensure_ascii=False)}\n\n"
            f"**Known OG50 meta:** {json.dumps(og_meta, ensure_ascii=False)}\n\n"
            f"**Scan:** {json.dumps({k: v for k, v in scan_pub.items() if k != 'rows'}, ensure_ascii=False)}\n\n"
            f"**Triangle rows:** {json.dumps([r for r in scan_pub.get('rows', []) if r.get('triangle')][:24], ensure_ascii=False)}\n\n"
            f"**Path-only head:** {json.dumps(scan_pub.get('path_only_head', []), ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** denser PATH∩focus Inst70; Instant only on OG481 (populated). "
            f"No Instant-empty re-poll of 575/962/976. Field name STUBBED. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2ic · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ic",
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

    set70, inst_meta = dig_481_inst70(b, base)
    army_to_ois, og_meta = known_og50_sets(b, base)
    scan = scan_triangle(b, base, tag, set70, army_to_ois)
    scan_pub = dict(scan)

    tri_n = scan["triangle_n"]
    path_n = scan["path_n"]
    arr70 = inst_meta.get("arr70_n") or 0
    inst_ok = bool(inst_meta.get("inst_ok"))

    if inst_ok and arr70 > 0 and tri_n >= 1:
        result = "PATH_OG481_INST70_TRIANGLE_HIT"
    elif inst_ok and arr70 > 0 and path_n >= 1:
        result = "PATH_OG481_INST70_TRIANGLE_PARTIAL"
    elif path_n >= 1:
        result = "PATH_OG481_INST70_TRIANGLE_EMPTY"
    else:
        result = "PATH_OG481_INST70_TRIANGLE_EMPTY"

    report = {
        "phase": "2ic",
        "result": result,
        "allow_post": False,
        "live": meta,
        "inst481": inst_meta,
        "known_og50": og_meta,
        "scan": {
            k: v
            for k, v in scan_pub.items()
            if k != "rows"
        },
        "triangle_rows": [r for r in scan_pub.get("rows", []) if r.get("triangle")],
        "path_only_head": scan_pub.get("path_only_head"),
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
            "plan-dense Assign oi≠0 (2ic PATH∩481 Inst70); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "PATH200 ∩ OG481 Instant+0x70 triangle denser; Instant only on 481; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ic",
                "result": result,
                "allow_post": False,
                "inst_ok": inst_ok,
                "arr70_n": arr70,
                "path_n": path_n,
                "triangle_n": tri_n,
                "path_only_n": scan["path_only_n"],
                "tri_in_481": scan["tri_in_481"],
                "tri_not_481": scan["tri_not_481"],
                "path_only_in_481": scan["path_only_in_481"],
                "by_dest_head": scan["by_dest_head"],
                "triangle_rows": report["triangle_rows"][:24],
                "path_only_head": scan["path_only_head"][:12],
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
        patch_docs(meta, result, inst_meta, scan_pub, og_meta)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2ic",
                "result": result,
                "allow_post": False,
                "live": meta,
                "inst481": inst_meta,
                "path_n": path_n,
                "triangle_n": tri_n,
                "path_only_n": scan["path_only_n"],
                "tri_in_481": scan["tri_in_481"],
                "tri_not_481": scan["tri_not_481"],
                "path_only_in_481": scan["path_only_in_481"],
                "by_dest_head": scan["by_dest_head"],
                "triangle_rows": report["triangle_rows"][:24],
                "path_only_head": scan["path_only_head"][:12],
                "known_og50": og_meta,
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
