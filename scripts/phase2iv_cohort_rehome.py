#!/usr/bin/env python3
"""Phase 2iv: re-home the 2iu focus-740 cohort after oi recycle (RO).

2iu (hours≈222) put 1042/2649/2671 on oi=1410 and 461 on oi=481. Seven game
hours later those order indices are gone. This slice checks the cohort handles,
scans oi 1..2000 once, and digs whatever live order group still owns them.
One-shot. No Post, no speed write, never 5x, no midflight poll. OG+0x50 name
stays STUBBED.
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

OUT = ROOT / "reports" / "phase2iv_cohort_rehome.json"
SUMMARY = ROOT / "reports" / "phase2iv_summary.json"
DOC = ROOT / "docs" / "PHASE2IV_COHORT_REHOME.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
FOCUS_OI = 1410  # 2iu home; expected stale
REF_OI = 481
COHORT = (461, 1042, 2647, 2649, 2671)  # 2iu focus-740 armies
STALE_OIS = (481, 575, 962, 976, 1410)
EXPECT_PROV = 740
OI_LO, OI_HI = 1, 2000
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
CP_VT = 0x29EE248
CP_ID = 0xA4
CP_VT_FALSE = 0x29D3C68
ARMY_LO, ARMY_HI = 1, 3000
SHA_BASE = "ef16ccf"


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
            "ITA OG1410 dig Inst70+ARR88+OG50+PATH "
            "(2iu new oi; no Post; OG50 name STUBBED; no midflight)"
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


def read_cpdx_ptrs(b, base, arr_addr, max_n=96):
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


def build_ptr_index(b, base):
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
    return ptr_to_idx


def decode_arr88(b, base, inst):
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
    return {
        "set88": set88,
        "arr88_size": arr88_size,
        "arr88_sentinel": arr88_sentinel,
        "arr88_kinds": kinds,
        "arr88_ids_n": len(set88),
        "arr88_ids_head": ids_head,
    }


def dig_oi(b, base, tag, oi, ptr_to_idx):
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        return {"oi": oi, "ok": False, "error": "resolve_fail"}
    if not hdr:
        return {"oi": oi, "ok": False, "error": "null_hdr"}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    inst_ok = False
    set70 = set()
    arr70_n = 0
    u32s_head = []
    inst_vt_rva = None
    arr88 = {
        "arr88_size": 0,
        "arr88_sentinel": False,
        "arr88_kinds": {},
        "arr88_ids_n": 0,
        "arr88_ids_head": [],
        "set88": set(),
    }
    if ptrs:
        inst = ptrs[0]
        vt = try_u64(b, inst)
        if vt:
            inst_vt_rva = vt - base
        inst_ok = bool(vt and (vt - base) == INST_VT)
        if inst_ok:
            a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
            if a70 and not a70.get("in_image_sentinel"):
                u32s = a70.get("u32s") or []
                if u32s and all(looks_like_province(v) for v in u32s):
                    set70 = set(u32s)
                    arr70_n = len(u32s)
                    u32s_head = u32s[:12]
            arr88 = decode_arr88(b, base, inst)

    set88 = arr88.get("set88") or set()
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 64)
    members = []
    walk_ok = 0
    expect_found = []
    for p in (arr50 or {}).get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        primary = p - CA_MI_OFF
        avt = try_u64(b, primary)
        mi_vt = try_u64(b, p)
        ok = bool(
            avt and (avt - base) == CA_VT_RVA and mi_vt and (mi_vt - base) == CA_MI_VT
        )
        if ok:
            walk_ok += 1
        atag = try_u32(b, primary + CA_TAG) if ok else None
        idx = ptr_to_idx.get(primary)
        path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
        pids = path.get("province_ids") or []
        if idx in COHORT:
            expect_found.append(idx)
        dest_in_70 = sorted(set(pids) & set70)
        dest_in_88 = sorted(set(pids) & set88)
        members.append(
            {
                "index": idx,
                "tag": atag,
                "ita": atag == tag if atag is not None else False,
                "walkback_ok": ok,
                "path_ids": pids if ok else [],
                "path_n": path.get("n") if ok else 0,
                "dest_in_70": dest_in_70,
                "dest_in_88": dest_in_88,
                "triangle70": bool(ok and dest_in_70),
                "triangle88": bool(ok and dest_in_88),
                "expect_prov": EXPECT_PROV in pids if ok else False,
            }
        )
    return {
        "oi": oi,
        "ok": True,
        "inst_ok": inst_ok,
        "inst_vt_rva": hex(inst_vt_rva) if inst_vt_rva is not None else None,
        "arr98_size": (arr98 or {}).get("size"),
        "arr70_n": arr70_n,
        "u32s_head": u32s_head,
        "arr88_size": arr88.get("arr88_size"),
        "arr88_sentinel": arr88.get("arr88_sentinel"),
        "arr88_kinds": arr88.get("arr88_kinds"),
        "arr88_ids_n": arr88.get("arr88_ids_n"),
        "arr88_ids_head": arr88.get("arr88_ids_head"),
        "og50_size": (arr50 or {}).get("size") or 0,
        "walk_ok": walk_ok,
        "expect_idxs": list(COHORT),
        "expect_found": sorted(set(expect_found)),
        "expect_prov": EXPECT_PROV,
        "expect_prov_n": sum(1 for m in members if m.get("expect_prov")),
        "members": members,
        "set70": set70,
        "set88": set88,
        "triangle70_n": sum(1 for m in members if m.get("triangle70")),
        "triangle88_n": sum(1 for m in members if m.get("triangle88")),
        "ita_n": sum(1 for m in members if m.get("ita")),
        "path_mem_n": sum(1 for m in members if (m.get("path_n") or 0) > 0),
    }


def dig_ref70(b, base):
    try:
        hdr = resolve_handle(b, TYPE_OG, REF_OI, base)
    except Exception:
        return set(), {"ok": False}
    if not hdr:
        return set(), {"ok": False}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    if not ptrs:
        return set(), {"ok": False, "reason": "no_inst_ptrs"}
    inst = ptrs[0]
    vt = try_u64(b, inst)
    if not vt or (vt - base) != INST_VT:
        return set(), {"ok": False, "inst_ok": False, "inst_vt_rva": hex(vt - base) if vt else None}
    a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
    if not a70 or a70.get("in_image_sentinel"):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    u32s = a70.get("u32s") or []
    if not u32s or not all(looks_like_province(v) for v in u32s):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    return set(u32s), {
        "ok": True,
        "inst_ok": True,
        "arr70_n": len(u32s),
        "u32s_head": u32s[:12],
    }


def patch_docs(meta, result, dig_pub, cross):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2iv `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    t2, n = re.subn(
        r"\*\*Next shortest NON-Post:\*\* human midflight CMove hex / SAFE Post for ring_embed OR later "
        r"Assign oi≠0 \([^)]+\); retry GitHub push when reachable\. Still \*\*NO ALLOW_POST\*\*\.",
        repl,
        t,
        count=1,
    )
    t = t2 if n else t
    brief = dig_pub.get("cohort_brief") or (
        f"oi{dig_pub.get('oi')} size={dig_pub.get('og50_size')} walk={dig_pub.get('walk_ok')} "
        f"arr70={dig_pub.get('arr70_n')} arr88={dig_pub.get('arr88_ids_n')} "
        f"clock={meta.get('clock_class')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2iv cohort rehome "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2iv** | `{result}` | 2iu focus-740 cohort rehome after oi recycle | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2iv** |" in t:
        t = re.sub(r"^\| \*\*2iv\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2iu** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2iu** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2iv cohort rehome:** result=`{result}` · {brief} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2iv cohort rehome:**" in t:
        t = re.sub(r"^\*\*2iv cohort rehome:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2iv OG1410 dig:**" in t:
        t = re.sub(r"^\*\*2iv OG1410 dig:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2iu PATH200 focus740/OG50:**" in t:
        idx = t.find("**2iu PATH200 focus740/OG50:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2iu · PATH200 focus740/OG50 · 2026-10-31 Asia/Shanghai*",
        "*Phase 2iv · cohort rehome · 2026-11-01 Asia/Shanghai*",
    )
    t = t.replace(
        "*Phase 2iv · OG1410 dig · 2026-11-01 Asia/Shanghai*",
        "*Phase 2iv · cohort rehome · 2026-11-01 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    s = safe.read_text(encoding="utf-8")
    s = s.replace(
        "## Phase 2gj … 2iu — checklist polish (CLOSED)",
        "## Phase 2gj … 2iv — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2iv | 2iu focus-740 cohort rehome after oi recycle | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2iv |" in s:
        s = re.sub(r"^\| 2iv \|.*\n", row2, s, count=1, flags=re.M)
    elif "| 2iu |" in s:
        lines = s.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2iu |"):
                out.append(row2)
        s = "".join(out)
    s = s.replace(
        "*Phase 2iu — PATH200 focus740/OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2iv — cohort rehome. Gate stays CLOSED. 2026-11-01 Asia/Shanghai*",
    )
    s = s.replace(
        "*Phase 2iv — OG1410 dig. Gate stays CLOSED. 2026-11-01 Asia/Shanghai*",
        "*Phase 2iv — cohort rehome. Gate stays CLOSED. 2026-11-01 Asia/Shanghai*",
    )
    safe.write_text(s, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2iv — 2iu cohort rehome\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Clock:** {meta.get('clock_class')} · hours={meta.get('hours')} · "
            f"year@+0x478={meta.get('year_at_0x478')} · UI={meta.get('ui_date')}\n\n"
            f"**Cohort:** {dig_pub.get('cohort_brief')}\n\n"
            f"**Stale OIs:** {dig_pub.get('stale_ois')}\n\n"
            f"**Primary dig:** {json.dumps(dig_pub.get('primary_pub'), ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** 2iu oi=1410/481 did not survive ~7 game hours. Re-home is the live "
            f"order index that still lists a cohort army. Field name STUBBED. No invent. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2iv · 2026-11-01 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def cohort_rows(b, base, tag):
    rows = []
    want = {}
    for idx in COHORT:
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            army = None
        if not army:
            rows.append({"index": idx, "alive": False})
            continue
        vt = try_u64(b, army)
        ok = bool(vt and (vt - base) == CA_VT_RVA)
        path = path60(b, base, army, tag) if ok else {"n": 0, "province_ids": []}
        mi = army + CA_MI_OFF
        rows.append(
            {
                "index": idx,
                "alive": ok,
                "path_ids": path.get("province_ids") or [],
                "has_expect_prov": EXPECT_PROV in (path.get("province_ids") or []),
            }
        )
        if ok:
            want[mi] = idx
            want[army] = idx
    return rows, want


def reverse_ois(b, base, want):
    found = {idx: [] for idx in COHORT}
    bands = {"1-499": 0, "500-999": 0, "1000-1499": 0, "1500-2000": 0}
    for oi in range(OI_LO, OI_HI + 1):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            hdr = None
        if not hdr:
            continue
        if oi < 500:
            bands["1-499"] += 1
        elif oi < 1000:
            bands["500-999"] += 1
        elif oi < 1500:
            bands["1000-1499"] += 1
        else:
            bands["1500-2000"] += 1
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 64)
        for p in (arr50 or {}).get("ptrs") or []:
            idx = want.get(p) or want.get((p - CA_MI_OFF) if p else 0)
            if idx and oi not in found[idx]:
                found[idx].append(oi)
    return found, bands


def stale_oi_map(b, base):
    out = {}
    for oi in STALE_OIS:
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            hdr = None
        out[str(oi)] = bool(hdr)
    return out


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2iv",
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
    meta["scenario"] = (
        "ITA 2iu focus-740 cohort rehome (oi 1..2000 once; dig live owner; no Post)"
    )

    rows, want = cohort_rows(b, base, tag)
    found, bands = reverse_ois(b, base, want)
    stale = stale_oi_map(b, base)
    for row in rows:
        row["ois"] = found.get(row["index"], [])

    owner_ois = sorted({oi for ois in found.values() for oi in ois})
    ptr_to_idx = build_ptr_index(b, base) if owner_ois else {}
    digs = []
    for oi in owner_ois:
        dig = dig_oi(b, base, tag, oi, ptr_to_idx)
        digs.append({k: v for k, v in dig.items() if k not in ("set70", "set88")})

    alive = [r for r in rows if r.get("alive")]
    homed = [r for r in alive if r.get("ois")]
    primary = digs[0] if digs else None
    primary_pub = None
    if primary:
        primary_pub = {
            "oi": primary.get("oi"),
            "inst_ok": primary.get("inst_ok"),
            "inst_vt_rva": primary.get("inst_vt_rva"),
            "og50_size": primary.get("og50_size"),
            "walk_ok": primary.get("walk_ok"),
            "arr70_n": primary.get("arr70_n"),
            "u32s_head": primary.get("u32s_head"),
            "arr88_ids_n": primary.get("arr88_ids_n"),
            "arr88_ids_head": primary.get("arr88_ids_head"),
            "ita_n": primary.get("ita_n"),
            "path_mem_n": primary.get("path_mem_n"),
            "triangle70_n": primary.get("triangle70_n"),
            "cohort_members": [
                {
                    "index": m.get("index"),
                    "path_ids": m.get("path_ids"),
                    "dest_in_70": m.get("dest_in_70"),
                }
                for m in (primary.get("members") or [])
                if m.get("index") in COHORT or (m.get("path_n") or 0) > 0
            ][:12],
        }

    if homed and primary and primary.get("ok") and (primary.get("walk_ok") or 0) >= 1:
        result = "COHORT_REHOME_HIT"
    elif alive:
        result = "COHORT_REHOME_PARTIAL"
    else:
        result = "COHORT_REHOME_EMPTY"

    cohort_brief = (
        f"alive={[r['index'] for r in alive]} homed={ {r['index']: r['ois'] for r in rows} } "
        f"stale_alive={[int(k) for k, v in stale.items() if v]} "
        f"bands={bands} primary_oi={(primary or {}).get('oi')} "
        f"clock={meta.get('clock_class')}"
    )
    dig_pub = {
        "cohort_brief": cohort_brief,
        "stale_ois": stale,
        "primary_pub": primary_pub,
        "oi": (primary or {}).get("oi"),
    }
    cross = {"owner_ois": owner_ois, "bands": bands}

    report = {
        "phase": "2iv",
        "result": result,
        "allow_post": False,
        "live": meta,
        "cohort": rows,
        "stale_ois": stale,
        "oi_bands": bands,
        "digs": digs,
        "sha_base": SHA_BASE,
        "hard_deny": [
            "ALLOW_POST",
            "Post inject",
            "5x",
            "speed write",
            "long midflight empty poll",
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed; "
            "2iu oi map is stale after a few game hours; still NO ALLOW_POST"
        ),
        "semantics": (
            "2iu focus-740 cohort re-homed on live oi 1..2000; old 1410/481 may be gone; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2iv",
                "result": result,
                "allow_post": False,
                "cohort": [
                    {"index": r["index"], "alive": r.get("alive"), "ois": r.get("ois"), "path_ids": r.get("path_ids")}
                    for r in rows
                ],
                "stale_ois": stale,
                "oi_bands": bands,
                "primary": primary_pub,
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "clock_class": meta.get("clock_class"),
                    "drain": meta.get("drain"),
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
        patch_docs(meta, result, dig_pub, cross)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("doc_patch_error", e)

    print(
        json.dumps(
            {
                "phase": "2iv",
                "result": result,
                "allow_post": False,
                "cohort": SUMMARY and json.loads(SUMMARY.read_text(encoding="utf-8"))["cohort"],
                "stale_ois": stale,
                "oi_bands": bands,
                "primary": primary_pub,
                "live": {
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "drain": meta.get("drain"),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


