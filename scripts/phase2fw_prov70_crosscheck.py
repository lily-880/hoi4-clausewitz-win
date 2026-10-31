#!/usr/bin/env python3
"""Phase 2fw: confirm Instance+0x70 vs live army provinces/path (RO).
Light: OG+0x50 CArmy MI / army-handle cross; optional +0x88 peek.
No Post. Never 5x. allow_post False.
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
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = int(cmd_layout.ISVALID_PATHS["COrderReplaceFallbackCommands"]["vt"])

RTTI_VT = {
    "COrdersGroup": 0x29CED90,
    "COrdersGroupMember": 0x29CED48,
    "COrderInstance": 0x2A02558,
    "CArmy": 0x29D6D68,
    "CArmy_MI_0": 0x29D6F48,
    "CArmy_MI_1": 0x29D6FB8,
    "CArmy_MI_2": 0x29D7000,
}
TYPE_OG = 0x35
CA_PROVINCE_ID = 0x28
CA_PROVINCE_PTR = 0x1F0
CP_PROVINCE_ID = 0xA4
# MI subobject deltas to try (bytes back from MI VT ptr to primary CArmy*)
MI_DELTAS = [0, 8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70, 0x80, 0x90, 0xA0, 0xB0, 0xC0, 0x100, 0x110, 0x120, 0x128, 0x130, 0x138, 0x140, 0x148, 0x150, 0x158, 0x160, 0x180, 0x1A0, 0x1C0, 0x1E0, 0x1F0, 0x200]


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


def live_meta(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = struct.unpack("<i", b.read(gs + 0x484, 4))[0]
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "pid": find_pid(),
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x Instance+0x70 vs army provinces (no Post)",
        "gs": hex(gs),
    }


def rtti_name(b, base, obj):
    try:
        vt = u64(b, obj)
        rva = vt - base
        for k, v in RTTI_VT.items():
            if v == rva:
                return k, hex(rva)
        return None, hex(rva)
    except Exception:
        return None, None


def read_cpdx(b, base, addr):
    raw = try_read(b, addr, 0x18)
    if not raw or len(raw) < 0x18:
        return None
    data, cap, size = struct.unpack_from("<Qii", raw, 0)
    alloc = struct.unpack_from("<Q", raw, 0x10)[0]
    in_image = base <= data < base + b.image_size
    plausible = data > 0x10000 and 0 <= size <= 4096 and 0 <= cap <= 8192 and size <= cap
    return {
        "data": hex(data),
        "data_int": data,
        "capacity": cap,
        "size": size,
        "alloc": hex(alloc),
        "in_image_sentinel": bool(in_image),
        "plausible": bool(plausible),
    }


def read_u32_arr(b, data, size, max_n=64):
    n = min(size, max_n)
    if n <= 0 or data < 0x10000:
        return []
    blob = try_read(b, data, n * 4)
    if not blob:
        return []
    return [struct.unpack_from("<I", blob, i * 4)[0] for i in range(n)]


def read_ptr_arr(b, data, size, max_n=16):
    n = min(size, max_n)
    if n <= 0 or data < 0x10000:
        return []
    blob = try_read(b, data, n * 8)
    if not blob:
        return []
    return [struct.unpack_from("<Q", blob, i * 8)[0] for i in range(n)]


def looks_like_province_id(v: int) -> bool:
    return 1 <= v <= 20000


def army_province(b, base, army_idx):
    hdr = resolve_handle(b, HANDLE_TYPE_ARMY, army_idx, base)
    if not hdr:
        return {"army_index": army_idx, "resolve_ok": False}
    # handle.py returns header; body often hdr+0x10 or hdr itself — try both for CArmy VT
    body = None
    body_off = None
    for cand, offname in ((hdr + 0x10, "hdr+0x10"), (hdr, "hdr"), (hdr + 0x8, "hdr+0x8")):
        nm, rva = rtti_name(b, base, cand)
        if nm == "CArmy" or (rva and int(rva, 16) in (
            RTTI_VT["CArmy"], RTTI_VT["CArmy_MI_0"], RTTI_VT["CArmy_MI_1"], RTTI_VT["CArmy_MI_2"]
        )):
            body, body_off = cand, offname
            break
        # if primary VT not at cand, try MI adjust later
        if nm is None and rva:
            # still accept if primary nearby
            pass
    if body is None:
        # prefer hdr+0x10 as conventional
        body, body_off = hdr + 0x10, "hdr+0x10_default"
    nm, rva = rtti_name(b, base, body)
    # If MI VT at body, walk back to primary
    primary = body
    primary_delta = 0
    if rva and int(rva, 16) != RTTI_VT["CArmy"]:
        for d in MI_DELTAS:
            cand = body - d
            if cand < 0x10000:
                continue
            nm2, rva2 = rtti_name(b, base, cand)
            if nm2 == "CArmy":
                primary, primary_delta = cand, d
                nm, rva = nm2, rva2
                break
    pid_direct = None
    pid_via_ptr = None
    prov_ptr = None
    try:
        pid_direct = u32(b, primary + CA_PROVINCE_ID)
    except Exception:
        pass
    try:
        prov_ptr = u64(b, primary + CA_PROVINCE_PTR)
        if prov_ptr > 0x10000:
            pid_via_ptr = u32(b, prov_ptr + CP_PROVINCE_ID)
    except Exception:
        pass
    return {
        "army_index": army_idx,
        "resolve_ok": True,
        "header": hex(hdr),
        "body": hex(body),
        "body_off": body_off,
        "primary": hex(primary),
        "primary_delta": primary_delta,
        "rtti": nm,
        "vt_rva": rva,
        "province_id_plus28": pid_direct,
        "province_ptr": hex(prov_ptr) if prov_ptr else None,
        "province_id_via_1f0": pid_via_ptr,
        "province_id": pid_via_ptr if pid_via_ptr and looks_like_province_id(pid_via_ptr) else (
            pid_direct if pid_direct and looks_like_province_id(pid_direct) else None
        ),
    }


def stage_watch(b, base, seconds: float = 14.0):
    sess = u64(b, base + post_abi.G_SESSION)
    watch = {
        ASSIGN_VT: "COrderAssignCommand",
        NF_VT: "COrderNewFallbackCommand",
        RF_VT: "COrderReplaceFallbackCommands",
    }
    t0 = time.time()
    counts = {}
    assigns, nfs, rfs = [], [], []
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
            name = watch.get(rva)
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1
            key = (name, ptr)
            if key in seen:
                continue
            seen.add(key)
            t = round(time.time() - t0, 3)
            if name == "COrderAssignCommand" and len(assigns) < 12:
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
                assigns.append(
                    {
                        "addr": hex(ptr),
                        "t": t,
                        "order_index": oi,
                        "u32_plus40": hex(u32(b, ptr + 0x40)),
                        "units_size": size,
                        "army_indices": armies,
                    }
                )
            elif name == "COrderNewFallbackCommand" and len(nfs) < 3:
                raw = try_read(b, ptr, 0x60)
                sub = [u32(b, ptr + 0x28), u32(b, ptr + 0x2C)]
                nfs.append({"addr": hex(ptr), "t": t, "subject_handle": sub, "hex": raw.hex() if raw else None})
            elif name == "COrderReplaceFallbackCommands" and len(rfs) < 3:
                raw = try_read(b, ptr, 0x60)
                rfs.append({"addr": hex(ptr), "t": t, "hex": raw.hex() if raw else None})
    return {
        "elapsed_s": round(time.time() - t0, 1),
        "sight_counts": counts,
        "assigns": assigns,
        "fallbacks": nfs,
        "replace_fallbacks": rfs,
    }


def inst_from_og(b, base, oi):
    hdr = resolve_handle(b, TYPE_OG, oi, base)
    if not hdr:
        return None
    og = hdr + 0x10
    arr = read_cpdx(b, base, og + 0x98)
    if not arr or not arr["plausible"] or arr["size"] < 1:
        return {"order_index": oi, "og": hex(og), "inst": None}
    ptr = u64(b, arr["data_int"])
    return {"order_index": oi, "header": hex(hdr), "og": hex(og), "inst": ptr, "inst_hex": hex(ptr)}


def map_inst70_88(b, base, inst):
    out = {"inst": hex(inst)}
    nm, rva = rtti_name(b, base, inst)
    out["rtti"] = nm
    out["vt_rva"] = rva
    for off, key in ((0x70, "arr70"), (0x88, "arr88"), (0xE0, "arr_e0"), (0x100, "arr_100")):
        arr = read_cpdx(b, base, inst + off)
        if not arr or not arr["plausible"]:
            out[key] = None
            continue
        entry = {k: v for k, v in arr.items() if k != "data_int"}
        if arr["size"] > 0 and not arr["in_image_sentinel"]:
            if off == 0x70:
                entry["u32s"] = read_u32_arr(b, arr["data_int"], arr["size"], max_n=64)
                entry["all_province_shaped"] = all(looks_like_province_id(v) for v in entry["u32s"]) if entry["u32s"] else False
            else:
                ptrs = read_ptr_arr(b, arr["data_int"], arr["size"], max_n=12)
                entry["ptrs"] = [hex(p) for p in ptrs]
                typed = []
                for p in ptrs[:8]:
                    nm2, rva2 = rtti_name(b, base, p)
                    # MI walk for CArmy
                    primary = None
                    if rva2 and int(rva2, 16) in (RTTI_VT["CArmy_MI_1"], RTTI_VT["CArmy_MI_0"], RTTI_VT["CArmy_MI_2"]):
                        for d in MI_DELTAS:
                            cand = p - d
                            nm3, rva3 = rtti_name(b, base, cand)
                            if nm3 == "CArmy":
                                primary = {"delta": d, "primary": hex(cand), "rtti": nm3}
                                break
                    typed.append({"ptr": hex(p), "rtti": nm2, "vt_rva": rva2, "carmy_primary": primary})
                entry["elem_types"] = typed
        out[key] = entry
    return out


def type_og50_elem(b, base, ptr, og_int, inst_int):
    rec = {"ptr": hex(ptr)}
    nm, rva = rtti_name(b, base, ptr)
    rec["vt_rtti"] = nm
    rec["vt_rva"] = rva
    primary = None
    for d in MI_DELTAS:
        cand = ptr - d
        if cand < 0x10000:
            continue
        nm2, rva2 = rtti_name(b, base, cand)
        if nm2 == "CArmy":
            primary = {"delta": d, "primary": hex(cand), "rtti": nm2, "vt_rva": rva2}
            break
    rec["carmy_primary"] = primary
    # backrefs
    raw = try_read(b, ptr, 0x40) or b""
    if len(raw) >= 0x28:
        q8 = struct.unpack_from("<Q", raw, 0x8)[0]
        q20 = struct.unpack_from("<Q", raw, 0x20)[0]
        rec["plus08_is_og"] = q8 == og_int
        rec["plus20_is_inst"] = q20 == inst_int
    if primary:
        paddr = int(primary["primary"], 16)
        try:
            pid = u32(b, paddr + CA_PROVINCE_ID)
            prov = u64(b, paddr + CA_PROVINCE_PTR)
            pid2 = u32(b, prov + CP_PROVINCE_ID) if prov > 0x10000 else None
            rec["province_id_plus28"] = pid
            rec["province_id_via_1f0"] = pid2
            rec["province_id"] = pid2 if pid2 and looks_like_province_id(pid2) else (
                pid if looks_like_province_id(pid) else None
            )
        except Exception as e:
            rec["province_err"] = str(e)
    return rec


def crosscheck_row(b, base, oi, army_indices):
    link = inst_from_og(b, base, oi)
    if not link or not link.get("inst"):
        return {"order_index": oi, "ok": False, "note": "no instance"}
    arrays = map_inst70_88(b, base, link["inst"])
    armies = [army_province(b, base, ix) for ix in army_indices[:24]]
    army_provs = [a["province_id"] for a in armies if a.get("province_id") is not None]
    u32s = (arrays.get("arr70") or {}).get("u32s") or []
    set70 = set(u32s)
    set_army = set(army_provs)
    overlap = sorted(set70 & set_army)
    # position of army provinces in stream
    positions = {pid: [i for i, v in enumerate(u32s) if v == pid] for pid in army_provs}
    # OG+0x50
    og = int(link["og"], 16)
    arr50 = read_cpdx(b, base, og + 0x50)
    elems50 = []
    if arr50 and arr50["plausible"] and arr50["size"] > 0 and not arr50["in_image_sentinel"]:
        ptrs = read_ptr_arr(b, arr50["data_int"], arr50["size"], max_n=12)
        for p in ptrs:
            elems50.append(type_og50_elem(b, base, p, og, link["inst"]))
    # Does +0x50 army province match Instance+0x70 / assign armies?
    p50 = [e.get("province_id") for e in elems50 if e.get("province_id") is not None]
    return {
        "order_index": oi,
        "ok": True,
        "link": {k: v for k, v in link.items() if k != "inst"},
        "arrays": arrays,
        "armies": armies,
        "army_province_ids": army_provs,
        "inst70_u32s": u32s,
        "inst70_size": (arrays.get("arr70") or {}).get("size"),
        "inst70_all_province_shaped": (arrays.get("arr70") or {}).get("all_province_shaped"),
        "overlap_army_in_70": overlap,
        "overlap_count": len(overlap),
        "army_prov_count": len(set_army),
        "frac_army_provs_in_70": (len(overlap) / len(set_army)) if set_army else None,
        "army_prov_positions_in_70": positions,
        "og50": {
            "arr": {k: v for k, v in (arr50 or {}).items() if k != "data_int"} if arr50 else None,
            "elems": elems50,
            "province_ids": p50,
            "overlap_50_vs_70": sorted(set(p50) & set70),
            "overlap_50_vs_army": sorted(set(p50) & set_army),
            "carmy_primary_hits": sum(1 for e in elems50 if e.get("carmy_primary")),
        },
    }


def main():
    assert allow_post() is False
    b = Backend()
    base = b.image_base
    live = live_meta(b, base)
    print("LIVE", json.dumps(live), flush=True)

    sight = stage_watch(b, base, 14.0)
    print("SIGHT", sight.get("sight_counts"), "assigns", len(sight["assigns"]), flush=True)

    # Prefer assigns with armies; also include hist ois with nonempty +0x70
    rows = []
    seen_oi = set()
    for a in sight["assigns"]:
        oi = a["order_index"]
        if oi in seen_oi:
            continue
        seen_oi.add(oi)
        row = crosscheck_row(b, base, oi, a.get("army_indices") or [])
        row["assign_units_size"] = a.get("units_size")
        row["assign_army_indices"] = a.get("army_indices")
        row["u32_plus40"] = a.get("u32_plus40")
        rows.append(row)

    # If few army-bearing assigns, also probe focus ois from 2fv with empty army list (70-only)
    for oi in [5, 6, 17, 20, 25, 40, 44, 52]:
        if oi in seen_oi:
            continue
        # still map 70; armies empty unless we can pull from OG+0x50
        row = crosscheck_row(b, base, oi, [])
        # if og50 yielded carmy, use those province ids as "army-like"
        rows.append(row)
        seen_oi.add(oi)
        if len(rows) >= 10:
            break

    # Aggregate
    with_70 = [r for r in rows if r.get("ok") and (r.get("inst70_u32s") or [])]
    with_army = [r for r in rows if r.get("ok") and (r.get("army_province_ids") or [])]
    with_both = [r for r in rows if r.get("ok") and (r.get("inst70_u32s") or []) and (r.get("army_province_ids") or [])]
    overlap_stats = [
        {
            "oi": r["order_index"],
            "n70": len(r.get("inst70_u32s") or []),
            "n_army_prov": r.get("army_prov_count"),
            "overlap": r.get("overlap_count"),
            "frac": r.get("frac_army_provs_in_70"),
            "army_ids": r.get("army_province_ids"),
            "sample70": (r.get("inst70_u32s") or [])[:12],
        }
        for r in with_both
    ]
    carmy50_n = sum((r.get("og50") or {}).get("carmy_primary_hits", 0) for r in rows if r.get("ok"))
    # +0x88 types
    kind88 = Counter()
    for r in rows:
        if not r.get("ok"):
            continue
        for e in ((r.get("arrays") or {}).get("arr88") or {}).get("elem_types") or []:
            if e.get("carmy_primary"):
                kind88["carmy_via_mi"] += 1
            elif e.get("rtti"):
                kind88[e["rtti"]] += 1
            else:
                kind88["opaque_or_unknown_vt"] += 1

    # Verdict
    if with_both:
        fracs = [r["frac_army_provs_in_70"] for r in with_both if r.get("frac_army_provs_in_70") is not None]
        any_full = any(f == 1.0 for f in fracs)
        any_partial = any(f and f > 0 for f in fracs)
        if any_full:
            result = "inst70_contains_army_provinces"
            note = "all assigned-army current provinces appear in Instance+0x70 for ≥1 oi"
        elif any_partial:
            result = "inst70_partial_army_province_overlap"
            note = "partial overlap army provinces ∩ Instance+0x70"
        else:
            result = "inst70_no_army_province_overlap"
            note = "Instance+0x70 nonempty but no overlap with assigned army current provinces"
    elif with_70 and not with_army:
        result = "inst70_mapped_no_assign_armies"
        note = "had +0x70 streams but no Assign army subjects to cross this window"
    else:
        result = "inst70_crosscheck_thin"
        note = "insufficient live +0x70 and/or army resolves"

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"stage sight {sight.get('sight_counts')} assigns={len(sight['assigns'])}",
        f"rows_ok={sum(1 for r in rows if r.get('ok'))} with_70={len(with_70)} with_army_prov={len(with_army)} with_both={len(with_both)}",
        f"result_note: {note}",
        f"overlap_stats: {overlap_stats}",
        f"OG+0x50 carmy_primary_hits_total={carmy50_n}",
        f"Instance+0x88 elem kinds: {dict(kind88)}",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "path-vector nonempty confirm as named path field",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "NewFallback subject type-id table",
        "live midflight NewFallback hex",
        "order_index→COrderInstance pool-slot arithmetic",
        "stable G_GAMESTATE→pool root pointer path",
        "full G_GAMESTATE→type-0x35-reg owner path",
        "named Instance +0x88/+0xe0/+0x100 field names",
        "demangled RTTI string dump for VT 0x29d6fb8 beyond WINDOWS_OFFSETS CArmy MI catalog",
    ]
    if result in ("inst70_contains_army_provinces", "inst70_partial_army_province_overlap"):
        next_b = (
            "NON-Post: deepen Instance+0x88 identity OR settle +0x70 as path vs garrison-list "
            "OR bounded NF/RF subject; still NO ALLOW_POST"
        )
    elif result == "inst70_no_army_province_overlap":
        next_b = (
            "NON-Post: reinterpret Instance+0x70 (not current-province list) OR deepen +0x88 "
            "OR bounded NF/RF; still NO ALLOW_POST"
        )
    else:
        next_b = (
            "NON-Post: re-run +0x70 cross when Assign carries armies OR deepen +0x88 "
            "OR bounded NF/RF; still NO ALLOW_POST"
        )

    out = {
        "result": result,
        "result_note": note,
        "allow_post": False,
        "live": live,
        "sight": sight,
        "rows": rows,
        "aggregate": {
            "with_70": len(with_70),
            "with_army": len(with_army),
            "with_both": len(with_both),
            "overlap_stats": overlap_stats,
            "carmy50_primary_hits": carmy50_n,
            "kind88": dict(kind88),
        },
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "phase2fw_prov70_crosscheck.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    summary = {
        "result": result,
        "result_note": note,
        "allow_post": False,
        "live": live,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "aggregate": out["aggregate"],
    }
    (reports / "phase2fw_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("RESULT", result, note, flush=True)
    print("overlap_stats", json.dumps(overlap_stats), flush=True)
    print("carmy50", carmy50_n, "kind88", dict(kind88), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
