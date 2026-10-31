#!/usr/bin/env python3
"""Phase 2hs: Instant+0x88 CP_VT false-gate fix; oi=481 × PATH/70 (RO).

2hr arr88 other=32 under wrong CP_VT=0x29D3C68 (and id@+0x18). 2fx catalog:
CProvince VT=0x29EE248, id@+0xA4. One-shot dig with correct constants +
cross vs path_union / focus / arr70. Uses INST_VT=0x2A02558. No Post;
never 5x; no speed write; no midflight; no Assign oi≠0; no endless Instant
poll; no field invent.
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
from handle import resolve_handle
from msvc_rtti import demangle_simple
from pe import PE
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hs_arr88_cp_vt_correct.json"
SUMMARY = ROOT / "reports" / "phase2hs_summary.json"
DOC = ROOT / "docs" / "PHASE2HS_ARR88_CP_VT_CORRECT.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
CP_VT_CORRECT = 0x29EE248
CP_ID_CORRECT = 0xA4
CP_VT_FALSE = 0x29D3C68
FOCUS_OI = 481
FOCUS_PROVS = (3816, 3938, 915)
SHA_BASE = "27c0971"


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
            "ITA oi=481 Instant+0x88 CP_VT=0x29EE248 id@+0xA4 × PATH/70 "
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
        out["error"] = "vt-8 not in PE"
        return out
    col_va = struct.unpack_from("<Q", pe.data, off)[0]
    col_rva = col_va - pe.image_base
    out["col_rva"] = hex(col_rva & 0xFFFFFFFFFFFFFFFF)
    if col_rva < 0 or col_rva > 0x10000000:
        out["error"] = "col_rva out of range"
        return out
    coff = pe.rva_to_off(col_rva)
    if coff is None:
        out["error"] = "COL not mapped"
        return out
    sig, _a, _b, td_rva = struct.unpack_from("<IIII", pe.data, coff)
    out["col_sig"] = sig
    if sig not in (0, 1):
        out["error"] = f"COL sig {sig}"
        return out
    td_off = pe.rva_to_off(td_rva)
    if td_off is None:
        out["error"] = "TD not mapped"
        return out
    name10 = pe.data[td_off + 0x10 : td_off + 0x10 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    name14 = pe.data[td_off + 0x14 : td_off + 0x14 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    pick = name10 if name10.startswith(".?A") else (name14 if name14.startswith(".?A") else name10)
    out["name_raw"] = pick
    out["demangled"] = demangle_simple(pick) if pick else None
    out["ok"] = bool(pick and pick.startswith(".?A"))
    return out


def pe_demangle(image_path: str, rvas) -> dict:
    out = {"image_path": image_path}
    if not image_path or not Path(image_path).is_file():
        out["error"] = "no_image_path"
        return out
    try:
        pe = PE(image_path)
    except Exception as e:
        out["error"] = str(e)
        return out
    out["by_rva"] = {hex(r): rtti_name_at_vtable(pe, r) for r in rvas}
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
    return {"n": len(vals), "province_ids": vals[:12]}


def read_cpdx_ptrs(b, base, arr_addr, max_n=64):
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
    return {"size": size, "in_image_sentinel": False, "u32s": u32s}


def dig(b, base, tag):
    try:
        hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    except Exception:
        hdr = None
    if not hdr:
        return {"ok": False, "reason": "og_unresolved"}
    og = hdr + 0x10
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 4)
    ptrs98 = (arr98 or {}).get("ptrs") or []
    inst = ptrs98[0] if ptrs98 else None
    live_rva = None
    if inst:
        ivt = try_u64(b, inst)
        live_rva = (ivt - base) if ivt else None
    inst_ok = bool(live_rva == INST_VT)

    path_union = set()
    ita_n = 0
    if arr50 and not arr50.get("in_image_sentinel"):
        for p in arr50.get("ptrs") or []:
            if not p:
                continue
            primary = p - CA_MI_OFF
            vt = try_u64(b, primary)
            if not vt or (vt - base) != CA_VT_RVA:
                continue
            atag = try_u32(b, primary + CA_TAG)
            if atag != tag:
                continue
            ita_n += 1
            path = path60(b, base, primary, tag)
            path_union.update(path.get("province_ids") or [])

    arr70 = None
    set70 = set()
    if inst and inst_ok:
        a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
        if a70 and not a70.get("in_image_sentinel"):
            u32s = a70.get("u32s") or []
            shaped = bool(u32s) and all(looks_like_province(v) for v in u32s)
            arr70 = {"size": a70.get("size"), "shaped": shaped, "u32s": u32s[:32]}
            if shaped:
                set70 = set(u32s)

    vt_hist = {}
    sample_vts = []
    ids_correct = []
    ids_false_id_off = []  # same VT but wrong id@+0x18 for contrast
    kinds = {
        "CProvince_correct": 0,
        "CProvince_false_vt": 0,
        "CArmy": 0,
        "COrderInstance": 0,
        "other": 0,
        "nullish": 0,
    }
    pairs = []
    arr88_meta = None
    if inst and inst_ok:
        a88 = read_cpdx_ptrs(b, base, inst + 0x88, 64)
        arr88_meta = {"size": (a88 or {}).get("size"), "in_image_sentinel": (a88 or {}).get("in_image_sentinel")}
        for p in (a88 or {}).get("ptrs") or []:
            if not p or p < 0x10000:
                kinds["nullish"] += 1
                continue
            vr = try_u64(b, p)
            if not vr:
                kinds["other"] += 1
                continue
            rva = vr - base
            key = hex(rva)
            vt_hist[key] = vt_hist.get(key, 0) + 1
            if len(sample_vts) < 6:
                sample_vts.append({"ptr": hex(p), "vt_rva": key})
            if rva == CP_VT_CORRECT:
                kinds["CProvince_correct"] += 1
                pid = try_u32(b, p + CP_ID_CORRECT)
                if pid is not None and looks_like_province(pid):
                    ids_correct.append(pid)
                pid18 = try_u32(b, p + 0x18)
                if pid18 is not None:
                    ids_false_id_off.append(pid18)
            elif rva == CP_VT_FALSE:
                kinds["CProvince_false_vt"] += 1
            elif rva == CA_VT_RVA:
                kinds["CArmy"] += 1
            elif rva == INST_VT:
                kinds["COrderInstance"] += 1
            else:
                kinds["other"] += 1
        # 2fx hub/neighbor packing
        for i in range(0, len(ids_correct) - 1, 2):
            pairs.append([ids_correct[i], ids_correct[i + 1]])
        if len(ids_correct) % 2 == 1:
            pairs.append([ids_correct[-1], None])

    focus = set(FOCUS_PROVS)
    set88 = set(ids_correct)
    return {
        "ok": True,
        "oi": FOCUS_OI,
        "inst": hex(inst) if inst else None,
        "inst_vt_ok": inst_ok,
        "live_vt_rva": hex(live_rva) if live_rva is not None else None,
        "ita_members": ita_n,
        "path_union_ita": sorted(path_union),
        "arr70": arr70,
        "arr88_meta": arr88_meta,
        "arr88_vt_hist": vt_hist,
        "arr88_sample_vts": sample_vts,
        "arr88_kinds": kinds,
        "arr88_ids_correct": ids_correct[:48],
        "arr88_ids_n": len(ids_correct),
        "arr88_id_at_0x18_sample": ids_false_id_off[:8],
        "arr88_pairs": pairs[:16],
        "cross70_path": sorted(path_union & set70),
        "cross88_path": sorted(path_union & set88),
        "cross88_70": sorted(set70 & set88),
        "focus_in_70": sorted(focus & set70),
        "focus_in_88": sorted(focus & set88),
        "cp_vt_correct": hex(CP_VT_CORRECT),
        "cp_id_correct": hex(CP_ID_CORRECT),
        "cp_vt_false_prior": hex(CP_VT_FALSE),
        "false_scripts_noted": ["phase2hr_inst_vt_gate_correct.py", "phase2hp / phase2gm CP_VT"],
        "correct_catalog": "phase2fx_70_88_structure (CP_VT=0x29EE248 id@+0xA4)",
    }


def patch_docs(meta, result, dig, pe_info):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hs `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2hr `INST_VT_GATE_CORRECT_CROSS_HIT`",
        "2hs `ARR88_CP_VT_CORRECT_HIT`",
        "2hs `ARR88_CP_VT_CORRECT_PARTIAL`",
        "2hs `ARR88_CP_VT_CORRECT_VT_ONLY`",
        "2hs `ARR88_CP_VT_CORRECT_MISS`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    c88p = len(dig.get("cross88_path") or [])
    c8870 = len(dig.get("cross88_70") or [])
    t = re.sub(
        r"\| `INST7088` \| order/front maps \| Instance`\+0x70`/`\+0x88`[^\n]*\|\n",
        f"| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` — 2hs oi=481 "
        f"CP_VT=0x29EE248 ids88={dig.get('arr88_ids_n')} cross88∩path={c88p} "
        f"cross88∩70={c8870} (⊀ named dest) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hs** | `{result}` | Instant+0x88 CP_VT fix 0x29D3C68→0x29EE248 id@+0xA4; oi=481 | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hs** |" not in t and "| **2hr** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hr** |"):
                out.append(row)
        t = "".join(out)
    dem = ((pe_info or {}).get("by_rva") or {}).get(hex(CP_VT_CORRECT), {}).get("demangled")
    note = (
        f"**2hs arr88 CP_VT correct:** result=`{result}` · ids88={dig.get('arr88_ids_n')} · "
        f"kinds={dig.get('arr88_kinds')} · cross88∩path={dig.get('cross88_path')} · "
        f"cross88∩70_n={c8870} · focus_in_88={dig.get('focus_in_88')} · "
        f"pe_CP={dem} · hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hs arr88 CP_VT correct:**" not in t and "**2hr INST_VT gate correct:**" in t:
        idx = t.find("**2hr INST_VT gate correct:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hr · INST_VT gate correct · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hs · arr88 CP_VT correct · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hr — checklist polish (CLOSED)",
        "## Phase 2gj … 2hs — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hs | Instant+0x88 CP_VT fix + oi=481 × PATH/70 | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hs |" not in t2 and "| 2hr |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hr |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hr — INST_VT gate correct. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hs — arr88 CP_VT correct. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2hs — Instant+0x88 CP_VT false-gate correction\n\n"
            f"**Result:** `{result}`\n\n"
            f"**False gate:** 2hr/2hp/2gm used `CP_VT=0x29D3C68` (+ id@+0x18) → arr88 other=32.\n\n"
            f"**Correct (2fx):** `CP_VT=0x29EE248` · id@`+0xA4`.\n\n"
            f"**PE demangle CP:** `{dem}`\n\n"
            f"**Live oi=481:** inst_ok={dig.get('inst_vt_ok')} · ids88={dig.get('arr88_ids_n')} · "
            f"kinds={dig.get('arr88_kinds')} · vt_hist={dig.get('arr88_vt_hist')}\n\n"
            f"**Cross:** path∩88={dig.get('cross88_path')} · 70∩88_n={c8870} · "
            f"focus_in_88={dig.get('focus_in_88')} · focus_in_70={dig.get('focus_in_70')}\n\n"
            f"**ids88 sample:** {dig.get('arr88_ids_correct')}\n\n"
            f"**pairs (hub,neighbor) sample:** {dig.get('arr88_pairs')}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** One-shot CP_VT correction + cross; not endless Instant poll. "
            f"Field name STUBBED. No invent. No Post / midflight / oi≠0.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2hs · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hs",
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
    dig_r = dig(b, base, tag)

    # demangle dominant live VT + correct/false constants
    rvas = [CP_VT_CORRECT, CP_VT_FALSE]
    for k in (dig_r.get("arr88_vt_hist") or {}):
        try:
            rvas.append(int(k, 16))
        except Exception:
            pass
    pe_info = pe_demangle(getattr(b, "image_path", "") or "", sorted(set(rvas)))

    n88 = dig_r.get("arr88_ids_n") or 0
    kinds = dig_r.get("arr88_kinds") or {}
    cp_n = kinds.get("CProvince_correct") or 0
    c88p = len(dig_r.get("cross88_path") or [])
    c8870 = len(dig_r.get("cross88_70") or [])
    if cp_n > 0 and (c88p > 0 or c8870 > 0):
        result = "ARR88_CP_VT_CORRECT_HIT"
    elif cp_n > 0:
        result = "ARR88_CP_VT_CORRECT_PARTIAL"
    elif dig_r.get("inst_vt_ok"):
        result = "ARR88_CP_VT_CORRECT_VT_ONLY"
    else:
        result = "ARR88_CP_VT_CORRECT_MISS"

    report = {
        "phase": "2hs",
        "result": result,
        "allow_post": False,
        "live": meta,
        "dig": dig_r,
        "pe_demangle": pe_info,
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
            "plan-dense Assign oi≠0 (2hs arr88 CP_VT corrected); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "Instant+0x88 CP_VT 0x29D3C68→0x29EE248 id@+0xA4; oi=481 × PATH/70; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2hs",
                "result": result,
                "allow_post": False,
                "arr88_ids_n": n88,
                "arr88_kinds": kinds,
                "cross88_path": dig_r.get("cross88_path"),
                "cross88_70_n": c8870,
                "focus_in_88": dig_r.get("focus_in_88"),
                "pe_cp_demangle": ((pe_info or {}).get("by_rva") or {}).get(
                    hex(CP_VT_CORRECT), {}
                ).get("demangled"),
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "drain": meta.get("drain"),
                    "exec": meta.get("exec"),
                    "stage_count": meta.get("stage_count"),
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
        patch_docs(meta, result, dig_r, pe_info)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2hs",
                "result": result,
                "allow_post": False,
                "live": meta,
                "inst_vt_ok": dig_r.get("inst_vt_ok"),
                "arr88_ids_n": n88,
                "arr88_kinds": kinds,
                "arr88_vt_hist": dig_r.get("arr88_vt_hist"),
                "arr88_ids_sample": (dig_r.get("arr88_ids_correct") or [])[:12],
                "arr88_pairs_sample": (dig_r.get("arr88_pairs") or [])[:6],
                "cross88_path": dig_r.get("cross88_path"),
                "cross88_70_n": c8870,
                "cross70_path": dig_r.get("cross70_path"),
                "focus_in_88": dig_r.get("focus_in_88"),
                "focus_in_70": dig_r.get("focus_in_70"),
                "path_union_ita": dig_r.get("path_union_ita"),
                "pe_cp": ((pe_info or {}).get("by_rva") or {}).get(hex(CP_VT_CORRECT)),
                "pe_false": ((pe_info or {}).get("by_rva") or {}).get(hex(CP_VT_FALSE)),
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
