#!/usr/bin/env python3
"""Phase 2iu: CONTINUOUS PATH200 focus740 + OG50 refresh 2671/2678 → OG+0x50 + 481 hub (RO).

Under clock CONTINUOUS, focus denser dig on Inst70∩ARR88 dest 740 + companions +
OG50 reverse refresh on 2671/2678 (oi1..2000); Instant only on 481;
cross dests vs OG481 Inst70/ARR88 (INST_VT=0x2A02558 CP_VT=0x29EE248) for
PATH×Inst drift honesty. Instant only on 481. No Instant map / hi-band
Instant-empty / 463 Inst70 / OG575 Instant-empty / Assign / midflight / Post;
never 5x; no speed write; OG+0x50 name STUBBED.
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

OUT = ROOT / "reports" / "phase2iu_path200_focus740_og50.json"
SUMMARY = ROOT / "reports" / "phase2iu_summary.json"
DOC = ROOT / "docs" / "PHASE2IU_PATH200_FOCUS740_OG50.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
CP_VT = 0x29EE248
CP_ID = 0xA4
CP_VT_FALSE = 0x29D3C68
REF_OI = 481
KNOWN = {
    481: "focus",
    575: "midband",
    962: "hiband",
    976: "hiband",
}
# DIG = mixed paths (Inst70 ∩ path AND outside70 ∩ path). Companions = path - Inst70.
FOCUS_PROVS = ()  # unused
DIG_FOCUS_SEED = (740, 489, 490, 1656, 3579)  # 2it Inst70∩ARR88 dest 740 + companions; OG50 refresh 2671/2678
DIG_LABEL = "focus740-og50-refresh"
TARGET_ARMIES = (2671, 2678)  # 2it tri70_88 no OG50 yet
ARMY_LO, ARMY_HI = 1, 3000
OI_LO, OI_HI = 1, 2000  # denser reverse for no-OG50 tri70_88
SHA_BASE = "9cd597f"


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
    # hours low + year@0x478 disagree with UI → reload class (do not treat as wrap)
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
            "ITA CONTINUOUS PATH200 focus denser 6867+2im-multi → OG+0x50 + 481 Inst70/ARR88 "
            "(2im new multi dests; Instant only on 481; PATH×Inst drift honesty; no Post; OG50 name STUBBED)"
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


def scan_path_armies(b, base, tag, dig_focus=None):
    focus = set(dig_focus) if dig_focus is not None else None
    ita_ok = empty_n = nonempty_n = multi_n = 0
    path_rows = []
    by_prov = defaultdict(list)
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
        if n > 1:
            multi_n += 1
        elif n == 1:
            nonempty_n += 1
        else:
            empty_n += 1
            continue
        inter = sorted(set(ids) & focus) if focus is not None else list(ids)
        path_rows.append(
            {
                "index": idx,
                "army": army,
                "path_n": n,
                "path_ids": ids,
                "focus_hit": inter,
            }
        )
        for pid in ids:
            by_prov[pid].append(idx)
    return {
        "ita_ok": ita_ok,
        "empty_n": empty_n,
        "nonempty_n": nonempty_n,
        "multi_n": multi_n,
        "path_rows": path_rows,
        "by_prov_head": {
            str(k): v[:8]
            for k, v in sorted(by_prov.items(), key=lambda kv: -len(kv[1]))[:16]
        },
    }


def reverse_og50(b, base, path_rows):
    """Map army ptr → list of oi that list it in OG+0x50. No Instant."""
    want = {}
    for r in path_rows:
        want[r["army"]] = r["index"]
        want[r["army"] + CA_MI_OFF] = r["index"]  # also match MI ptr form
    army_to_ois = defaultdict(list)
    oi_with_arr50 = 0
    oi_scanned = 0
    for oi in range(OI_LO, OI_HI + 1):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        oi_scanned += 1
        if not hdr:
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
        if not arr50 or arr50.get("in_image_sentinel"):
            continue
        ptrs = arr50.get("ptrs") or []
        if not ptrs:
            continue
        oi_with_arr50 += 1
        for p in ptrs:
            if not p or p < 0x10000:
                continue
            idx = want.get(p) or want.get(p - CA_MI_OFF)
            if idx is None:
                # walkback primary if MI
                mi_vt = try_u64(b, p)
                if mi_vt and (mi_vt - base) == CA_MI_VT:
                    primary = p - CA_MI_OFF
                    idx = want.get(primary)
            if idx is None:
                continue
            if oi not in army_to_ois[idx]:
                army_to_ois[idx].append(oi)
    return dict(army_to_ois), {"oi_scanned": oi_scanned, "oi_with_arr50": oi_with_arr50}


def classify_ois(ois):
    tags = []
    for oi in ois:
        tags.append({"oi": oi, "kind": KNOWN.get(oi, "other")})
    return tags


def patch_docs(meta, result, scan_pub, reverse_meta, hits_pub, new_ois):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2iu `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2it `PATH200_ARR88_9840_HIT`",
        "2it `PATH200_ARR88_9840_PARTIAL`",
        "2is `PATH200_FOCUS1053_1869_HIT`",
        "2is `PATH200_FOCUS1053_1869_PARTIAL`",
        "2ir `PATH200_DENSE_MIXED_PATHONLY_HIT`",
        "2ir `PATH200_DENSE_MIXED_PATHONLY_PARTIAL`",
        "2iq `PATH200_MIXED70_COMPANION_HIT`",
        "2iq `PATH200_MIXED70_COMPANION_PARTIAL`",
        "2iq `PATH200_MIXED70_COMPANION_PARTITION`",
        "2il `PATH200_MULTI_DENSE_HIT`",
        "2il `PATH200_MULTI_DENSE_PARTIAL`",
        "2im `PATH200_FOCUS4527_HIT`",
        "2im `PATH200_FOCUS4527_PARTIAL`",
        "2im `PATH200_FOCUS4527_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = (
        f"dig={scan_pub.get('dig_focus')} path_armies={scan_pub.get('path_army_n')} "
        f"hit={len([h for h in hits_pub if h.get('ois')])} cls={scan_pub.get('by_class_n')} "
        f"by_dig={scan_pub.get('by_dig_prov')} dests={scan_pub.get('focus_dest_union')} "
        f"cross70={scan_pub.get('cross70_focus')} cross88={scan_pub.get('cross88_focus')} "
        f"clock={meta.get('clock_class')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2iu PATH200 focus740/OG50 "
        f"{brief}; 2ii drift honesty path_only vs Inst70 (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2iu** | `{result}` | CONTINUOUS PATH200 {DIG_LABEL} → OG50+481 hub | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2iu** |" in t:
        t = re.sub(r"^\| \*\*2iu\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2it** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2it** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2iu PATH200 focus740/OG50:** result=`{result}` · {brief} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2iu PATH200 focus740/OG50:**" in t:
        t = re.sub(r"^\*\*2iu PATH200 focus740/OG50:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2it PATH200 ARR88×9840:**" in t:
        idx = t.find("**2it PATH200 ARR88×9840:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2it · PATH200 ARR88×9840 · 2026-10-31 Asia/Shanghai*",
        "*Phase 2iu · PATH200 focus740/OG50 · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2it — checklist polish (CLOSED)",
        "## Phase 2gj … 2iu — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2iu | CONTINUOUS PATH200 {DIG_LABEL} → OG50+481 hub | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2iu |" in t2:
        t2 = re.sub(r"^\| 2iu \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2it |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2it |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2it — PATH200 ARR88×9840. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2iu — PATH200 focus740/OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2iu — CONTINUOUS PATH200 focus {DIG_LABEL} denser → OG50 + 481 hub\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Clock:** {meta.get('clock_class')} · hours={meta.get('hours')} · "
            f"year@+0x478={meta.get('year_at_0x478')} · UI={meta.get('ui_date')}\n\n"
            f"**Scan:** {json.dumps(scan_pub, ensure_ascii=False)}\n\n"
            f"**Reverse:** {json.dumps(reverse_meta, ensure_ascii=False)}\n\n"
            f"**Hits (path army → ois):** {json.dumps(hits_pub, ensure_ascii=False)}\n\n"
            f"**New OIs (not in known 481/575/962/976):** {new_ois}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** CONTINUOUS PATH200 focus denser {DIG_LABEL} + OG+0x50 reverse + "
            f"481 Inst70/ARR88 honesty cross. Instant only on 481. "
            f"No Instant-empty re-dig. Field name STUBBED. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2iu · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2iu",
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
    # Pass 1: all nonempty PATH rows (no dig filter)
    scan = scan_path_armies(b, base, tag, None)
    path_rows_all = scan["path_rows"]
    multi_rows = [r for r in path_rows_all if (r.get("path_n") or 0) > 1]
    # Dig = MIXED paths: nonempty ∩Inst70 AND nonempty outside70 (= path - Inst70)
    all_path_dests = {p for r in path_rows_all for p in (r.get("path_ids") or [])}
    outside_all = sorted(all_path_dests - set70) if set70 else sorted(all_path_dests)
    dig_list = outside_all if outside_all else list(DIG_FOCUS_SEED)
    dig_set = set(dig_list)
    focus_seed = set(DIG_FOCUS_SEED)
    class_70_not_88 = (set70 - set88) if set70 else set()
    target_set = set(TARGET_ARMIES)
    focus_rows = []
    # Dig: paths hitting 740-class seed, OR target armies 2671/2678, OR mixed Inst70+outside
    for r in path_rows_all:
        ids = set(r.get("path_ids") or [])
        if not ids:
            continue
        in70 = ids & set70
        in88 = ids & set88
        outside = ids - set70
        hit_seed = bool(ids & focus_seed)
        hit_target = r.get("index") in target_set
        if in70 and outside:
            row_kind = "mixed"
        elif outside and not in70:
            row_kind = "path_only"
        elif in70 and not outside:
            row_kind = "pure_inst70"
        else:
            continue
        if not (hit_seed or hit_target or row_kind == "mixed"):
            continue
        r = dict(r)
        r["row_kind"] = row_kind
        r["focus_hit"] = sorted(ids & focus_seed) if hit_seed else sorted(ids)
        r["in70_path"] = sorted(in70)
        r["in88_path"] = sorted(in88)
        r["companion_outside"] = sorted(outside)
        r["in70_not88"] = sorted(ids & class_70_not_88)
        r["is_og50_target"] = hit_target
        focus_rows.append(r)
    dig_list = sorted(focus_seed | {p for r in focus_rows for p in (r.get("path_ids") or [])})
    path_rows = focus_rows
    # Partition all nonempty PATH armies for agent-facing honesty (one pass)
    part = {"pure_inst70": 0, "pure_outside70": 0, "mixed": 0, "other": 0}
    pure70_dests, pure_out_dests = set(), set()
    for r in path_rows_all:
        ids = set(r.get("path_ids") or [])
        if not ids:
            continue
        in70 = bool(ids & set70)
        out = bool(ids - set70)
        if in70 and out:
            part["mixed"] += 1
        elif in70:
            part["pure_inst70"] += 1
            pure70_dests |= ids
        elif out:
            part["pure_outside70"] += 1
            pure_out_dests |= ids
        else:
            part["other"] += 1
    partition_meta = {
        "counts": part,
        "pure_inst70_dest_union": sorted(pure70_dests),
        "pure_outside70_dest_union": sorted(pure_out_dests),
    }
    army_to_ois, reverse_meta = reverse_og50(b, base, path_rows)

    hits = []
    new_oi_set = set()
    known_hit_n = 0
    for r in path_rows:
        ois = sorted(army_to_ois.get(r["index"]) or [])
        kinds = classify_ois(ois)
        for k in kinds:
            if k["kind"] == "other":
                new_oi_set.add(k["oi"])
            else:
                known_hit_n += 1
        ids = r["path_ids"]
        in70 = sorted(set(ids) & set70)
        in88 = sorted(set(ids) & set88)
        if in70 and in88:
            cls = "tri70_88"
        elif in70:
            cls = "tri70"
        elif in88:
            cls = "hub88"
        else:
            cls = "path_only"
        hits.append(
            {
                "index": r["index"],
                "path_ids": ids,
                "focus_hit": r["focus_hit"],
                "companion_outside": r.get("companion_outside") or sorted(set(ids) - set70),
                "in70_path": r.get("in70_path") or in70,
                "in88_path": r.get("in88_path") or in88,
                "in70_not88": r.get("in70_not88") or sorted(set(ids) & (set70 - set88)),
                "row_kind": r.get("row_kind"),
                "is_og50_target": bool(r.get("is_og50_target")),
                "ois": ois,
                "kinds": kinds,
                "in70": in70,
                "in88": in88,
                "class": cls,
            }
        )

    hit_n = sum(1 for h in hits if h["ois"])
    path_army_n = len(path_rows)
    new_ois = sorted(new_oi_set)
    by_class_n = {}
    for h in hits:
        by_class_n[h["class"]] = by_class_n.get(h["class"], 0) + 1
    multi_dest_union = sorted({p for r in multi_rows for p in (r.get("path_ids") or [])})
    focus_dest_union = sorted({p for r in path_rows for p in (r.get("path_ids") or [])})
    by_dig = {str(d): [] for d in dig_list}
    for r in path_rows:
        for d in dig_list:
            if d in (r.get("path_ids") or []):
                by_dig[str(d)].append(r["index"])
    # compact by_dig: only provs with armies
    by_dig = {k: v for k, v in by_dig.items() if v}
    scan_pub = {
        "ita_ok": scan["ita_ok"],
        "empty_n": scan["empty_n"],
        "nonempty_n": scan["nonempty_n"],
        "multi_n": scan["multi_n"],
        "path_army_n": path_army_n,
        "dig_focus": dig_list,
        "dig_focus_n": len(dig_list),
        "dig_mode": "focus740_og50_refresh",
        "row_kind_n": {
            "mixed": sum(1 for r in path_rows if r.get("row_kind") == "mixed"),
            "path_only": sum(1 for r in path_rows if r.get("row_kind") == "path_only"),
        },
        "focus_dest_union": focus_dest_union,
        "multi_dest_union": multi_dest_union,
        "by_dig_prov": by_dig,
        "by_class_n": by_class_n,
        "cross70_focus": sorted(set(focus_dest_union) & set70),
        "cross88_focus": sorted(set(focus_dest_union) & set88),
        "outside70_dest_n": len(dig_list),
        "inst70_n": len(set70),
        "companion_union": sorted({p for h in hits for p in (h.get("companion_outside") or [])}),
        "in70_path_union": sorted({p for h in hits for p in (h.get("in70_path") or h.get("in70") or [])}),
        "partition": partition_meta,
        "by_prov_head": scan["by_prov_head"],
        "hub": {k: v for k, v in (hub_meta or {}).items() if k != "u32s_head" or True},
    }
    hits_pub = hits  # all path armies (usually small)

    path_only_n = by_class_n.get("path_only", 0)
    tri_n = by_class_n.get("tri70_88", 0) + by_class_n.get("tri70", 0)
    hub88_n = by_class_n.get("hub88", 0)
    pure70_n = partition_meta["counts"].get("pure_inst70", 0)
    pure_out_n = partition_meta["counts"].get("pure_outside70", 0)
    seed_hit_n = sum(1 for h in hits if h.get("ois") and set(h.get("path_ids") or []) & set(DIG_FOCUS_SEED))
    # OG50 refresh on 2it no-OG50 targets 2671/2678 (wider oi1..2000)
    og50_refresh = []
    for tid in TARGET_ARMIES:
        hmatch = next((h for h in hits if h.get("index") == tid), None)
        ois = (hmatch or {}).get("ois") or army_to_ois.get(tid) or []
        og50_refresh.append({
            "index": tid,
            "present": hmatch is not None,
            "path_ids": (hmatch or {}).get("path_ids"),
            "ois": ois,
            "class": (hmatch or {}).get("class"),
            "gained_og50": bool(ois),
        })
    all_dests = {p for r in path_rows_all for p in (r.get("path_ids") or [])}
    arr88_xpath = {
        "in70_and_88": sorted(all_dests & set70 & set88),
        "in70_not_88": sorted((all_dests & set70) - set88),
        "in88_not_70": sorted((all_dests & set88) - set70),
        "outside70_outside88": sorted(all_dests - set70 - set88),
    }
    scan_pub["arr88_xpath"] = arr88_xpath
    scan_pub["class_70_not_88_n"] = len(class_70_not_88)
    scan_pub["og50_refresh"] = og50_refresh
    scan_pub["oi_hi"] = OI_HI
    target_gained = sum(1 for x in og50_refresh if x.get("gained_og50"))
    # HIT: 740-seed with OG50, or target gained OG50, or denser tri70_88
    if seed_hit_n >= 1 or target_gained >= 1 or (hit_n >= 1 and tri_n >= 1):
        result = "PATH200_FOCUS740_OG50_HIT"
    elif path_army_n >= 1 and hit_n >= 1:
        result = "PATH200_FOCUS740_OG50_PARTIAL"
    elif pure70_n >= 1 or pure_out_n >= 1:
        result = "PATH200_FOCUS740_OG50_PARTITION"
    else:
        result = "PATH200_FOCUS740_OG50_EMPTY"

    report = {
        "phase": "2iu",
        "result": result,
        "allow_post": False,
        "live": meta,
        "scan": scan_pub,
        "hub": hub_meta,
        "reverse": reverse_meta,
        "hits": hits_pub,
        "new_ois": new_ois,
        "hit_n": hit_n,
        "known_kind_sightings": known_hit_n,
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
            "plan-dense Assign oi≠0 (2iu PATH200 focus740/OG50); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "CONTINUOUS PATH200 focus denser 6867+2im-multi → OG+0x50 + 481 Inst70/ARR88; "
            "2il new dests; PATH×Inst drift honesty; Instant only on 481; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2iu",
                "result": result,
                "allow_post": False,
                "path_army_n": path_army_n,
                "hit_n": hit_n,
                "new_ois": new_ois,
                "hits_head": hits_pub[:24],
                "reverse": reverse_meta,
                "scan": {
                    "ita_ok": scan_pub["ita_ok"],
                    "nonempty_n": scan_pub["nonempty_n"],
                    "multi_n": scan_pub["multi_n"],
                },
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
        patch_docs(meta, result, scan_pub, reverse_meta, hits_pub[:32], new_ois)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2iu",
                "result": result,
                "allow_post": False,
                "live": meta,
                "scan": scan_pub,
                "reverse": reverse_meta,
                "hit_n": hit_n,
                "path_army_n": path_army_n,
                "multi_n": scan_pub.get("multi_n"),
                "by_class_n": scan_pub.get("by_class_n"),
                "dig_focus": scan_pub.get("dig_focus"),
                "by_dig_prov": scan_pub.get("by_dig_prov"),
                "focus_dest_union": scan_pub.get("focus_dest_union"),
                "multi_dest_union": scan_pub.get("multi_dest_union"),
                "new_ois": new_ois,
                "hits_head": hits_pub[:24],
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
