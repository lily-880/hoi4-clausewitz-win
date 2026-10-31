#!/usr/bin/env python3
"""Phase 2fz: deepen Instance+0xe0/+0x100 RO identity.
Relation to +0x70/+0x88; province vs ptr reinterpretation. No Post. Never 5x.
"""
from __future__ import annotations

import json
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
OG_VT = 0x29CED00  # may be wrong; catalog soft
MEMBER_VT = 0x29CED48
MAX_SIGHT_S = 10.0
MAX_ARR = 64

# Catalog names for known VTs (no invent beyond WINDOWS_OFFSETS / prior slices)
VT_CATALOG = {
    INST_VT: "COrderInstance",
    CA_VT: "CArmy",
    0x29D6F48: "CArmy_MI",
    0x29D6FB8: "CArmy_MI",
    0x29D7000: "CArmy_MI",
    CP_VT: "CProvince",
    MEMBER_VT: "COrdersGroupMember",
    0x29CEE28: "CArmyGroup",
    0x29CEEA0: "CArmyGroup_MI",
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
    plausible = data > 0x10000 and 0 <= size <= 8192 and size <= max(cap, size)
    return {
        "data": data,
        "size": size,
        "cap": cap,
        "plausible": plausible,
        "sentinel": base <= data < base + b.image_size,
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
        "scenario": "ITA@1x Instance+0xe0/+0x100 deepen (no Post)",
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
            size = i32(b, ptr + 0x34)
            data = u64(b, ptr + 0x28)
            armies = []
            if data and 0 < size <= 64:
                blob = try_read(b, data, size * 8)
                if blob:
                    for j in range(size):
                        typ, ix = struct.unpack_from("<II", blob, j * 8)
                        if typ == HANDLE_TYPE_ARMY:
                            armies.append(ix)
            assigns.append({"order_index": oi, "army_indices": armies})
    return {"elapsed_s": round(time.time() - t0, 1), "sight_counts": dict(counts), "assigns": assigns}


def vt_name(rva):
    return VT_CATALOG.get(rva)


def classify_qword(b, base, q):
    typ = q & 0xFFFFFFFF
    idx = (q >> 32) & 0xFFFFFFFF
    # handle-shaped: low type small, high index
    if typ < 0x80 and idx < 0x100000 and (typ > 0 or idx > 0):
        hdr = None
        try:
            hdr = resolve_handle(b, typ, idx, base)
        except Exception:
            pass
        body_info = None
        if hdr:
            for cand in (hdr + 0x10, hdr):
                raw = try_read(b, cand, 8)
                if not raw:
                    continue
                vr = struct.unpack("<Q", raw)[0] - base
                nm = vt_name(vr)
                if nm or (0 < vr < 0x4000000):
                    body_info = {"cand": hex(cand), "vt_rva": hex(vr), "vt_name": nm}
                    if nm:
                        break
        return {
            "kind": "handle_resolved" if hdr else "handle_shaped",
            "type": typ,
            "type_hex": hex(typ),
            "index": idx,
            "header": hex(hdr) if hdr else None,
            "body": body_info,
        }
    if q < 0x10000:
        return {"kind": "nullish", "raw": hex(q)}
    raw = try_read(b, q, 8)
    if not raw:
        return {"kind": "unreadable_ptr", "ptr": hex(q)}
    vr = struct.unpack("<Q", raw)[0] - base
    nm = vt_name(vr)
    prov_id = None
    if nm == "CProvince" or vr == CP_VT:
        try:
            prov_id = u32(b, q + CP_ID)
        except Exception:
            pass
        return {"kind": "CProvince*", "ptr": hex(q), "vt_rva": hex(vr), "province_id": prov_id}
    if nm == "CArmy" or vr == CA_VT or vr in CA_MI:
        return {"kind": "CArmy*_or_MI", "ptr": hex(q), "vt_rva": hex(vr), "vt_name": nm or "CArmy_MI"}
    if nm == "COrderInstance" or vr == INST_VT:
        return {"kind": "COrderInstance*", "ptr": hex(q), "vt_rva": hex(vr)}
    if nm:
        return {"kind": "named_ptr", "ptr": hex(q), "vt_rva": hex(vr), "vt_name": nm}
    # probe MI-ish / first 4 bytes as possible id
    soft = None
    try:
        soft = u32(b, q + CP_ID)
    except Exception:
        pass
    return {
        "kind": "opaque_ptr",
        "ptr": hex(q),
        "vt_rva": hex(vr) if 0 < vr < 0x4000000 else None,
        "soft_u32_at_a4": soft if soft is not None and looks_prov(soft) else None,
    }


def analyze_arr(b, base, arr, label):
    if not arr or not arr["plausible"] or arr["size"] <= 0:
        return {"label": label, "empty": True, "size": (arr or {}).get("size"), "cap": (arr or {}).get("cap")}
    if arr["sentinel"]:
        return {"label": label, "empty": True, "reason": "image_sentinel", "size": arr["size"]}
    n = min(arr["size"], MAX_ARR)
    # u32 reinterpret
    blob4 = try_read(b, arr["data"], n * 4)
    u32s = []
    if blob4 and len(blob4) >= n * 4:
        u32s = [struct.unpack_from("<I", blob4, i * 4)[0] for i in range(n)]
    u32_all_prov = bool(u32s) and all(looks_prov(v) for v in u32s)
    # ptr/handle reinterpret (stride 8) — size is element count for CPdxArray
    blob8 = try_read(b, arr["data"], n * 8)
    elems = []
    kinds = Counter()
    if blob8 and len(blob8) >= n * 8:
        for i in range(n):
            q = struct.unpack_from("<Q", blob8, i * 8)[0]
            c = classify_qword(b, base, q)
            elems.append({"i": i, **c})
            kinds[c["kind"]] += 1
    else:
        # maybe size is bytes? try size/2 as qword count if size even and small
        pass

    # Dominant identity
    dominant = None
    if kinds:
        dominant = kinds.most_common(1)[0][0]
    reinterpretation = {
        "u32_all_province_shaped": u32_all_prov,
        "u32_sample": u32s[:12],
        "ptr_kinds": dict(kinds),
        "verdict": None,
    }
    if kinds.get("CProvince*", 0) >= max(1, n // 2):
        reinterpretation["verdict"] = "ptr_CProvince_array"
    elif kinds.get("handle_resolved", 0) + kinds.get("handle_shaped", 0) >= max(1, n // 2):
        reinterpretation["verdict"] = "handle_array"
    elif kinds.get("CArmy*_or_MI", 0) >= max(1, n // 2):
        reinterpretation["verdict"] = "ptr_CArmy_array"
    elif kinds.get("opaque_ptr", 0) + kinds.get("unreadable_ptr", 0) >= max(1, n // 2):
        # if also u32_all_prov, that is FALSE province stream from pointer low/high dwords
        if u32_all_prov:
            reinterpretation["verdict"] = "opaque_ptr_array__u32_province_is_reinterpretation_artifact"
        else:
            reinterpretation["verdict"] = "opaque_ptr_array"
    elif u32_all_prov and not kinds:
        reinterpretation["verdict"] = "u32_province_stream_only"
    elif u32_all_prov and kinds.get("nullish", 0) + kinds.get("handle_shaped", 0) > 0:
        reinterpretation["verdict"] = "mixed_or_ambiguous"
    else:
        reinterpretation["verdict"] = "mixed_or_thin"

    prov_ids_from_cp = [e.get("province_id") for e in elems if e.get("kind") == "CProvince*" and e.get("province_id")]
    handle_types = Counter(e["type"] for e in elems if e.get("kind") in ("handle_resolved", "handle_shaped") and "type" in e)

    return {
        "label": label,
        "empty": False,
        "size": arr["size"],
        "cap": arr["cap"],
        "data": hex(arr["data"]),
        "reinterpretation": reinterpretation,
        "elems_sample": elems[:16],
        "province_ids_from_CProvince": prov_ids_from_cp[:32],
        "handle_type_hist": {hex(k): v for k, v in handle_types.items()},
        "dominant_kind": dominant,
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
        vt = u64(b, inst) - base
    except Exception:
        return None
    if vt != INST_VT:
        return {"oi": oi, "vt_ok": False, "vt": hex(vt)}
    out = {"oi": oi, "vt_ok": True, "inst": hex(inst), "og": hex(og)}
    arr70 = read_cpdx(b, base, inst + 0x70)
    arr88 = read_cpdx(b, base, inst + 0x88)
    arr_e0 = read_cpdx(b, base, inst + 0xE0)
    arr_100 = read_cpdx(b, base, inst + 0x100)

    u32s70 = []
    if arr70 and arr70["plausible"] and arr70["size"] > 0 and not arr70["sentinel"]:
        blob = try_read(b, arr70["data"], min(arr70["size"], MAX_ARR) * 4)
        if blob:
            n = min(arr70["size"], MAX_ARR)
            u32s70 = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(n)]
            if not all(looks_prov(v) for v in u32s70):
                u32s70 = []

    hubs88 = []
    neigh88 = []
    if arr88 and arr88["plausible"] and arr88["size"] > 0 and not arr88["sentinel"]:
        # (hub,neighbor) pairs as CProvince* — 2fx
        n = min(arr88["size"], MAX_ARR)
        blob = try_read(b, arr88["data"], n * 8)
        if blob:
            ids = []
            for i in range(n):
                p = struct.unpack_from("<Q", blob, i * 8)[0]
                if p < 0x10000:
                    ids.append(None)
                    continue
                try:
                    if u64(b, p) - base != CP_VT:
                        ids.append(None)
                        continue
                    ids.append(u32(b, p + CP_ID))
                except Exception:
                    ids.append(None)
            for i in range(0, len(ids) - 1, 2):
                if ids[i] is not None:
                    hubs88.append(ids[i])
                if ids[i + 1] is not None:
                    neigh88.append(ids[i + 1])

    e0 = analyze_arr(b, base, arr_e0, "+0xe0")
    e100 = analyze_arr(b, base, arr_100, "+0x100")

    def rel(ids):
        set70 = set(u32s70)
        set_h = set(hubs88)
        set_n = set(neigh88)
        s = set(ids)
        return {
            "n": len(ids),
            "overlap_70": sorted(s & set70),
            "frac_in_70": (len(s & set70) / len(s)) if s else None,
            "overlap_hubs88": sorted(s & set_h),
            "overlap_neigh88": sorted(s & set_n),
            "equal_70": ids == u32s70 and bool(ids),
            "equal_hubs_prefix": ids == hubs88[: len(ids)] and bool(ids),
        }

    e0_rel = rel(e0.get("province_ids_from_CProvince") or [])
    e100_rel = rel(e100.get("province_ids_from_CProvince") or [])

    # Also: if handle array, do indices relate? leave as hist only
    # Size relations
    size_rel = {
        "n70": len(u32s70),
        "n88": (arr88 or {}).get("size"),
        "n_e0": (arr_e0 or {}).get("size") if arr_e0 else None,
        "n_100": (arr_100 or {}).get("size") if arr_100 else None,
        "e0_eq_70": (arr_e0 or {}).get("size") == len(u32s70) if arr_e0 and u32s70 else False,
        "e0_eq_88": (arr_e0 or {}).get("size") == (arr88 or {}).get("size") if arr_e0 and arr88 else False,
        "e100_eq_e0": (arr_e0 or {}).get("size") == (arr_100 or {}).get("size") if arr_e0 and arr_100 else False,
        "e100_eq_70": (arr_100 or {}).get("size") == len(u32s70) if arr_100 and u32s70 else False,
        "e100_eq_88": (arr_100 or {}).get("size") == (arr88 or {}).get("size") if arr_100 and arr88 else False,
    }

    out.update({
        "u32s70_sample": u32s70[:16],
        "hubs88_sample": hubs88[:12],
        "neigh88_sample": neigh88[:12],
        "e0": e0,
        "e100": e100,
        "e0_vs_70_88": e0_rel,
        "e100_vs_70_88": e100_rel,
        "size_rel": size_rel,
    })
    return out


def main():
    b = Backend()
    base = b.image_base
    meta = live_meta(b, base)
    sight = stage_watch(b, base)
    print("SIGHT", sight["sight_counts"], "assigns", len(sight["assigns"]), flush=True)

    ois = set()
    for a in sight["assigns"]:
        ois.add(int(a["order_index"]))
    for oi in (5, 6, 7, 8, 9, 13, 17, 20, 22, 25, 27, 38, 40, 44, 52, 68, 70, 124):
        ois.add(oi)

    rows = []
    verdicts_e0 = Counter()
    verdicts_e100 = Counter()
    nonempty_e0 = 0
    nonempty_e100 = 0
    for oi in sorted(ois):
        inst = read_inst(b, base, oi)
        if not inst or not inst.get("vt_ok"):
            rows.append({"oi": oi, "ok": False})
            continue
        if not inst["e0"].get("empty"):
            nonempty_e0 += 1
            verdicts_e0[inst["e0"]["reinterpretation"]["verdict"]] += 1
        if not inst["e100"].get("empty"):
            nonempty_e100 += 1
            verdicts_e100[inst["e100"]["reinterpretation"]["verdict"]] += 1
        rows.append({"oi": oi, "ok": True, **{k: inst[k] for k in inst if k not in ("oi", "vt_ok")}})

    # Aggregate identity claim (honest)
    top_e0 = verdicts_e0.most_common(1)[0] if verdicts_e0 else (None, 0)
    top_e100 = verdicts_e100.most_common(1)[0] if verdicts_e100 else (None, 0)

    # Relation summary across nonempty CP arrays
    cp_e0_overlap_any = any(
        (r.get("e0_vs_70_88") or {}).get("overlap_70")
        or (r.get("e0_vs_70_88") or {}).get("overlap_hubs88")
        for r in rows if r.get("ok") and not (r.get("e0") or {}).get("empty")
    )
    size_e100_eq_e0 = sum(1 for r in rows if r.get("ok") and (r.get("size_rel") or {}).get("e100_eq_e0"))
    size_e0_eq_88 = sum(1 for r in rows if r.get("ok") and (r.get("size_rel") or {}).get("e0_eq_88"))
    size_e0_eq_70 = sum(1 for r in rows if r.get("ok") and (r.get("size_rel") or {}).get("e0_eq_70"))

    if nonempty_e0 == 0 and nonempty_e100 == 0:
        result = "inst_e0_e100_empty_this_window"
        note = "No nonempty +0xe0/+0x100 on sampled ois"
    elif top_e0[0] and "reinterpretation_artifact" in (top_e0[0] or ""):
        result = "inst_e0_e100_opaque_ptr__u32_prov_artifact"
        note = (
            f"+0xe0 dominant={top_e0}; +0x100 dominant={top_e100}. "
            "u32 province-shaped reads are reinterpretation of pointer dwords; "
            "elems are opaque/unreadable ptrs (not proven CProvince*/CArmy*). "
            f"size e0==e100 on {size_e100_eq_e0} ois; e0==88 on {size_e0_eq_88}; e0==70 on {size_e0_eq_70}."
        )
    elif top_e0[0] == "handle_array" or top_e100[0] == "handle_array":
        result = "inst_e0_e100_handle_array"
        note = f"e0={top_e0} e100={top_e100}; see handle_type_hist"
    elif top_e0[0] == "ptr_CProvince_array" or top_e100[0] == "ptr_CProvince_array":
        result = "inst_e0_e100_cprovince_ptr_array"
        note = f"e0={top_e0} e100={top_e100}; cp_overlap_vs_70_88_any={cp_e0_overlap_any}"
    elif top_e0[0] == "opaque_ptr_array" or top_e100[0] == "opaque_ptr_array":
        result = "inst_e0_e100_opaque_ptr_array"
        note = (
            f"e0={top_e0} e100={top_e100}; size e100==e0:{size_e100_eq_e0} e0==88:{size_e0_eq_88} e0==70:{size_e0_eq_70}. "
            "No catalog VT on elems this window."
        )
    else:
        result = "inst_e0_e100_identity_partial"
        note = f"e0={dict(verdicts_e0)} e100={dict(verdicts_e100)}; size e100==e0:{size_e100_eq_e0}"

    out = {
        "phase": "2fz",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta,
        "sight": {"sight_counts": sight["sight_counts"], "n_assigns": len(sight["assigns"]), "elapsed_s": sight["elapsed_s"]},
        "aggregate": {
            "ois": len(rows),
            "nonempty_e0": nonempty_e0,
            "nonempty_e100": nonempty_e100,
            "verdicts_e0": dict(verdicts_e0),
            "verdicts_e100": dict(verdicts_e100),
            "size_e100_eq_e0_count": size_e100_eq_e0,
            "size_e0_eq_88_count": size_e0_eq_88,
            "size_e0_eq_70_count": size_e0_eq_70,
            "cp_overlap_vs_70_88_any": cp_e0_overlap_any,
        },
        "rows": rows,
        "works": [
            "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
            f"result={result}",
            f"nonempty_e0={nonempty_e0} nonempty_e100={nonempty_e100}",
            f"verdicts_e0={dict(verdicts_e0)} verdicts_e100={dict(verdicts_e100)}",
            f"Assign sight {dict(sight['sight_counts'])} n={len(sight['assigns'])}",
        ],
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live leaf",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
            "named demangled RTTI for +0xe0/+0x100 elem VTs beyond catalog miss",
            "named movement-path proof for +0x70",
            "named CArmy path-field offsets",
            "HourlyTick abuse",
            "Capstone/121 re-churn",
            "NewFallback subject type-id table",
            "live midflight NewFallback hex",
            "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        ],
        "next_shortest_blocker": (
            "NON-Post: bounded NF/RF midflight OR war-dense named CArmy path OR "
            "demangle opaque +0xe0/+0x100 elem VTs; still NO ALLOW_POST"
        ),
    }
    (ROOT / "reports" / "phase2fz_e0_e100_identity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    briefs = []
    for r in rows:
        if not r.get("ok"):
            continue
        briefs.append({
            "oi": r["oi"] if "oi" in r else None,
            "n70": (r.get("size_rel") or {}).get("n70"),
            "n88": (r.get("size_rel") or {}).get("n88"),
            "e0_verdict": ((r.get("e0") or {}).get("reinterpretation") or {}).get("verdict"),
            "e0_size": (r.get("e0") or {}).get("size"),
            "e0_kinds": ((r.get("e0") or {}).get("reinterpretation") or {}).get("ptr_kinds"),
            "e0_handle_types": (r.get("e0") or {}).get("handle_type_hist"),
            "e0_cp_ids": (r.get("e0") or {}).get("province_ids_from_CProvince"),
            "e0_vs": r.get("e0_vs_70_88"),
            "e100_verdict": ((r.get("e100") or {}).get("reinterpretation") or {}).get("verdict"),
            "e100_size": (r.get("e100") or {}).get("size"),
            "e100_kinds": ((r.get("e100") or {}).get("reinterpretation") or {}).get("ptr_kinds"),
            "e100_handle_types": (r.get("e100") or {}).get("handle_type_hist"),
            "e100_cp_ids": (r.get("e100") or {}).get("province_ids_from_CProvince"),
            "size_rel": r.get("size_rel"),
            "e0_elems_head": ((r.get("e0") or {}).get("elems_sample") or [])[:4],
            "e100_elems_head": ((r.get("e100") or {}).get("elems_sample") or [])[:4],
        })
    # fix oi in briefs - rows have oi at top when ok
    for i, r in enumerate(rows):
        if r.get("ok") and i < len(briefs):
            # find matching
            pass
    # rebuild briefs with oi
    briefs = []
    for r in rows:
        if not r.get("ok"):
            continue
        # oi is not in the spread - need to track. Fix: store oi in loop above.
        pass

    # Re-derive briefs properly from rows — we lost oi. Re-read from file after fix.
    # Actually looking at code: out rows append {"oi": oi, "ok": True, **...} so oi is there.
    briefs = []
    for r in rows:
        if not r.get("ok"):
            continue
        briefs.append({
            "oi": r.get("oi"),
            "n70": (r.get("size_rel") or {}).get("n70"),
            "n88": (r.get("size_rel") or {}).get("n88"),
            "e0_verdict": ((r.get("e0") or {}).get("reinterpretation") or {}).get("verdict"),
            "e0_size": (r.get("e0") or {}).get("size"),
            "e0_kinds": ((r.get("e0") or {}).get("reinterpretation") or {}).get("ptr_kinds"),
            "e0_handle_types": (r.get("e0") or {}).get("handle_type_hist"),
            "e0_cp_ids": (r.get("e0") or {}).get("province_ids_from_CProvince"),
            "e0_vs": r.get("e0_vs_70_88"),
            "e100_verdict": ((r.get("e100") or {}).get("reinterpretation") or {}).get("verdict"),
            "e100_size": (r.get("e100") or {}).get("size"),
            "e100_kinds": ((r.get("e100") or {}).get("reinterpretation") or {}).get("ptr_kinds"),
            "e100_handle_types": (r.get("e100") or {}).get("handle_type_hist"),
            "size_rel": r.get("size_rel"),
            "e0_elems_head": ((r.get("e0") or {}).get("elems_sample") or [])[:3],
            "e100_elems_head": ((r.get("e100") or {}).get("elems_sample") or [])[:3],
        })

    summary = {k: out[k] for k in out if k != "rows"}
    summary["briefs"] = briefs
    (ROOT / "reports" / "phase2fz_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "live": meta,
        "aggregate": out["aggregate"],
        "briefs_nonempty": [x for x in briefs if x.get("e0_size") or x.get("e100_size")][:8],
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
