#!/usr/bin/env python3
"""Phase 2ht: multi-oi Instant+0x70 × ITA PATH200 perception (RO).

Uses corrected INST_VT=0x2A02558 and CP_VT=0x29EE248 id@+0xA4.
One-shot: scan OG oi1..511 Instant+0x70 province sets; scan ITA PATH200@+0x60;
cross path dests → covering oi(s). Optional light +0x88 id presence for focus
provs only. No Post; never 5x; no speed write; no midflight; no Assign oi≠0;
no endless Instant poll; no field invent.
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

OUT = ROOT / "reports" / "phase2ht_multi_oi_inst70_path_cross.json"
SUMMARY = ROOT / "reports" / "phase2ht_summary.json"
DOC = ROOT / "docs" / "PHASE2HT_MULTI_OI_INST70_PATH_CROSS.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
CP_VT = 0x29EE248
CP_ID = 0xA4
OI_LO, OI_HI = 1, 511
ARMY_LO, ARMY_HI = 1, 2000
FOCUS_PROVS = (3816, 3938, 915)
SHA_BASE = "9cce48c"


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
            "ITA multi-oi Instant+0x70 × PATH200 (INST_VT/CP_VT corrected; "
            "no Post, no midflight, no oi≠0, no endless Instant poll)"
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


def scan_ita_paths(b, base, tag):
    rows = []
    nonempty = 0
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
        if try_u32(b, army + CA_TAG) != tag:
            continue
        p = path60(b, base, army, tag)
        if p["n"] <= 0:
            continue
        nonempty += 1
        rows.append({"index": idx, "army": hex(army), "path_ids": p["province_ids"], "path_n": p["n"]})
    return {"nonempty_n": nonempty, "rows": rows}


def focus_in_88(b, base, inst, focus: set) -> list:
    """Light: only check whether focus provs appear as CProvince ids in +0x88."""
    a88 = read_cpdx_ptrs(b, base, inst + 0x88, 64)
    if not a88 or a88.get("in_image_sentinel"):
        return []
    hit = set()
    for p in a88.get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        vt = try_u64(b, p)
        if not vt or (vt - base) != CP_VT:
            continue
        pid = try_u32(b, p + CP_ID)
        if pid in focus:
            hit.add(pid)
    return sorted(hit)


def scan_ois(b, base, focus: set):
    oi_inst_ok = 0
    oi_70_shaped = 0
    oi_rows = []
    prov_to_ois = defaultdict(list)
    focus_70_ois = defaultdict(list)
    focus_88_ois = defaultdict(list)
    for oi in range(OI_LO, OI_HI + 1):
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
        u32s = []
        shaped = False
        if a70 and not a70.get("in_image_sentinel"):
            u32s = a70.get("u32s") or []
            shaped = bool(u32s) and all(looks_like_province(v) for v in u32s)
        if not shaped:
            continue
        oi_70_shaped += 1
        s70 = set(u32s)
        for pid in s70:
            prov_to_ois[pid].append(oi)
        f70 = sorted(s70 & focus)
        for pid in f70:
            focus_70_ois[pid].append(oi)
        f88 = focus_in_88(b, base, inst, focus) if f70 or True else []
        # always light-check focus in 88 for shaped ois (bounded 511)
        f88 = focus_in_88(b, base, inst, focus)
        for pid in f88:
            focus_88_ois[pid].append(oi)
        if f70 or f88 or oi in (481,):
            oi_rows.append(
                {
                    "oi": oi,
                    "arr70_n": len(u32s),
                    "focus_in_70": f70,
                    "focus_in_88": f88,
                    "u32s_head": u32s[:8],
                }
            )
    return {
        "oi_lo": OI_LO,
        "oi_hi": OI_HI,
        "oi_inst_ok": oi_inst_ok,
        "oi_70_shaped": oi_70_shaped,
        "focus_70_ois": {str(k): v for k, v in sorted(focus_70_ois.items())},
        "focus_88_ois": {str(k): v for k, v in sorted(focus_88_ois.items())},
        "focus_oi_rows": oi_rows[:24],
        "prov_to_ois_focus_only": True,
        # keep full prov→oi only for path-needed; filled by caller
        "_prov_to_ois": prov_to_ois,
    }


def cross_paths(path_scan, oi_scan):
    prov_to_ois = oi_scan.get("_prov_to_ois") or {}
    army_hits = []
    dest_cover = defaultdict(list)
    for row in path_scan.get("rows") or []:
        covered = {}
        for pid in row.get("path_ids") or []:
            ois = prov_to_ois.get(pid) or []
            if ois:
                covered[str(pid)] = ois[:12]
                dest_cover[pid].append(row["index"])
        army_hits.append(
            {
                "index": row["index"],
                "path_ids": row["path_ids"],
                "dest_in_inst70": covered,
                "any_cover": bool(covered),
            }
        )
    covered_n = sum(1 for a in army_hits if a["any_cover"])
    return {
        "army_path_n": len(army_hits),
        "army_covered_n": covered_n,
        "army_hits": army_hits,
        "dest_cover_armies": {str(k): v for k, v in sorted(dest_cover.items())},
    }


def patch_docs(meta, result, path_scan, oi_scan, cross):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ht `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2hs `ARR88_CP_VT_CORRECT_HIT`",
        "2ht `MULTI_OI_INST70_PATH_HIT`",
        "2ht `MULTI_OI_INST70_PATH_PARTIAL`",
        "2ht `MULTI_OI_INST70_PATH_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    f70 = oi_scan.get("focus_70_ois") or {}
    t = re.sub(
        r"\| `INST7088` \| order/front maps \| Instance`\+0x70`/`\+0x88`[^\n]*\|\n",
        f"| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` — 2ht multi-oi "
        f"inst_ok={oi_scan.get('oi_inst_ok')} shaped70={oi_scan.get('oi_70_shaped')} "
        f"focus70={f70} path_covered={cross.get('army_covered_n')}/{cross.get('army_path_n')} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ht** | `{result}` | multi-oi Instant+0x70 × ITA PATH200 (corrected VTs) | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2ht** |" not in t and "| **2hs** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hs** |"):
                out.append(row)
        t = "".join(out)
    hits = "; ".join(
        f"idx={a['index']}→{a['dest_in_inst70']}"
        for a in (cross.get("army_hits") or [])
        if a.get("any_cover")
    )[:180] or "none"
    note = (
        f"**2ht multi-oi Inst70×PATH:** result=`{result}` · "
        f"oi_inst_ok={oi_scan.get('oi_inst_ok')} shaped70={oi_scan.get('oi_70_shaped')} · "
        f"focus70={f70} · path_armies={cross.get('army_path_n')} covered={cross.get('army_covered_n')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False. hits=[{hits}]\n"
    )
    if "**2ht multi-oi Inst70×PATH:**" not in t and "**2hs arr88 CP_VT correct:**" in t:
        idx = t.find("**2hs arr88 CP_VT correct:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hs · arr88 CP_VT correct · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ht · multi-oi Inst70×PATH · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hs — checklist polish (CLOSED)",
        "## Phase 2gj … 2ht — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ht | multi-oi Instant+0x70 × ITA PATH200 | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ht |" not in t2 and "| 2hs |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hs |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hs — arr88 CP_VT correct. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ht — multi-oi Inst70×PATH. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2ht — multi-oi Instant+0x70 × ITA PATH200\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Constants:** INST_VT=0x2A02558 · CP_VT=0x29EE248 id@+0xA4\n\n"
            f"**OG scan oi{OI_LO}..{OI_HI}:** inst_ok={oi_scan.get('oi_inst_ok')} · "
            f"shaped70={oi_scan.get('oi_70_shaped')}\n\n"
            f"**Focus in +0x70:** {f70}\n\n"
            f"**Focus in +0x88:** {oi_scan.get('focus_88_ois')}\n\n"
            f"**ITA PATH nonempty:** {path_scan.get('nonempty_n')} · "
            f"covered={cross.get('army_covered_n')}/{cross.get('army_path_n')}\n\n"
            f"**Army hits:** {json.dumps(cross.get('army_hits'), ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Perception: path dest ∈ Instant+0x70 ⇒ covering order_index. "
            f"Field name STUBBED. No invent. No Post / midflight / oi≠0 / endless Instant poll.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2ht · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ht",
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
    focus = set(FOCUS_PROVS)

    path_scan = scan_ita_paths(b, base, tag)
    oi_scan = scan_ois(b, base, focus)
    cross = cross_paths(path_scan, oi_scan)
    # strip internal map from persisted oi_scan
    oi_pub = {k: v for k, v in oi_scan.items() if not k.startswith("_")}

    covered = cross.get("army_covered_n") or 0
    f70 = oi_scan.get("focus_70_ois") or {}
    if covered >= 2 and f70:
        result = "MULTI_OI_INST70_PATH_HIT"
    elif covered >= 1 or f70:
        result = "MULTI_OI_INST70_PATH_PARTIAL"
    else:
        result = "MULTI_OI_INST70_PATH_EMPTY"

    report = {
        "phase": "2ht",
        "result": result,
        "allow_post": False,
        "live": meta,
        "path_scan": {"nonempty_n": path_scan["nonempty_n"], "rows": path_scan["rows"]},
        "oi_scan": oi_pub,
        "cross": cross,
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
            "plan-dense Assign oi≠0 (2ht multi-oi Inst70×PATH); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "multi-oi Instant+0x70 × PATH200 with corrected INST_VT/CP_VT; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ht",
                "result": result,
                "allow_post": False,
                "oi_inst_ok": oi_scan.get("oi_inst_ok"),
                "oi_70_shaped": oi_scan.get("oi_70_shaped"),
                "focus_70_ois": f70,
                "focus_88_ois": oi_scan.get("focus_88_ois"),
                "army_path_n": cross.get("army_path_n"),
                "army_covered_n": covered,
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
        patch_docs(meta, result, path_scan, oi_pub, cross)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2ht",
                "result": result,
                "allow_post": False,
                "live": meta,
                "oi_inst_ok": oi_scan.get("oi_inst_ok"),
                "oi_70_shaped": oi_scan.get("oi_70_shaped"),
                "focus_70_ois": f70,
                "focus_88_ois": oi_scan.get("focus_88_ois"),
                "army_path_n": cross.get("army_path_n"),
                "army_covered_n": covered,
                "army_hits": cross.get("army_hits"),
                "focus_oi_rows": oi_scan.get("focus_oi_rows"),
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
