#!/usr/bin/env python3
"""Phase 2fu: map COrdersGroup internals (arrays/members) for path/units (RO).
Also short COrderInstance re-probe. No Post. Never 5x. allow_post stays False.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
import cmd_layout
import post_abi
from handle import resolve_handle, HANDLE_TYPE_ARMY, HANDLE_TYPE_TABLE

assert allow_post() is False, "allow_post must stay False"

ASSIGN_VT = cmd_layout.ORDERS["COrderAssignCommand"]["vt"]
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = int(cmd_layout.ISVALID_PATHS["COrderReplaceFallbackCommands"]["vt"])

RTTI_VT = {
    "COrdersGroup": 0x29CED90,
    "COrdersGroupMember": 0x29CED48,
    "COrderInstance": 0x2A02558,
}
RTTI_BY_RVA = {v: k for k, v in RTTI_VT.items()}
TYPE_OG = 0x35
STRIDE = 0x3D0
# CPdxArray proven: data@0 cap@8 size@0xC alloc@0x10 (2fm/2fn)
ARRAY_OFFS = [0x18, 0x30, 0x48, 0x50, 0x68, 0x80, 0x98]
HIST_OI = [1, 6, 9, 10, 12, 25, 33]
FOCUS_OI = [1, 10, 33]


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
        "scenario": "ITA@1x COrdersGroup internals map (no Post)",
        "gs": hex(gs),
    }


def rtti_at(b, base, obj):
    try:
        vt = u64(b, obj)
        rva = vt - base
        return RTTI_BY_RVA.get(rva), hex(rva)
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
        "in_image_sentinel": in_image,
        "plausible": plausible,
    }


def classify_elem(b, base, ptr_or_handle_q):
    """Classify one 8-byte element: RTTI object, handle pair, or opaque."""
    typ = ptr_or_handle_q & 0xFFFFFFFF
    idx = (ptr_or_handle_q >> 32) & 0xFFFFFFFF
    # handle-shaped if type small
    if typ < 0x64 and idx < 0x100000:
        resolved = None
        rtti = None
        try:
            resolved = resolve_handle(b, typ, idx, base)
        except Exception:
            pass
        if resolved:
            # for 0x35, object body at +0x10
            body = resolved + 0x10 if typ == TYPE_OG else resolved
            # army resolve returns header-0x10? handle.py returns ptr-0x10 always
            nm, rva = rtti_at(b, base, resolved + 0x10)
            if not nm:
                nm, rva = rtti_at(b, base, resolved)
            return {
                "kind": "handle",
                "type": typ,
                "type_hex": hex(typ),
                "index": idx,
                "resolved_header": hex(resolved),
                "body_rtti": nm,
                "body_vt_rva": rva,
            }
        return {"kind": "handle_unresolved", "type": typ, "type_hex": hex(typ), "index": idx}
    # pointer-shaped
    if ptr_or_handle_q > 0x10000:
        nm, rva = rtti_at(b, base, ptr_or_handle_q)
        if nm:
            return {"kind": "rtti_ptr", "ptr": hex(ptr_or_handle_q), "rtti": nm, "vt_rva": rva}
        # maybe points to header before RTTI
        nm2, rva2 = rtti_at(b, base, ptr_or_handle_q + 0x10)
        if nm2:
            return {
                "kind": "rtti_ptr_plus10",
                "ptr": hex(ptr_or_handle_q),
                "rtti": nm2,
                "vt_rva": rva2,
            }
        return {"kind": "opaque_ptr", "ptr": hex(ptr_or_handle_q)}
    return {"kind": "small", "raw": hex(ptr_or_handle_q)}


def dump_array_elems(b, base, arr, max_n=16, elem_stride=8):
    if not arr or not arr["plausible"] or arr["size"] <= 0:
        return []
    n = min(arr["size"], max_n)
    blob = try_read(b, arr["data_int"], n * elem_stride)
    if not blob:
        return []
    out = []
    for i in range(n):
        if elem_stride == 8:
            q = struct.unpack_from("<Q", blob, i * 8)[0]
            # also try as two u32
            t, ix = struct.unpack_from("<II", blob, i * 8)
            rec = {"i": i, "qword": hex(q), "as_u32_pair": [t, ix]}
            rec["class"] = classify_elem(b, base, q)
            # alternate: if looks like two u32 handle packed little-endian type then index
            if t < 0x64:
                rec["class_as_handle_le"] = classify_elem(
                    b, base, (ix << 32) | t
                )  # already same as q if layout is type|index
            out.append(rec)
        elif elem_stride == 4:
            v = struct.unpack_from("<I", blob, i * 4)[0]
            out.append({"i": i, "u32": v, "u32_hex": hex(v)})
    return out


def map_og(b, base, oi):
    hdr = resolve_handle(b, TYPE_OG, oi, base)
    if not hdr:
        return {"order_index": oi, "resolve_ok": False}
    og = hdr + 0x10
    nm, rva = rtti_at(b, base, og)
    blob = try_read(b, og, 0xC0)
    arrays = {}
    for off in ARRAY_OFFS:
        arr = read_cpdx(b, base, og + off)
        if not arr:
            continue
        entry = {"off": hex(off), **{k: v for k, v in arr.items() if k != "data_int"}}
        # element dumps for plausible non-empty
        if arr["plausible"] and arr["size"] > 0 and not arr["in_image_sentinel"]:
            entry["elems8"] = dump_array_elems(b, base, arr, max_n=12, elem_stride=8)
            # also try as u32 stream (province path?)
            entry["elems4_head"] = dump_array_elems(b, base, arr, max_n=16, elem_stride=4)
        arrays[hex(off)] = entry
    # scan first 0xC0 for direct Member VT pointers
    member_hits = []
    vt_mem = base + RTTI_VT["COrdersGroupMember"]
    if blob:
        for off in range(0, len(blob) - 7, 8):
            q = struct.unpack_from("<Q", blob, off)[0]
            if q == vt_mem:
                member_hits.append({"off": hex(off), "kind": "embedded_vt"})
            elif q > 0x10000:
                raw = try_read(b, q, 8)
                if raw and struct.unpack("<Q", raw)[0] == vt_mem:
                    member_hits.append({"off": hex(off), "ptr": hex(q), "kind": "ptr_to_member"})
    # header echo
    echo = list(struct.unpack("<II", b.read(hdr + 0x18, 8)))
    t8, i8 = struct.unpack("<II", b.read(og + 0x8, 8))
    return {
        "order_index": oi,
        "resolve_ok": True,
        "header": hex(hdr),
        "og": hex(og),
        "og_rtti": nm,
        "og_vt_rva": rva,
        "echo": echo,
        "plus8_type": t8,
        "plus0c_index": i8,
        "arrays": arrays,
        "member_hits": member_hits,
        "u32_0x00_0x60": [hex(struct.unpack_from("<I", blob, i)[0]) for i in range(0, min(0x60, len(blob or b"")), 4)]
        if blob
        else [],
    }


def writable_regions(b, base):
    out = []
    for m in b.regions():
        if "w" not in (m.get("perms") or ""):
            continue
        start, end = m["start"], m["end"]
        if base <= start < base + b.image_size:
            continue
        if end - start < 0x1000:
            continue
        out.append((start, end))
    return out


def heap_scan_vt(b, base, needles, max_samples=32, chunk=4 << 20, time_budget_s=30.0):
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    t0 = time.time()
    packed = {k: struct.pack("<Q", base + rva) for k, rva in needles.items()}
    for start, end in writable_regions(b, base):
        if time.time() - t0 > time_budget_s:
            break
        pos = start
        while pos < end:
            if time.time() - t0 > time_budget_s:
                break
            nread = min(chunk, end - pos)
            data = try_read(b, pos, nread)
            scanned += nread
            if data:
                for k, needle in packed.items():
                    off = 0
                    while True:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            counts[k] += 1
                            if len(samples[k]) < max_samples:
                                samples[k].append(pos + i)
                        off = i + 8
            pos += nread
    return {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 1),
        "counts": counts,
        "samples": {k: [hex(x) for x in v] for k, v in samples.items()},
        "sample_addrs": samples,
    }


def stage_watch(b, base, seconds: float):
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
            if name == "COrderAssignCommand" and len(assigns) < 10:
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
            elif name == "COrderNewFallbackCommand" and len(nfs) < 4:
                raw = try_read(b, ptr, 0x60)
                sub = [u32(b, ptr + 0x28), u32(b, ptr + 0x2C)]
                nfs.append(
                    {
                        "addr": hex(ptr),
                        "t": t,
                        "subject_handle": sub,
                        "subject_type_hex": hex(sub[0]),
                        "hex": raw.hex() if raw else None,
                    }
                )
            elif name == "COrderReplaceFallbackCommands" and len(rfs) < 4:
                raw = try_read(b, ptr, 0x60)
                rfs.append({"addr": hex(ptr), "t": t, "hex": raw.hex() if raw else None})
    return {
        "elapsed_s": round(time.time() - t0, 1),
        "sight_counts": counts,
        "assigns": assigns,
        "fallbacks": nfs,
        "replace_fallbacks": rfs,
    }


def expand_pool(b, base, seeds):
    vt_abs = base + RTTI_VT["COrderInstance"]
    found = set(seeds)
    changed = True
    while changed:
        changed = False
        for a in list(found):
            for cand in (a - STRIDE, a + STRIDE):
                if cand in found or cand <= 0x10000:
                    continue
                blob = try_read(b, cand, 8)
                if not blob:
                    continue
                if struct.unpack("<Q", blob)[0] == vt_abs:
                    found.add(cand)
                    changed = True
    addrs = sorted(found)
    return {
        "stride": hex(STRIDE),
        "addrs": [hex(x) for x in addrs],
        "len": len(addrs),
        "base": hex(addrs[0]) if addrs else None,
    }


def summarize_progress(maps, army_by_oi):
    """Detect real documented progress: non-empty heap arrays with classified elems."""
    nonempty = 0
    member_elems = 0
    handle_elems = 0
    army_overlap = []
    for m in maps:
        if not m.get("resolve_ok"):
            continue
        for off, arr in (m.get("arrays") or {}).items():
            if arr.get("plausible") and arr.get("size", 0) > 0 and not arr.get("in_image_sentinel"):
                nonempty += 1
                for e in arr.get("elems8") or []:
                    cls = e.get("class") or {}
                    if cls.get("rtti") == "COrdersGroupMember" or cls.get("body_rtti") == "COrdersGroupMember":
                        member_elems += 1
                    if cls.get("kind") in ("handle", "handle_unresolved") or e.get("class_as_handle_le", {}).get(
                        "kind"
                    ) in ("handle", "handle_unresolved"):
                        handle_elems += 1
                    # army index overlap
                    oi = m["order_index"]
                    armies = set(army_by_oi.get(oi) or [])
                    if cls.get("kind") == "handle" and cls.get("type") == HANDLE_TYPE_ARMY:
                        if cls.get("index") in armies:
                            army_overlap.append({"oi": oi, "army": cls["index"], "via": off})
                    le = e.get("class_as_handle_le") or {}
                    if le.get("kind") == "handle" and le.get("type") == HANDLE_TYPE_ARMY:
                        if le.get("index") in armies:
                            army_overlap.append({"oi": oi, "army": le["index"], "via": off, "le": True})
    return {
        "nonempty_heap_arrays": nonempty,
        "member_classified_elems": member_elems,
        "handle_classified_elems": handle_elems,
        "army_overlap": army_overlap,
    }


def main():
    pid = find_pid()
    b = Backend(pid)
    base = b.image_base
    live0 = live_meta(b, base)
    print(f"[2fu] live {live0['ui_date']} pid {pid}", flush=True)
    assert allow_post() is False

    print("[2fu] stage Assign/NF 20s…", flush=True)
    sight = stage_watch(b, base, 20.0)
    live_ois = sorted({a["order_index"] for a in sight["assigns"]})
    army_by_oi = {}
    for a in sight["assigns"]:
        army_by_oi.setdefault(a["order_index"], [])
        for ix in a.get("army_indices") or []:
            if ix not in army_by_oi[a["order_index"]]:
                army_by_oi[a["order_index"]].append(ix)
    print(f"[2fu] sight {sight['sight_counts']} live_ois={live_ois}", flush=True)

    probe_ois = sorted(set(FOCUS_OI) | set(live_ois) | set(HIST_OI))
    # prioritize focus + live
    probe_ois = sorted(set(FOCUS_OI) | set(live_ois)) + [
        x for x in HIST_OI if x not in set(FOCUS_OI) | set(live_ois)
    ]
    print(f"[2fu] map OG internals for {probe_ois}…", flush=True)
    maps = [map_og(b, base, oi) for oi in probe_ois]
    prog = summarize_progress(maps, army_by_oi)
    print(
        f"[2fu] resolve_ok={sum(1 for m in maps if m.get('resolve_ok'))} "
        f"nonempty_arrays={prog['nonempty_heap_arrays']} members={prog['member_classified_elems']} "
        f"handles={prog['handle_classified_elems']} army_overlap={len(prog['army_overlap'])}",
        flush=True,
    )

    print("[2fu] heap Instance ≤30s…", flush=True)
    heap = heap_scan_vt(
        b,
        base,
        {
            "COrderInstance": RTTI_VT["COrderInstance"],
            "COrdersGroupMember": RTTI_VT["COrdersGroupMember"],
        },
        time_budget_s=30.0,
    )
    print(f"[2fu] heap {heap['counts']}", flush=True)
    pool = expand_pool(b, base, heap["sample_addrs"].get("COrderInstance", []))
    index_map = {"ok": False, "reason": "empty pool"}
    if pool["len"] > 0 and (live_ois or FOCUS_OI):
        ois = live_ois or FOCUS_OI
        pbase = int(pool["base"], 16)
        hits = []
        for oi in ois:
            slot = pbase + oi * STRIDE
            blob = try_read(b, slot, 8)
            vt_ok = bool(blob) and struct.unpack("<Q", blob)[0] == base + RTTI_VT["COrderInstance"]
            hits.append({"oi": oi, "slot": hex(slot), "vt_match": vt_ok})
        index_map = {"ok": any(h["vt_match"] for h in hits), "hits": hits}

    a_progress = prog["nonempty_heap_arrays"] > 0 and (
        prog["member_classified_elems"] > 0
        or prog["handle_classified_elems"] > 0
        or len(prog["army_overlap"]) > 0
        or any(
            (m.get("arrays") or {}).get("0x50", {}).get("size", 0) > 0
            and not (m.get("arrays") or {}).get("0x50", {}).get("in_image_sentinel")
            for m in maps
            if m.get("resolve_ok")
        )
    )
    # even documenting consistent array layout at known offs with elem classes counts
    if not a_progress:
        # weaker but real: ≥3 OGs with plausible +0x50 size documented + elem classes attempted
        a_progress = (
            sum(
                1
                for m in maps
                if m.get("resolve_ok")
                and (m.get("arrays") or {}).get("0x50", {}).get("plausible")
                and (m.get("arrays") or {}).get("0x50", {}).get("size", 0) >= 0
            )
            >= 3
            and prog["nonempty_heap_arrays"] > 0
        )

    b_progress = pool["len"] > 0 and index_map.get("ok")

    nf_ran = False
    nf = {"skipped": True, "reason": "A or B produced progress"}
    if not a_progress and not b_progress:
        print("[2fu] A+B thin → NF/RF 75s…", flush=True)
        nf = stage_watch(b, base, 75.0)
        sight = nf
        nf_ran = True
        live_ois = sorted(set(live_ois) | {a["order_index"] for a in nf["assigns"]})
        for a in nf["assigns"]:
            army_by_oi.setdefault(a["order_index"], [])
            for ix in a.get("army_indices") or []:
                if ix not in army_by_oi[a["order_index"]]:
                    army_by_oi[a["order_index"]].append(ix)
        # remap any new ois
        for oi in live_ois:
            if oi not in {m["order_index"] for m in maps}:
                maps.append(map_og(b, base, oi))
        prog = summarize_progress(maps, army_by_oi)
        a_progress = prog["nonempty_heap_arrays"] > 0
        print(f"[2fu] after NF prog={prog}", flush=True)

    live1 = live_meta(b, base)

    if a_progress:
        result = "orders_group_internals_mapped"
    elif b_progress:
        result = "order_instance_pool_oi_mapped"
    elif nf_ran:
        result = "nf_midflight_bounded"
    else:
        result = "og_internals_inconclusive"

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"stage sight {sight.get('sight_counts')} live_ois={live_ois}",
        f"OG maps resolve_ok={sum(1 for m in maps if m.get('resolve_ok'))}/{len(maps)}",
        f"nonempty_heap_arrays={prog['nonempty_heap_arrays']} member_elems={prog['member_classified_elems']} "
        f"handle_elems={prog['handle_classified_elems']} army_overlap={prog['army_overlap'][:8]}",
        f"heap Instance={heap['counts'].get('COrderInstance')} Member={heap['counts'].get('COrdersGroupMember')} "
        f"pool_len={pool['len']}",
        "CPdxArray layout used: data@0 cap@8 size@0xC alloc@0x10",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "path-vector nonempty",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "NewFallback subject type-id table",
        "live midflight NewFallback hex" if not (nf_ran and nf.get("fallbacks")) else "NF captured",
        "order_index→COrderInstance pool-slot proven",
        "stable G_GAMESTATE→pool root pointer path",
        "full G_GAMESTATE→type-0x35-reg owner path",
        "named COrdersGroup field beyond observed array offs/elem classes",
    ]
    next_blocker = (
        "NON-Post: follow classified OG array elems (Member/units/path) into Post-ready subject pack "
        "OR bounded NF/RF midflight OR COrderInstance when live; still NO ALLOW_POST"
    )

    report = {
        "phase": "2fu",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "34af121",
        "live_at_start": live0,
        "live": live1,
        "cpdxarray_layout": "data@0 capacity@8 size@0xC alloc@0x10",
        "sight": sight,
        "army_by_oi": army_by_oi,
        "maps": maps,
        "progress": prog,
        "heap": {k: v for k, v in heap.items() if k != "sample_addrs"},
        "pool": pool,
        "index_map": index_map,
        "nf_midflight_ran": nf_ran,
        "nf_midflight": nf,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "phase2fu_og_internals.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fu",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "ui_date_start": live0["ui_date"],
        "scenario": live1["scenario"],
        "speed_policy": live1["speed_policy"],
        "live_ois": live_ois,
        "nonempty_heap_arrays": prog["nonempty_heap_arrays"],
        "member_elems": prog["member_classified_elems"],
        "handle_elems": prog["handle_classified_elems"],
        "army_overlap_n": len(prog["army_overlap"]),
        "instance_pool_len": pool["len"],
        "nf_midflight_ran": nf_ran,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "34af121",
    }
    (ROOT / "reports" / "phase2fu_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
