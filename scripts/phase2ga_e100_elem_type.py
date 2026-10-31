#!/usr/bin/env python3
"""Phase 2ga: name Instance+0x100 elem type vs +0xe0 twin (RO).
No Post. Never 5x. allow_post False.
"""
from __future__ import annotations

import json
import math
import struct
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
import cmd_layout
import post_abi
from handle import resolve_handle, HANDLE_TYPE_ARMY

assert allow_post() is False, "allow_post must stay False"

ASSIGN_VT = cmd_layout.ORDERS["COrderAssignCommand"]["vt"]
TYPE_OG = 0x35
INST_VT = 0x2A02558
CA_VT = 0x29D6D68
CA_MI = {0x29D6F48, 0x29D6FB8, 0x29D7000}
CP_VT = 0x29EE248
CP_ID = 0xA4
MAX_SIGHT_S = 8.0

VT_CATALOG = {
    INST_VT: "COrderInstance",
    CA_VT: "CArmy",
    0x29D6F48: "CArmy_MI",
    0x29D6FB8: "CArmy_MI",
    0x29D7000: "CArmy_MI",
    CP_VT: "CProvince",
    0x29CED48: "COrdersGroupMember",
    0x29CE220: "catalog_miss_0x29ce220",  # seen resolved from handle in 2fz
    0x29D4858: "catalog_miss_0x29d4858",
    0x29CED90: "catalog_miss_0x29ced90",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def looks_prov(v: int) -> bool:
    return 1 <= v <= 20000


def read_cpdx(b, base, addr):
    raw = try_read(b, addr, 0x18)
    if not raw:
        return None
    data, cap, size = struct.unpack_from("<Qii", raw, 0)
    alloc = struct.unpack_from("<Q", raw, 0x10)[0] if len(raw) >= 0x18 else 0
    plausible = data > 0x10000 and 0 <= size <= 8192 and size <= max(cap, size)
    return {
        "data": data,
        "size": size,
        "cap": cap,
        "alloc": alloc,
        "plausible": plausible,
        "sentinel": base <= data < base + b.image_size,
        "meta": hex(addr),
    }


def live_meta(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "pid": find_pid(),
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x Instance+0x100 elem type vs +0xe0 (no Post)",
        "gs": hex(gs),
    }


def stage_watch(b, base, seconds=MAX_SIGHT_S):
    sess = u64(b, base + post_abi.G_SESSION)
    t0 = time.time()
    counts = Counter()
    assigns = []
    seen = set()
    while time.time() - t0 < seconds:
        try:
            stage = u64(b, sess + post_abi.CSession_STAGE_ARRAY)
            scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        except Exception:
            continue
        if not stage or not (0 < scount < 256):
            continue
        for i in range(scount):
            try:
                ptr = u64(b, stage + i * 8)
                vt = u64(b, ptr)
            except Exception:
                continue
            rva = vt - base
            if rva != ASSIGN_VT:
                continue
            counts["COrderAssignCommand"] += 1
            if ptr in seen:
                continue
            seen.add(ptr)
            oi = u32(b, ptr + 0x48)
            assigns.append(oi)
    return {"elapsed_s": round(time.time() - t0, 1), "sight_counts": dict(counts), "ois": sorted(set(assigns))}


def classify_ptr(b, base, p):
    if p < 0x10000:
        return {"kind": "nullish", "raw": hex(p)}
    raw = try_read(b, p, 16)
    if not raw:
        return {"kind": "unreadable", "ptr": hex(p)}
    vt = struct.unpack_from("<Q", raw, 0)[0]
    vr = vt - base
    nm = VT_CATALOG.get(vr)
    out = {"kind": "ptr", "ptr": hex(p), "vt_rva": hex(vr) if 0 < vr < 0x4000000 else None, "vt_name": nm}
    if vr == CP_VT or nm == "CProvince":
        try:
            out["kind"] = "CProvince*"
            out["province_id"] = u32(b, p + CP_ID)
        except Exception:
            pass
    elif vr == CA_VT or vr in CA_MI or (nm and nm.startswith("CArmy")):
        out["kind"] = "CArmy*_or_MI"
    elif vr == INST_VT:
        out["kind"] = "COrderInstance*"
    elif nm:
        out["kind"] = "named_ptr"
    else:
        # soft fields
        try:
            out["u32_0"] = struct.unpack_from("<I", raw, 0)[0]
            out["u32_4"] = struct.unpack_from("<I", raw, 4)[0]
            out["f32_0"] = struct.unpack_from("<f", raw, 0)[0]
        except Exception:
            pass
        out["kind"] = "opaque_ptr"
    return out


def as_float_ok(u: int) -> bool:
    f = struct.unpack("<f", struct.pack("<I", u & 0xFFFFFFFF))[0]
    if not math.isfinite(f):
        return False
    # reject huge / tiny denorm-ish for game weights
    return abs(f) < 1e6


def analyze_e100(b, base, arr_e0, arr_100):
    if not arr_100 or not arr_100["plausible"] or arr_100["size"] <= 0 or arr_100["sentinel"]:
        return {"empty": True, "size": (arr_100 or {}).get("size")}

    n = arr_100["size"]
    # raw dumps
    raw4 = try_read(b, arr_100["data"], n * 4) or b""
    raw8 = try_read(b, arr_100["data"], n * 8) or b""
    raw16 = try_read(b, arr_100["data"], n * 16) or b""

    u32s = [struct.unpack_from("<I", raw4, i * 4)[0] for i in range(len(raw4) // 4)]
    qwords = [struct.unpack_from("<Q", raw8, i * 8)[0] for i in range(len(raw8) // 8)]
    floats = [struct.unpack_from("<f", raw4, i * 4)[0] for i in range(len(raw4) // 4)]

    e0_u32s = []
    if arr_e0 and arr_e0["plausible"] and arr_e0["size"] > 0 and not arr_e0["sentinel"]:
        blob = try_read(b, arr_e0["data"], arr_e0["size"] * 4) or b""
        e0_u32s = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(len(blob) // 4)]

    # Hypothesis scores
    hyp = {}

    # H1: CPdxArray<u32> (same as e0) — already known false if not all prov
    hyp["u32_all_province"] = bool(u32s) and len(u32s) >= n and all(looks_prov(v) for v in u32s[:n])

    # H2: CPdxArray<float>
    fslice = floats[:n] if len(floats) >= n else floats
    hyp["float_array"] = bool(fslice) and all(math.isfinite(f) and abs(f) < 1e6 for f in fslice)
    hyp["float_sample"] = [round(f, 5) for f in fslice[:8]]

    # H3: CPdxArray<ptr> size qwords
    ptr_kinds = Counter()
    ptr_elems = []
    for i, q in enumerate(qwords[:n]):
        c = classify_ptr(b, base, q)
        ptr_elems.append({"i": i, **c})
        ptr_kinds[c["kind"]] += 1
    hyp["ptr_kinds"] = dict(ptr_kinds)
    hyp["ptr_elems_sample"] = ptr_elems[:8]
    hyp["ptr_array_named"] = (
        ptr_kinds.get("CProvince*", 0)
        + ptr_kinds.get("CArmy*_or_MI", 0)
        + ptr_kinds.get("COrderInstance*", 0)
        + ptr_kinds.get("named_ptr", 0)
    ) >= max(1, n // 2)

    # H4: interleaved struct in e100 alone: {u32,u32} or {float,u32} pairs with n/2 elems — only if n even
    # H5: parallel to e0 — e100[i] associates with e0[i]
    #     try: e100 as float[i], or ptr[i], or struct at stride 8/16
    parallel = {
        "same_size": arr_e0 and arr_e0.get("size") == n,
        "same_data_ptr": arr_e0 and arr_e0.get("data") == arr_100.get("data"),
        "e0_first_eq_e100_u32_0": bool(e0_u32s) and bool(u32s) and e0_u32s[0] == u32s[0],
        "e0_sample": e0_u32s[:8],
        "e100_u32_sample": u32s[:8],
    }

    # Per-index pairing: for i in 0..n-1, look at qword i and float i vs e0[i]
    pairs = []
    for i in range(min(n, len(e0_u32s), 12)):
        rec = {"i": i, "e0": e0_u32s[i]}
        if i < len(u32s):
            rec["e100_u32"] = u32s[i]
            rec["e100_f32"] = round(floats[i], 5) if i < len(floats) else None
            rec["e100_u32_is_prov"] = looks_prov(u32s[i])
            rec["e100_f32_ok"] = as_float_ok(u32s[i]) if i < len(u32s) else False
        if i < len(qwords):
            rec["e100_qword"] = hex(qwords[i])
            rec["e100_ptr_class"] = classify_ptr(b, base, qwords[i])
        pairs.append(rec)
    hyp["pairs"] = pairs

    # H6: stride-16 structs (n structs) — each 16 bytes: maybe {ptr, float, pad} or {u64,u64}
    stride16 = []
    if len(raw16) >= n * 16:
        for i in range(min(n, 8)):
            chunk = raw16[i * 16 : (i + 1) * 16]
            a, c = struct.unpack_from("<QQ", chunk, 0)
            u0, u1, u2, u3 = struct.unpack_from("<IIII", chunk, 0)
            f0, f1 = struct.unpack_from("<ff", chunk, 0)
            stride16.append({
                "i": i,
                "q0": hex(a),
                "q1": hex(c),
                "u": [u0, u1, u2, u3],
                "f": [round(f0, 5), round(f1, 5)],
                "q0_class": classify_ptr(b, base, a),
                "q1_class": classify_ptr(b, base, c),
            })
    hyp["stride16_sample"] = stride16

    # Dominant verdict (honest, no invent)
    verdict = "unnamed"
    detail = []
    if hyp["u32_all_province"]:
        verdict = "CPdxArray_u32_province"
        detail.append("all u32 province-shaped")
    elif hyp["ptr_array_named"]:
        top = ptr_kinds.most_common(1)[0][0]
        verdict = f"CPdxArray_ptr__{top}"
        detail.append(f"named ptr majority: {dict(ptr_kinds)}")
    elif hyp["float_array"] and not any(looks_prov(v) for v in u32s[:n] if True):
        # floats that aren't coincidentally province ids
        # many province ids as floats are tiny integers — check if values look like weights 0..1 or large
        if fslice and all(0.0 <= f <= 10.0 for f in fslice):
            verdict = "CPdxArray_float_weightish"
            detail.append(f"floats in [0,10]: {hyp['float_sample']}")
        elif fslice and sum(1 for f in fslice if abs(f - 1.0) < 1e-5 or abs(f) < 1e-5) >= max(1, n // 2):
            verdict = "CPdxArray_float_0_or_1"
            detail.append(f"mostly 0/1 floats: {hyp['float_sample']}")
        else:
            verdict = "CPdxArray_float_candidate"
            detail.append(f"finite floats: {hyp['float_sample']}")
    elif ptr_kinds.get("opaque_ptr", 0) + ptr_kinds.get("unreadable", 0) >= max(1, n // 2):
        verdict = "CPdxArray_opaque_ptr"
        detail.append(f"ptr kinds {dict(ptr_kinds)}")
    elif ptr_kinds.get("nullish", 0) >= max(1, n // 2):
        verdict = "CPdxArray_mostly_null_qwords"
        detail.append(f"ptr kinds {dict(ptr_kinds)}")
    else:
        # Mixed: often first u32 equals e0[0] then garbage — suggest size counts parallel slots
        # but storage is not homogeneous u32
        if parallel["e0_first_eq_e100_u32_0"]:
            verdict = "parallel_slots_mixed_layout__first_u32_echoes_e0"
            detail.append("first dword of +0x100 equals e0[0]; remaining not homogeneous province u32")
        else:
            verdict = "mixed_or_opaque_layout"
            detail.append(f"ptr={dict(ptr_kinds)} float_ok={hyp['float_array']}")

    # Shared first-dword rate
    first_echo = 0
    if e0_u32s and u32s and arr_e0 and arr_e0.get("size") == n:
        if e0_u32s[0] == u32s[0]:
            first_echo = 1

    return {
        "empty": False,
        "size": n,
        "cap": arr_100["cap"],
        "data": hex(arr_100["data"]),
        "alloc": hex(arr_100["alloc"]),
        "e0_size": (arr_e0 or {}).get("size"),
        "e0_data": hex(arr_e0["data"]) if arr_e0 else None,
        "parallel": parallel,
        "hypotheses": {
            "u32_all_province": hyp["u32_all_province"],
            "float_array": hyp["float_array"],
            "float_sample": hyp["float_sample"],
            "ptr_kinds": hyp["ptr_kinds"],
            "ptr_array_named": hyp["ptr_array_named"],
        },
        "ptr_elems_sample": hyp["ptr_elems_sample"],
        "pairs": hyp["pairs"],
        "stride16_sample": hyp["stride16_sample"],
        "verdict": verdict,
        "verdict_detail": detail,
        "first_u32_echoes_e0": bool(first_echo),
        "raw8_hex_head": raw8[:64].hex() if raw8 else None,
    }


def read_inst(b, base, oi):
    hdr = resolve_handle(b, TYPE_OG, oi, base)
    if not hdr:
        return None
    og = hdr + 0x10
    a98 = read_cpdx(b, base, og + 0x98)
    if not a98 or not a98["plausible"] or a98["size"] < 1 or a98["sentinel"]:
        return None
    inst = u64(b, a98["data"])
    try:
        if u64(b, inst) - base != INST_VT:
            return {"oi": oi, "vt_ok": False}
    except Exception:
        return None
    arr_e0 = read_cpdx(b, base, inst + 0xE0)
    arr_100 = read_cpdx(b, base, inst + 0x100)
    arr_70 = read_cpdx(b, base, inst + 0x70)
    analysis = analyze_e100(b, base, arr_e0, arr_100)
    e0_u32s = []
    if arr_e0 and arr_e0["plausible"] and arr_e0["size"] > 0 and not arr_e0["sentinel"]:
        blob = try_read(b, arr_e0["data"], min(arr_e0["size"], 64) * 4) or b""
        e0_u32s = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(len(blob) // 4)]
    return {
        "oi": oi,
        "vt_ok": True,
        "inst": hex(inst),
        "n70": (arr_70 or {}).get("size"),
        "n_e0": (arr_e0 or {}).get("size"),
        "n_100": (arr_100 or {}).get("size"),
        "e0_u32_sample": e0_u32s[:12],
        "e0_all_prov": bool(e0_u32s) and all(looks_prov(v) for v in e0_u32s),
        "e100": analysis,
    }


def main():
    b = Backend()
    base = b.image_base
    meta = live_meta(b, base)
    sight = stage_watch(b, base)
    print("SIGHT", sight, flush=True)

    ois = set(sight.get("ois") or [])
    for oi in (4, 5, 6, 7, 8, 9, 13, 17, 20, 22, 25, 27, 38, 40, 44, 52, 68, 70, 124):
        ois.add(oi)

    rows = []
    verdicts = Counter()
    nonempty = 0
    first_echo = 0
    size_twin = 0
    for oi in sorted(ois):
        rec = read_inst(b, base, oi)
        if not rec or not rec.get("vt_ok"):
            rows.append({"oi": oi, "ok": False})
            continue
        rows.append({"oi": oi, "ok": True, **{k: rec[k] for k in rec if k not in ("oi", "vt_ok")}})
        e = rec.get("e100") or {}
        if not e.get("empty"):
            nonempty += 1
            verdicts[e.get("verdict")] += 1
            if e.get("first_u32_echoes_e0"):
                first_echo += 1
            if rec.get("n_e0") == rec.get("n_100"):
                size_twin += 1

    top = verdicts.most_common(1)[0] if verdicts else (None, 0)
    if nonempty == 0:
        result = "inst_e100_empty_this_window"
        note = "No nonempty +0x100"
    elif top[0] and top[0].startswith("CPdxArray_ptr__"):
        result = f"inst_e100_{top[0]}"
        note = f"dominant={top}; first_echo_e0={first_echo}/{nonempty}; size_twin={size_twin}"
    elif top[0] and "float" in (top[0] or ""):
        result = f"inst_e100_{top[0]}"
        note = f"dominant={top}; first_echo_e0={first_echo}/{nonempty}"
    elif top[0] == "parallel_slots_mixed_layout__first_u32_echoes_e0":
        result = "inst_e100_parallel_mixed__first_dword_echoes_e0"
        note = (
            f"+0x100 size-twins +0xe0; first dword often echoes e0[0]; "
            f"storage not homogeneous u32-province / not catalog-named ptr majority. "
            f"verdicts={dict(verdicts)}. Elem type still not a single named Clausewitz class."
        )
    else:
        result = "inst_e100_elem_type_partial"
        note = f"verdicts={dict(verdicts)}; first_echo={first_echo}/{nonempty}; size_twin={size_twin}"

    out = {
        "phase": "2ga",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta,
        "sight": sight,
        "aggregate": {
            "ois": len(rows),
            "nonempty_e100": nonempty,
            "verdicts": dict(verdicts),
            "first_u32_echoes_e0": first_echo,
            "size_twin_e0": size_twin,
        },
        "rows": rows,
        "works": [
            "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
            f"result={result}",
            f"nonempty_e100={nonempty} verdicts={dict(verdicts)}",
            f"first_u32_echoes_e0={first_echo}/{nonempty} size_twin={size_twin}",
            f"Assign sight {sight.get('sight_counts')} ois={sight.get('ois')}",
        ],
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live leaf",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
            "named +0x100 Clausewitz class / demangled RTTI (if still partial)",
            "named +0xe0 role beyond u32 province stream",
            "named CArmy path-field offsets",
            "war-dense relaunch (not this slice if B progressed)",
            "HourlyTick abuse",
            "Capstone/121 re-churn",
            "NewFallback subject type-id table",
            "live midflight NewFallback hex",
            "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        ],
        "next_shortest_blocker": (
            "NON-Post: bounded NF/RF midflight OR war-dense named CArmy path OR "
            "demangle +0x100 opaque ptr VTs; still NO ALLOW_POST"
        ),
    }
    (ROOT / "reports" / "phase2ga_e100_elem_type.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    briefs = []
    for r in rows:
        if not r.get("ok"):
            continue
        e = r.get("e100") or {}
        if e.get("empty"):
            continue
        briefs.append({
            "oi": r["oi"],
            "n_e0": r.get("n_e0"),
            "n_100": r.get("n_100"),
            "e0_sample": r.get("e0_u32_sample"),
            "verdict": e.get("verdict"),
            "detail": e.get("verdict_detail"),
            "hyp": e.get("hypotheses"),
            "pairs": e.get("pairs"),
            "ptr_sample": e.get("ptr_elems_sample"),
            "stride16": e.get("stride16_sample"),
            "raw8_hex_head": e.get("raw8_hex_head"),
            "first_echo": e.get("first_u32_echoes_e0"),
        })
    summary = {k: out[k] for k in out if k != "rows"}
    summary["briefs"] = briefs
    (ROOT / "reports" / "phase2ga_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "live": meta,
        "aggregate": out["aggregate"],
        "briefs": briefs[:6],
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
