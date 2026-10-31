#!/usr/bin/env python3
"""Phase 2fy: prove/refute Instance+0x70 vs CArmy path/history (RO).
Light: Instance+0xe0/+0x100 peek. No Post. Never 5x. allow_post False.
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
CA_MI = (0x29D6F48, 0x29D6FB8, 0x29D7000)
CA_PROVINCE_ID = 0x28
CA_PROVINCE_PTR = 0x1F0
CP_PROVINCE_ID = 0xA4
CP_VT = 0x29EE248
MAX_SIGHT_S = 10.0
MAX_ARR = 256
# subject+0x2b4 last-path dword note from WINDOWS_OFFSETS (candidate only)
CA_LAST_PATH_CAND = 0x2B4
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


def looks_like_province_id(v: int) -> bool:
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
        "scenario": "ITA@1x Instance+0x70 vs CArmy path/history (no Post)",
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
            assigns.append({"order_index": oi, "army_indices": armies, "t": round(time.time() - t0, 3)})
    return {"elapsed_s": round(time.time() - t0, 1), "sight_counts": dict(counts), "assigns": assigns}


def resolve_carmy(b, base, army_idx):
    hdr = resolve_handle(b, HANDLE_TYPE_ARMY, army_idx, base)
    if not hdr:
        return None
    body = hdr + 0x10
    primary = None
    primary_delta = None
    body_off = 0x10
    # try body and body candidates
    for delta in [0] + MI_DELTAS:
        cand = body - delta if delta else body
        # also try hdr+delta styles
        for addr in (cand, body, hdr + 0x10):
            try:
                vt = u64(b, addr) - base
            except Exception:
                continue
            if vt == CA_VT:
                primary = addr
                primary_delta = (body - addr) if addr != body else 0
                break
            if vt in CA_MI:
                for d2 in MI_DELTAS:
                    try:
                        p2 = addr - d2
                        if u64(b, p2) - base == CA_VT:
                            primary = p2
                            primary_delta = d2
                            break
                    except Exception:
                        continue
            if primary:
                break
        if primary:
            break
    if not primary:
        # last try: hdr+0x10 VT check with walk
        try:
            vt = u64(b, body) - base
            if vt in CA_MI or vt == CA_VT:
                if vt == CA_VT:
                    primary = body
                    primary_delta = 0
                else:
                    for d2 in MI_DELTAS:
                        try:
                            if u64(b, body - d2) - base == CA_VT:
                                primary = body - d2
                                primary_delta = d2
                                break
                        except Exception:
                            pass
        except Exception:
            pass
    if not primary:
        return {"army_index": army_idx, "resolve_ok": False, "header": hex(hdr)}
    pid_direct = None
    pid_via = None
    try:
        pid_direct = u32(b, primary + CA_PROVINCE_ID)
    except Exception:
        pass
    try:
        pp = u64(b, primary + CA_PROVINCE_PTR)
        if pp > 0x10000:
            pid_via = u32(b, pp + CP_PROVINCE_ID)
    except Exception:
        pass
    last_path_cand = None
    try:
        v = u32(b, primary + CA_LAST_PATH_CAND)
        if looks_like_province_id(v):
            last_path_cand = v
    except Exception:
        pass
    return {
        "army_index": army_idx,
        "resolve_ok": True,
        "primary": hex(primary),
        "primary_int": primary,
        "primary_delta": primary_delta,
        "province_id": pid_via if pid_via and looks_like_province_id(pid_via) else (
            pid_direct if pid_direct and looks_like_province_id(pid_direct) else None
        ),
        "province_id_plus28": pid_direct,
        "province_id_via_1f0": pid_via,
        "last_path_cand_2b4": last_path_cand,
    }


def read_u32_stdvec(b, begin, end, cap, max_n=64):
    if not begin or not end or end < begin:
        return None
    nbytes = end - begin
    if nbytes % 4 != 0 or nbytes > max_n * 4 or nbytes == 0:
        return None
    if cap and cap < end:
        return None
    blob = try_read(b, begin, nbytes)
    if not blob or len(blob) != nbytes:
        return None
    return list(struct.unpack("<" + "I" * (nbytes // 4), blob))


def scan_army_path_cands(b, base, primary, current_prov):
    """Scan CArmy for std::vector<u32> and CPdxArray u32 province-id streams (RO)."""
    blob = try_read(b, primary, 0x800) or b""
    cands = []
    # std::vector begin/end/cap
    for off in range(0x40, min(len(blob) - 24, 0x780), 8):
        begin, end, cap = struct.unpack_from("<QQQ", blob, off)
        if begin < 0x10000 or end < begin:
            continue
        vals = read_u32_stdvec(b, begin, end, cap, max_n=64)
        if not vals or not all(looks_like_province_id(v) for v in vals):
            continue
        cands.append({
            "kind": "stdvec_u32",
            "off": hex(off),
            "n": len(vals),
            "province_ids": vals,
            "matches_current_only": vals == [current_prov] if current_prov is not None else False,
        })
    # CPdxArray data/cap/size
    for off in range(0x40, min(len(blob) - 24, 0x780), 8):
        data, cap, size = struct.unpack_from("<Qii", blob, off)
        if data < 0x10000 or size <= 0 or size > 64 or size > max(cap, size):
            continue
        if base <= data < base + b.image_size:
            continue  # sentinel
        blob2 = try_read(b, data, size * 4)
        if not blob2:
            continue
        vals = [struct.unpack_from("<I", blob2, i * 4)[0] for i in range(size)]
        if not all(looks_like_province_id(v) for v in vals):
            continue
        # de-dupe vs stdvec at same off
        if any(c["off"] == hex(off) for c in cands):
            continue
        cands.append({
            "kind": "cpdx_u32",
            "off": hex(off),
            "n": len(vals),
            "province_ids": vals,
            "matches_current_only": vals == [current_prov] if current_prov is not None else False,
        })
    useful = [c for c in cands if not c["matches_current_only"] or c["n"] > 1]
    return useful if useful else cands


def read_inst70(b, base, oi):
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
    out = {"oi": oi, "vt_ok": True, "inst": hex(inst), "inst_int": inst, "og": hex(og)}
    for off, key in ((0x70, "arr70"), (0x88, "arr88"), (0xE0, "arr_e0"), (0x100, "arr_100")):
        arr = read_cpdx(b, base, inst + off)
        if not arr or not arr["plausible"]:
            out[key] = None
            continue
        info = {k: arr[k] for k in ("size", "cap", "plausible", "sentinel", "data")}
        info["data_hex"] = hex(arr["data"])
        if arr["size"] > 0 and not arr["sentinel"]:
            # try u32 stream
            n = min(arr["size"], MAX_ARR)
            blob = try_read(b, arr["data"], n * 4)
            u32s = []
            if blob and len(blob) >= n * 4:
                u32s = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(n)]
            info["u32_stream"] = u32s
            info["u32_all_province_shaped"] = bool(u32s) and all(looks_like_province_id(v) for v in u32s)
            # try ptr stream + VT
            blobp = try_read(b, arr["data"], min(arr["size"], 32) * 8)
            ptr_kinds = Counter()
            ptr_ids = []
            if blobp:
                for i in range(min(arr["size"], 32)):
                    p = struct.unpack_from("<Q", blobp, i * 8)[0]
                    if p < 0x10000:
                        ptr_kinds["nullish"] += 1
                        continue
                    try:
                        vr = u64(b, p) - base
                    except Exception:
                        ptr_kinds["unreadable"] += 1
                        continue
                    if vr == CP_VT:
                        ptr_kinds["CProvince"] += 1
                        try:
                            ptr_ids.append(u32(b, p + CP_PROVINCE_ID))
                        except Exception:
                            ptr_ids.append(None)
                    elif vr == CA_VT:
                        ptr_kinds["CArmy"] += 1
                    elif vr == INST_VT:
                        ptr_kinds["COrderInstance"] += 1
                    else:
                        ptr_kinds[f"vt_{hex(vr)}"] += 1
            info["ptr_kinds"] = dict(ptr_kinds)
            info["ptr_province_ids_sample"] = ptr_ids[:16]
        out[key] = info
    return out


def cross(u32s70, path_ids, current_prov, last_2b4):
    set70 = set(u32s70 or [])
    setp = set(path_ids or [])
    out = {
        "n70": len(u32s70 or []),
        "n_path": len(path_ids or []),
        "equal": (u32s70 or []) == (path_ids or []) and bool(u32s70),
        "equal_as_sets": set70 == setp and bool(set70),
        "70_subset_path": set70 <= setp and bool(set70),
        "path_subset_70": setp <= set70 and bool(setp),
        "overlap": sorted(set70 & setp),
        "frac_70_in_path": (len(set70 & setp) / len(set70)) if set70 else None,
        "frac_path_in_70": (len(set70 & setp) / len(setp)) if setp else None,
        "path_last_eq_70_last": bool(u32s70) and bool(path_ids) and u32s70[-1] == path_ids[-1],
        "current_in_70": current_prov in set70 if current_prov is not None else None,
        "last2b4_in_70": last_2b4 in set70 if last_2b4 is not None else None,
        "last2b4_eq_70_last": bool(u32s70) and last_2b4 == u32s70[-1] if last_2b4 is not None else None,
    }
    # subsequence checks
    def is_subseq(a, b):
        it = iter(b)
        return all(x in it for x in a)

    out["70_subseq_of_path"] = is_subseq(u32s70 or [], path_ids or []) if u32s70 and path_ids else False
    out["path_subseq_of_70"] = is_subseq(path_ids or [], u32s70 or []) if u32s70 and path_ids else False
    return out


def main():
    b = Backend()
    base = b.image_base
    meta = live_meta(b, base)
    sight = stage_watch(b, base)
    print("SIGHT", sight["sight_counts"], "assigns", len(sight["assigns"]), flush=True)

    # seed ois from assigns + prior nonempty
    oi_armies = {}
    for a in sight["assigns"]:
        oi_armies.setdefault(int(a["order_index"]), set()).update(a["army_indices"])
    for oi in (5, 6, 7, 9, 13, 17, 20, 22, 25, 38, 40, 44, 68, 70):
        oi_armies.setdefault(oi, set())

    rows = []
    path_nonempty_armies = 0
    with_70 = 0
    with_both = 0  # 70 + any useful path cand
    equal_hits = 0
    overlap_hits = 0

    for oi, armies in sorted(oi_armies.items()):
        inst = read_inst70(b, base, oi)
        if not inst or not inst.get("vt_ok"):
            rows.append({"oi": oi, "ok": False, "inst": inst})
            continue
        u32s70 = ((inst.get("arr70") or {}).get("u32_stream")) or []
        if u32s70 and (inst["arr70"] or {}).get("u32_all_province_shaped"):
            with_70 += 1
        else:
            u32s70 = u32s70 if u32s70 else []

        army_rows = []
        for aidx in sorted(armies)[:8]:
            ca = resolve_carmy(b, base, aidx)
            if not ca or not ca.get("resolve_ok"):
                army_rows.append({"army_index": aidx, "resolve_ok": False})
                continue
            cands = scan_army_path_cands(b, base, ca["primary_int"], ca.get("province_id"))
            useful = [c for c in cands if not c["matches_current_only"]]
            if useful:
                path_nonempty_armies += 1
            best = useful[0] if useful else (cands[0] if cands else None)
            xr = None
            if best and u32s70:
                xr = cross(u32s70, best["province_ids"], ca.get("province_id"), ca.get("last_path_cand_2b4"))
                if xr["equal"] or xr["equal_as_sets"] or xr["70_subseq_of_path"] or xr["path_subseq_of_70"]:
                    equal_hits += 1
                if xr["overlap"]:
                    overlap_hits += 1
            # also cross last2b4 alone
            if u32s70 and ca.get("last_path_cand_2b4") is not None and xr is None:
                xr = cross(u32s70, [], ca.get("province_id"), ca.get("last_path_cand_2b4"))
            army_rows.append({
                **{k: ca[k] for k in ca if k != "primary_int"},
                "path_cands": cands[:6],
                "best_path": best,
                "cross_vs_70": xr,
            })

        if u32s70 and any((a.get("best_path") and not a["best_path"].get("matches_current_only")) for a in army_rows):
            with_both += 1

        rows.append({
            "oi": oi,
            "ok": True,
            "n70": len(u32s70),
            "u32s70_sample": u32s70[:16],
            "u32s70": u32s70,
            "arr70": {k: inst["arr70"][k] for k in ("size", "cap", "u32_all_province_shaped") if inst.get("arr70") and k in inst["arr70"]} if inst.get("arr70") else None,
            "arr_e0": inst.get("arr_e0"),
            "arr_100": inst.get("arr_100"),
            "army_indices": sorted(armies),
            "armies": army_rows,
        })

    # Aggregate result (honest)
    nonempty70 = [r for r in rows if r.get("ok") and r.get("n70")]
    any_path = path_nonempty_armies > 0
    if nonempty70 and not any_path:
        result = "inst70_populated_while_army_path_vectors_empty"
        note = (
            f"+0x70 nonempty on {len(nonempty70)} ois while assigned CArmy path-vector candidates "
            f"(beyond current-province echo) are empty — evidence against +0x70 being live midflight "
            f"CArmy movement path this window; consistent with order/front geometry (2fx). "
            f"last_path_cand@+0x2b4 checked as province-shaped when present."
        )
    elif nonempty70 and equal_hits > 0:
        result = "inst70_matches_army_path_candidate"
        note = f"equal/subseq hits={equal_hits} on with_both-ish; see rows — still candidate until named"
    elif nonempty70 and overlap_hits > 0:
        result = "inst70_partial_overlap_army_path_candidate"
        note = f"overlap_hits={overlap_hits}; not equal — document mismatch"
    elif nonempty70 and any_path:
        result = "inst70_no_overlap_with_army_path_candidates"
        note = "path cands nonempty but no overlap with +0x70"
    else:
        result = "inst70_army_path_crosscheck_thin"
        note = "few/no +0x70 streams this window"

    # e0/100 summary
    e0_kinds = Counter()
    e100_kinds = Counter()
    for r in rows:
        if not r.get("ok"):
            continue
        for key, ctr in (("arr_e0", e0_kinds), ("arr_100", e100_kinds)):
            arr = r.get(key)
            if not arr or not arr.get("size"):
                ctr["empty_or_absent"] += 1
                continue
            if arr.get("u32_all_province_shaped"):
                ctr["u32_province_stream"] += 1
            pk = arr.get("ptr_kinds") or {}
            if pk.get("CProvince"):
                ctr["ptr_CProvince"] += 1
            elif pk:
                ctr["ptr_other"] += 1
            else:
                ctr["opaque"] += 1

    out = {
        "phase": "2fy",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta,
        "sight": {"sight_counts": sight["sight_counts"], "n_assigns": len(sight["assigns"]), "elapsed_s": sight["elapsed_s"]},
        "aggregate": {
            "ois": len(rows),
            "with_70": with_70,
            "path_nonempty_armies": path_nonempty_armies,
            "with_both": with_both,
            "equal_or_subseq_hits": equal_hits,
            "overlap_hits": overlap_hits,
            "e0_kinds": dict(e0_kinds),
            "e100_kinds": dict(e100_kinds),
        },
        "rows": rows,
        "works": [
            "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
            f"result={result}",
            f"with_70={with_70} path_nonempty_armies={path_nonempty_armies} with_both={with_both}",
            f"Assign sight {dict(sight['sight_counts'])} n={len(sight['assigns'])}",
            f"e0_kinds={dict(e0_kinds)} e100_kinds={dict(e100_kinds)}",
        ],
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live leaf",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
            "path-vector nonempty as named CArmy field (offsets still candidates)",
            "named movement-path proof for +0x70",
            "HourlyTick abuse",
            "Capstone/121 re-churn",
            "NewFallback subject type-id table",
            "live midflight NewFallback hex",
            "named Instance +0xe0/+0x100 beyond kind peek",
            "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        ],
        "next_shortest_blocker": (
            "NON-Post: if paths empty, deepen +0xe0/+0x100 OR bounded NF/RF midflight OR "
            "war-dense relaunch for nonempty CArmy path; still NO ALLOW_POST"
        ),
    }
    (ROOT / "reports" / "phase2fy_army_path_vs_70.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    summary = {k: out[k] for k in out if k != "rows"}
    summary["row_briefs"] = []
    for r in rows:
        if not r.get("ok"):
            continue
        abriefs = []
        for a in r.get("armies") or []:
            if not a.get("resolve_ok"):
                continue
            bp = a.get("best_path")
            abriefs.append({
                "army": a.get("army_index"),
                "prov": a.get("province_id"),
                "last2b4": a.get("last_path_cand_2b4"),
                "n_cands": len(a.get("path_cands") or []),
                "best_n": (bp or {}).get("n"),
                "best_off": (bp or {}).get("off"),
                "best_sample": ((bp or {}).get("province_ids") or [])[:8],
                "cross": a.get("cross_vs_70"),
            })
        summary["row_briefs"].append({
            "oi": r["oi"],
            "n70": r.get("n70"),
            "sample70": (r.get("u32s70_sample") or [])[:10],
            "e0_size": (r.get("arr_e0") or {}).get("size"),
            "e0_ptr_kinds": (r.get("arr_e0") or {}).get("ptr_kinds"),
            "e0_u32_prov": (r.get("arr_e0") or {}).get("u32_all_province_shaped"),
            "e100_size": (r.get("arr_100") or {}).get("size"),
            "e100_ptr_kinds": (r.get("arr_100") or {}).get("ptr_kinds"),
            "e100_u32_prov": (r.get("arr_100") or {}).get("u32_all_province_shaped"),
            "armies": abriefs,
        })
    (ROOT / "reports" / "phase2fy_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "live": meta,
        "aggregate": out["aggregate"],
        "briefs": summary["row_briefs"][:8],
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
