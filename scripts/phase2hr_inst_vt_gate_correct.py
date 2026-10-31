#!/usr/bin/env python3
"""Phase 2hr: correct INST_VT false gate; oi=481 Instant×PATH one-shot (RO).

2hq dumped oi=481 +0x98[0] VT=0x2a02558; scripts 2hp/2hq/2gm used INST_VT=
0x2A84A38 → false inst_vt_ok=False. Catalog (2fu/2fv) + older scripts already
use 0x2A02558 = COrderInstance. This slice: PE RTTI demangle both RVAs + live
one-shot dig with CORRECT VT (not endless Instant map poll). No Post; never 5x;
no speed write; no field invent; no midflight; no Assign oi≠0.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from msvc_rtti import demangle_simple
from pe import PE
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hr_inst_vt_gate_correct.json"
SUMMARY = ROOT / "reports" / "phase2hr_summary.json"
DOC = ROOT / "docs" / "PHASE2HR_INST_VT_GATE_CORRECT.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT_CORRECT = 0x2A02558
INST_VT_FALSE = 0x2A84A38
CP_VT = 0x29D3C68
CP_PROVINCE_ID = 0x18
FOCUS_OI = 481
FOCUS_PROVS = (3816, 3938, 915)
SHA_BASE = "31ace87"


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
            "ITA oi=481 INST_VT gate correct 0x2A02558 + Instant×PATH one-shot "
            "(no Post, no midflight, no oi≠0, no endless Instant poll)"
        ),
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def rtti_name_at_vtable(pe: PE, vt_rva: int) -> dict:
    out = {"vtable_rva": hex(vt_rva)}
    off = pe.rva_to_off(vt_rva - 8)
    if off is None:
        out["error"] = "vt-8 not in PE image"
        return out
    col_va = struct.unpack_from("<Q", pe.data, off)[0]
    col_rva = col_va - pe.image_base
    out["col_rva"] = hex(col_rva & 0xFFFFFFFFFFFFFFFF)
    if col_rva < 0 or col_rva > 0x10000000:
        out["error"] = "col_rva out of range"
        return out
    coff = pe.rva_to_off(col_rva)
    if coff is None:
        out["error"] = "COL RVA not mapped"
        return out
    sig, _off_field, _cd, td_rva = struct.unpack_from("<IIII", pe.data, coff)
    out["col_sig"] = sig
    out["td_rva"] = hex(td_rva)
    if sig not in (0, 1):
        out["error"] = f"COL signature {sig} not MSVC RTTI"
        return out
    td_off = pe.rva_to_off(td_rva)
    if td_off is None:
        out["error"] = "TD RVA not mapped"
        return out
    name10 = pe.data[td_off + 0x10 : td_off + 0x10 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    name14 = pe.data[td_off + 0x14 : td_off + 0x14 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    pick = name10 if name10.startswith(".?A") else (name14 if name14.startswith(".?A") else name10)
    out["name_raw"] = pick
    out["demangled"] = demangle_simple(pick) if pick else None
    out["ok"] = bool(pick and pick.startswith(".?A"))
    return out


def pe_demangle_pair(image_path: str) -> dict:
    out = {"image_path": image_path}
    if not image_path or not Path(image_path).is_file():
        out["error"] = "no_image_path"
        return out
    try:
        pe = PE(image_path)
    except Exception as e:
        out["error"] = f"PE open: {e}"
        return out
    out["correct"] = rtti_name_at_vtable(pe, INST_VT_CORRECT)
    out["false_gate"] = rtti_name_at_vtable(pe, INST_VT_FALSE)
    out["ok"] = True
    return out


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
    n = min(size, max_n)
    blob = try_read(b, data, n * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    ptrs = [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(n)]
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs, "data": hex(data)}


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
    u32s = [struct.unpack_from("<I", blob, j * 4)[0] for j in range(n)]
    return {"size": size, "in_image_sentinel": False, "u32s": u32s, "data": hex(data)}


def dig_oi481_corrected(b, base, tag):
    try:
        hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    except Exception:
        hdr = None
    if not hdr:
        return {"ok": False, "reason": "og_unresolved"}
    og = hdr + 0x10
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 8)
    ptrs = (arr98 or {}).get("ptrs") or []
    inst = ptrs[0] if ptrs else None
    live_rva = None
    if inst:
        ivt = try_u64(b, inst)
        live_rva = (ivt - base) if ivt else None
    gate_false = bool(live_rva is not None and live_rva == INST_VT_FALSE)
    gate_correct = bool(live_rva is not None and live_rva == INST_VT_CORRECT)

    members = []
    path_union = set()
    if arr50 and not arr50.get("in_image_sentinel"):
        for p in arr50.get("ptrs") or []:
            if not p:
                continue
            primary = p - CA_MI_OFF
            vt = try_u64(b, primary)
            ok = bool(vt and (vt - base) == CA_VT_RVA)
            atag = try_u32(b, primary + CA_TAG) if ok else None
            path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
            if ok and atag == tag and path.get("province_ids"):
                path_union.update(path["province_ids"])
            members.append(
                {
                    "mi": hex(p),
                    "walkback_ok": ok,
                    "tag": atag,
                    "ita": atag == tag,
                    "path_ids": path.get("province_ids") if ok else [],
                    "path_n": path.get("n") if ok else 0,
                }
            )

    arr70 = None
    arr70_shaped = False
    arr88_ids = None
    arr88_kinds = {}
    if inst and gate_correct:
        a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
        if a70 and not a70.get("in_image_sentinel"):
            u32s = a70.get("u32s") or []
            arr70_shaped = bool(u32s) and all(looks_like_province(v) for v in u32s)
            arr70 = {"size": a70.get("size"), "shaped": arr70_shaped, "u32s": u32s[:32]}
        a88 = read_cpdx_ptrs(b, base, inst + 0x88, 32)
        if a88 and not a88.get("in_image_sentinel"):
            ids = []
            kinds = {"CProvince": 0, "CArmy": 0, "COrderInstance": 0, "other": 0, "nullish": 0}
            for p in a88.get("ptrs") or []:
                if not p or p < 0x10000:
                    kinds["nullish"] += 1
                    continue
                vr = try_u64(b, p)
                if not vr:
                    kinds["other"] += 1
                    continue
                rva = vr - base
                if rva == CP_VT:
                    kinds["CProvince"] += 1
                    pid = try_u32(b, p + CP_PROVINCE_ID)
                    if pid is not None:
                        ids.append(pid)
                elif rva == CA_VT_RVA:
                    kinds["CArmy"] += 1
                elif rva == INST_VT_CORRECT:
                    kinds["COrderInstance"] += 1
                else:
                    kinds["other"] += 1
            arr88_ids = ids[:32]
            arr88_kinds = kinds

    set70 = set((arr70 or {}).get("u32s") or []) if arr70_shaped else set()
    set88 = set(arr88_ids or [])
    focus = set(FOCUS_PROVS)
    cross70 = sorted(path_union & set70)
    cross88 = sorted(path_union & set88)
    focus70 = sorted(focus & set70)
    focus88 = sorted(focus & set88)
    return {
        "ok": True,
        "oi": FOCUS_OI,
        "hdr": hex(hdr),
        "og": hex(og),
        "arr50_size": (arr50 or {}).get("size"),
        "member_n": len(members),
        "ita_members": sum(1 for m in members if m.get("ita")),
        "path_union_ita": sorted(path_union),
        "inst": hex(inst) if inst else None,
        "live_vt_rva": hex(live_rva) if live_rva is not None else None,
        "matches_false_gate_0x2A84A38": gate_false,
        "matches_correct_0x2A02558": gate_correct,
        "arr70": arr70,
        "arr88_province_ids": arr88_ids,
        "arr88_kinds": arr88_kinds,
        "cross70": cross70,
        "cross88": cross88,
        "cross70_n": len(cross70),
        "cross88_n": len(cross88),
        "focus_in_70": focus70,
        "focus_in_88": focus88,
        "false_scripts_noted": [
            "phase2hp_og481_instance_path_cross.py",
            "phase2hq_path200_focus_prov_matrix.py",
            "phase2gm_carmy_path_instance_ro.py",
        ],
        "correct_scripts_noted": [
            "phase2fv_instance_fields.py / docs",
            "phase2fu_og_internals.md",
            "phase2fx_70_88_structure.py",
            "phase2fy_army_path_vs_70.py",
            "phase2fz / phase2ga",
        ],
    }


def patch_docs(meta, result, dig, pe_info):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hr `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2hq `PATH200_FOCUS_PROV_HIT`",
        "2hr `INST_VT_GATE_CORRECT_CROSS_HIT`",
        "2hr `INST_VT_GATE_CORRECT_CROSS_PARTIAL`",
        "2hr `INST_VT_GATE_CORRECT_VT_ONLY`",
        "2hr `INST_VT_GATE_CORRECT_MISS`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    c70 = dig.get("cross70_n", 0) if dig.get("ok") else 0
    c88 = dig.get("cross88_n", 0) if dig.get("ok") else 0
    t = re.sub(
        r"\| `INST7088` \| order/front maps \| Instance`\+0x70`/`\+0x88`[^\n]*\|\n",
        f"| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` — 2hr oi=481 "
        f"VT=0x2A02558 gate_ok cross70={c70} cross88={c88} (⊀ named dest) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hr** | `{result}` | INST_VT false-gate fix 0x2A84A38→0x2A02558; oi=481 Instant×PATH | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hr** |" not in t and "| **2hq** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hq** |"):
                out.append(row)
        t = "".join(out)
    dem_c = ((pe_info or {}).get("correct") or {}).get("demangled")
    dem_f = ((pe_info or {}).get("false_gate") or {}).get("demangled")
    note = (
        f"**2hr INST_VT gate correct:** result=`{result}` · live_vt={dig.get('live_vt_rva')} · "
        f"correct_demangle={dem_c} · false_demangle={dem_f} · "
        f"cross70={c70} cross88={c88} focus70={dig.get('focus_in_70')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hr INST_VT gate correct:**" not in t and "**2hq PATH200 focus-prov denser:**" in t:
        idx = t.find("**2hq PATH200 focus-prov denser:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hq · PATH200 focus-prov denser · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hr · INST_VT gate correct · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hq — checklist polish (CLOSED)",
        "## Phase 2gj … 2hr — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hr | INST_VT false-gate fix + oi=481 Instant×PATH | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hr |" not in t2 and "| 2hq |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hq |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hq — PATH200 focus-prov denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hr — INST_VT gate correct. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hr — INST_VT false-gate correction\n\n"
            f"**Result:** `{result}`\n\n"
            f"**False gate:** scripts used `INST_VT=0x2A84A38` (2hp/2hq/2gm) → `inst_vt_ok=False` "
            f"despite live VT `0x2a02558`.\n\n"
            f"**Correct:** `INST_VT=0x2A02558` (2fu/2fv/2fx/2fy/2fz/2ga) = COrderInstance.\n\n"
            f"**PE demangle:** correct→`{dem_c}` · false→`{dem_f}`\n\n"
            f"**Live oi=481:** vt={dig.get('live_vt_rva')} · matches_correct="
            f"{dig.get('matches_correct_0x2A02558')} · "
            f"cross70={c70} cross88={c88} · path_union={dig.get('path_union_ita')} · "
            f"focus_in_70={dig.get('focus_in_70')} focus_in_88={dig.get('focus_in_88')}\n\n"
            f"**arr70:** {json.dumps(dig.get('arr70'), ensure_ascii=False)}\n\n"
            f"**arr88 kinds:** {dig.get('arr88_kinds')} · ids={dig.get('arr88_province_ids')}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** One-shot gate correction + Instant×PATH; not endless Instant poll. "
            f"Field name STUBBED. No invent. No Post / midflight / oi≠0.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hr · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hr",
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
    image_path = getattr(b, "image_path", "") or ""
    pe_info = pe_demangle_pair(image_path)
    dig = dig_oi481_corrected(b, base, tag)

    c70 = dig.get("cross70_n", 0) if dig.get("ok") else 0
    c88 = dig.get("cross88_n", 0) if dig.get("ok") else 0
    gate_ok = bool(dig.get("matches_correct_0x2A02558"))
    dem_ok = bool(((pe_info or {}).get("correct") or {}).get("demangled"))
    if gate_ok and (c70 > 0 or c88 > 0):
        result = "INST_VT_GATE_CORRECT_CROSS_HIT"
    elif gate_ok and dig.get("arr70") is not None:
        result = "INST_VT_GATE_CORRECT_CROSS_PARTIAL"
    elif gate_ok or dem_ok:
        result = "INST_VT_GATE_CORRECT_VT_ONLY"
    else:
        result = "INST_VT_GATE_CORRECT_MISS"

    report = {
        "phase": "2hr",
        "result": result,
        "allow_post": False,
        "live": meta,
        "pe_demangle": pe_info,
        "dig": dig,
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
            "plan-dense Assign oi≠0 (2hr INST_VT gate corrected); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "INST_VT false-gate 0x2A84A38→0x2A02558; oi=481 Instant×PATH one-shot; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hr",
                "result": result,
                "allow_post": False,
                "live_vt_rva": dig.get("live_vt_rva"),
                "matches_correct": dig.get("matches_correct_0x2A02558"),
                "cross70_n": c70,
                "cross88_n": c88,
                "focus_in_70": dig.get("focus_in_70"),
                "pe_correct_demangle": ((pe_info or {}).get("correct") or {}).get("demangled"),
                "pe_false_demangle": ((pe_info or {}).get("false_gate") or {}).get("demangled"),
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
        patch_docs(meta, result, dig, pe_info)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hr",
                "result": result,
                "allow_post": False,
                "live": meta,
                "live_vt_rva": dig.get("live_vt_rva"),
                "matches_correct": dig.get("matches_correct_0x2A02558"),
                "matches_false": dig.get("matches_false_gate_0x2A84A38"),
                "cross70": dig.get("cross70"),
                "cross88": dig.get("cross88"),
                "focus_in_70": dig.get("focus_in_70"),
                "focus_in_88": dig.get("focus_in_88"),
                "arr70": dig.get("arr70"),
                "arr88_kinds": dig.get("arr88_kinds"),
                "arr88_ids": dig.get("arr88_province_ids"),
                "path_union_ita": dig.get("path_union_ita"),
                "pe_correct": (pe_info or {}).get("correct"),
                "pe_false": (pe_info or {}).get("false_gate"),
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
