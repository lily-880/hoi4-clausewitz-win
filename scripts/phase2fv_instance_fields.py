#!/usr/bin/env python3
"""Phase 2fv: map COrderInstance fields from OG+0x98 targets (RO).
Also light type-pass on OG+0x50 opaque elems. No Post. Never 5x. allow_post False.
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
}
RTTI_BY_RVA = {v: k for k, v in RTTI_VT.items()}
TYPE_OG = 0x35
STRIDE = 0x3D0
# Instance dump window (object is large; map first 0x200 + selected array offs)
INST_MAP = 0x200
# Candidate CPdxArray offs inside Instance (scan 8-aligned 0x08..0x1F0)
ARRAY_SCAN_OFFS = list(range(0x08, 0x1F0, 8))
FOCUS_LIVE = [17, 20, 52]
HIST = [1, 6, 9, 10, 12, 25, 33]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


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
        "scenario": "ITA@1x COrderInstance field map via OG+0x98 (no Post)",
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
        "in_image_sentinel": bool(in_image),
        "plausible": bool(plausible),
    }


def classify_elem(b, base, q):
    typ = q & 0xFFFFFFFF
    idx = (q >> 32) & 0xFFFFFFFF
    if typ < 0x64 and idx < 0x100000:
        resolved = None
        try:
            resolved = resolve_handle(b, typ, idx, base)
        except Exception:
            pass
        if resolved:
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
    if q > 0x10000:
        nm, rva = rtti_at(b, base, q)
        if nm:
            return {"kind": "rtti_ptr", "ptr": hex(q), "rtti": nm, "vt_rva": rva}
        nm2, rva2 = rtti_at(b, base, q + 0x10)
        if nm2:
            return {
                "kind": "rtti_ptr_plus10",
                "ptr": hex(q),
                "rtti": nm2,
                "vt_rva": rva2,
            }
        return {"kind": "opaque_ptr", "ptr": hex(q)}
    return {"kind": "small", "raw": hex(q)}


def dump_array_elems(b, base, arr, max_n=12, stride=8):
    if not arr or not arr["plausible"] or arr["size"] <= 0 or arr.get("in_image_sentinel"):
        return []
    n = min(arr["size"], max_n)
    blob = try_read(b, arr["data_int"], n * stride)
    if not blob:
        return []
    out = []
    for i in range(n):
        if stride == 8:
            q = struct.unpack_from("<Q", blob, i * 8)[0]
            t, ix = struct.unpack_from("<II", blob, i * 8)
            out.append({"i": i, "qword": hex(q), "as_u32_pair": [t, ix], "class": classify_elem(b, base, q)})
        else:
            v = struct.unpack_from("<I", blob, i * 4)[0]
            out.append({"i": i, "u32": v, "u32_hex": hex(v)})
    return out


def stage_watch(b, base, seconds: float = 12.0):
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
                size = struct.unpack("<i", b.read(ptr + 0x34, 4))[0]
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


def type_opaque50(b, base, ptr):
    """Deepen one OG+0x50 opaque elem: VT at 0/+8/+0x10, Member scan, handle peeks, small arrays."""
    out = {"ptr": hex(ptr)}
    if ptr < 0x10000:
        out["kind"] = "small"
        return out
    raw = try_read(b, ptr, 0x80)
    if not raw:
        out["kind"] = "unreadable"
        return out
    # VT candidates
    for off in (0, 8, 0x10, 0x18):
        if off + 8 > len(raw):
            break
        q = struct.unpack_from("<Q", raw, off)[0]
        if base <= q < base + b.image_size:
            rva = q - base
            nm = RTTI_BY_RVA.get(rva)
            out[f"vt_at_plus{hex(off)}"] = {"rva": hex(rva), "rtti": nm}
            if nm:
                out["kind"] = f"rtti_at_plus{hex(off)}"
                out["rtti"] = nm
    # Member VT absolute anywhere in first 0x80
    vt_mem = base + RTTI_VT["COrdersGroupMember"]
    mem_hits = []
    for off in range(0, len(raw) - 7, 8):
        if struct.unpack_from("<Q", raw, off)[0] == vt_mem:
            mem_hits.append(hex(off))
    if mem_hits:
        out["member_vt_offs"] = mem_hits
        out["kind"] = out.get("kind") or "embedded_Member_vt"
    # Handle-shaped qwords
    handles = []
    for off in range(0, min(0x60, len(raw) - 7), 8):
        q = struct.unpack_from("<Q", raw, off)[0]
        typ = q & 0xFFFFFFFF
        idx = (q >> 32) & 0xFFFFFFFF
        if typ in (HANDLE_TYPE_ARMY, TYPE_OG, 0x33, 0x34, 0x35) and idx < 0x100000:
            handles.append({"off": hex(off), "type": typ, "index": idx})
    if handles:
        out["handle_shaped"] = handles
    # CPdxArray candidates at +0x08..+0x50
    arrays = {}
    for off in (0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50):
        arr = read_cpdx(b, base, ptr + off)
        if arr and arr["plausible"] and arr["size"] > 0 and not arr["in_image_sentinel"]:
            entry = {k: v for k, v in arr.items() if k != "data_int"}
            entry["elems8"] = dump_array_elems(b, base, arr, max_n=6)
            entry["elems4_head"] = dump_array_elems(b, base, arr, max_n=8, stride=4)
            arrays[hex(off)] = entry
    if arrays:
        out["arrays"] = arrays
    # u32 head
    out["u32_0x00_0x40"] = [hex(struct.unpack_from("<I", raw, i)[0]) for i in range(0, 0x40, 4)]
    if "kind" not in out:
        out["kind"] = "opaque_still"
    return out


def map_instance(b, base, oi, inst):
    nm, rva = rtti_at(b, base, inst)
    blob = try_read(b, inst, INST_MAP)
    rec = {
        "order_index": oi,
        "inst": hex(inst),
        "rtti": nm,
        "vt_rva": rva,
        "vt_ok": nm == "COrderInstance",
    }
    if not blob:
        rec["read_ok"] = False
        return rec
    rec["read_ok"] = True
    # u32 / qword dumps
    rec["u32_0x00_0x80"] = [hex(struct.unpack_from("<I", blob, i)[0]) for i in range(0, 0x80, 4)]
    # Handle-shaped + RTTI ptrs in first 0x100
    hits = []
    for off in range(0, min(0x100, len(blob) - 7), 8):
        q = struct.unpack_from("<Q", blob, off)[0]
        cls = classify_elem(b, base, q)
        if cls["kind"] in ("handle", "handle_unresolved", "rtti_ptr", "rtti_ptr_plus10"):
            hits.append({"off": hex(off), **cls})
        elif cls["kind"] == "opaque_ptr":
            # only keep if looks interesting: points near OG/inst
            hits.append({"off": hex(off), **cls})
    # Keep only non-opaque OR first few opaque for size control
    interesting = [h for h in hits if h["kind"] != "opaque_ptr"]
    opaque = [h for h in hits if h["kind"] == "opaque_ptr"][:8]
    rec["field_hits"] = interesting + opaque
    # order_index echo search: u32 == oi
    oi_offs = []
    for off in range(0, len(blob) - 3, 4):
        if struct.unpack_from("<I", blob, off)[0] == oi:
            oi_offs.append(hex(off))
    rec["u32_eq_order_index_offs"] = oi_offs[:16]
    # type 0x35 echo
    t35_offs = []
    for off in range(0, len(blob) - 3, 4):
        if struct.unpack_from("<I", blob, off)[0] == TYPE_OG:
            t35_offs.append(hex(off))
    rec["u32_eq_0x35_offs"] = t35_offs[:16]
    # CPdxArray scan
    arrays = {}
    for off in ARRAY_SCAN_OFFS:
        if off + 0x18 > INST_MAP:
            continue
        arr = read_cpdx(b, base, inst + off)
        if not arr or not arr["plausible"]:
            continue
        entry = {k: v for k, v in arr.items() if k != "data_int"}
        if arr["size"] > 0 and not arr["in_image_sentinel"]:
            entry["elems8"] = dump_array_elems(b, base, arr, max_n=10)
            entry["elems4_head"] = dump_array_elems(b, base, arr, max_n=12, stride=4)
            arrays[hex(off)] = entry
        elif arr["in_image_sentinel"] and arr["size"] == 0:
            # record sentinel empties sparsely
            if off in (0x18, 0x30, 0x48, 0x50, 0x68, 0x80, 0x98, 0xA0, 0xB0, 0xC0):
                arrays[hex(off)] = {**entry, "note": "empty_sentinel"}
    rec["arrays"] = arrays
    # Back-pointer to OG? search for qword == og (filled by caller)
    return rec


def resolve_inst_via_og(b, base, oi):
    hdr = resolve_handle(b, TYPE_OG, oi, base)
    if not hdr:
        return None
    og = hdr + 0x10
    arr = read_cpdx(b, base, og + 0x98)
    if not arr or not arr["plausible"] or arr["size"] < 1:
        return {"order_index": oi, "og": hex(og), "inst": None, "note": "no +0x98"}
    ptr = u64(b, arr["data_int"])
    return {
        "order_index": oi,
        "header": hex(hdr),
        "og": hex(og),
        "arr98": {k: v for k, v in arr.items() if k != "data_int"},
        "inst_ptr": ptr,
        "inst": hex(ptr),
    }


def map_og50(b, base, oi):
    hdr = resolve_handle(b, TYPE_OG, oi, base)
    if not hdr:
        return {"order_index": oi, "resolve_ok": False}
    og = hdr + 0x10
    arr = read_cpdx(b, base, og + 0x50)
    if not arr or not arr["plausible"]:
        return {"order_index": oi, "og": hex(og), "arr50": None}
    elems = []
    if arr["size"] > 0 and not arr["in_image_sentinel"]:
        n = min(arr["size"], 8)
        blob = try_read(b, arr["data_int"], n * 8)
        if blob:
            for i in range(n):
                q = struct.unpack_from("<Q", blob, i * 8)[0]
                elems.append(type_opaque50(b, base, q))
    return {
        "order_index": oi,
        "og": hex(og),
        "arr50": {k: v for k, v in arr.items() if k != "data_int"},
        "elems_typed": elems,
    }


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        raise SystemExit("hoi4.exe not found")
    b = Backend(pid)
    base = b.image_base
    live = live_meta(b, base)
    print("LIVE", json.dumps(live))

    sight = stage_watch(b, base, seconds=12.0)
    live_ois = sorted({a["order_index"] for a in sight.get("assigns", []) if "order_index" in a})
    print("SIGHT ois", live_ois, "n_assign", len(sight.get("assigns", [])))

    targets = sorted(set(FOCUS_LIVE) | set(live_ois) | set(HIST[:5]))
    # Prefer live first
    order = [x for x in (live_ois + FOCUS_LIVE + HIST) if x in targets]
    seen = []
    for x in order:
        if x not in seen:
            seen.append(x)
    targets = seen[:12]

    instances = []
    for oi in targets:
        link = resolve_inst_via_og(b, base, oi)
        if not link or not link.get("inst_ptr"):
            instances.append({"order_index": oi, "resolve_ok": False, "link": link})
            continue
        m = map_instance(b, base, oi, link["inst_ptr"])
        m["link"] = {k: v for k, v in link.items() if k != "inst_ptr"}
        # OG backref: does Instance contain og ptr?
        og_int = int(link["og"], 16)
        blob = try_read(b, link["inst_ptr"], INST_MAP) or b""
        og_offs = []
        for off in range(0, len(blob) - 7, 8):
            if struct.unpack_from("<Q", blob, off)[0] == og_int:
                og_offs.append(hex(off))
        m["qword_eq_og_offs"] = og_offs[:8]
        instances.append(m)

    # B light: type +0x50 for live/focus
    og50 = []
    for oi in (live_ois or FOCUS_LIVE)[:6]:
        og50.append(map_og50(b, base, oi))

    # Consistency: which Instance array offs nonempty across samples
    nonempty_arr_offs = Counter()
    handle_hits = Counter()
    oi_echo_offs = Counter()
    for m in instances:
        if not m.get("vt_ok"):
            continue
        for off, arr in (m.get("arrays") or {}).items():
            if arr.get("size", 0) > 0 and not arr.get("in_image_sentinel"):
                nonempty_arr_offs[off] += 1
        for h in m.get("field_hits") or []:
            if h.get("kind") == "handle":
                handle_hits[f"t{h.get('type')}@{h.get('off')}"] += 1
        for off in m.get("u32_eq_order_index_offs") or []:
            oi_echo_offs[off] += 1

    # +0x50 kind tally
    kind50 = Counter()
    for g in og50:
        for e in g.get("elems_typed") or []:
            kind50[e.get("kind", "?")] += 1

    vt_ok_n = sum(1 for m in instances if m.get("vt_ok"))
    result = "order_instance_fields_mapped" if vt_ok_n >= 2 else (
        "order_instance_fields_thin" if vt_ok_n >= 1 else "order_instance_fields_empty"
    )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"stage sight assigns={len(sight.get('assigns', []))} live_ois={live_ois}",
        f"Instance via OG+0x98 mapped vt_ok={vt_ok_n}/{len(instances)}",
        f"nonempty Instance array offs (count across maps): {dict(nonempty_arr_offs)}",
        f"order_index u32 echo offs tally: {dict(oi_echo_offs)}",
        f"handle-shaped Instance hits tally: {dict(list(handle_hits.items())[:20])}",
        f"+0x50 elem kinds: {dict(kind50)}",
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
        "live midflight NewFallback hex",
        "order_index→COrderInstance pool-slot arithmetic (object path via OG+0x98 works)",
        "stable G_GAMESTATE→pool root pointer path",
        "full G_GAMESTATE→type-0x35-reg owner path",
    ]
    # leave typed +0x50 / Instance field names in stubbed if still opaque
    if not any(k.startswith("rtti") or k.startswith("embedded") for k in kind50):
        stubbed.append("typed identity of COrdersGroup+0x50 opaque elems (still opaque/partial)")
    next_blocker = (
        "NON-Post: deepen typed Instance arrays/handles for path/units OR finish +0x50 identity "
        "OR bounded NF/RF subject; still NO ALLOW_POST"
    )

    out = {
        "result": result,
        "allow_post": False,
        "live": live,
        "sight": sight,
        "targets": targets,
        "instances": instances,
        "og50": og50,
        "consistency": {
            "nonempty_arr_offs": dict(nonempty_arr_offs),
            "oi_echo_offs": dict(oi_echo_offs),
            "handle_hits": dict(handle_hits),
            "kind50": dict(kind50),
            "vt_ok_n": vt_ok_n,
        },
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "phase2fv_instance_fields.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    summary = {
        "result": result,
        "allow_post": False,
        "live": live,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "consistency": out["consistency"],
        "live_ois": live_ois,
        "vt_ok_n": vt_ok_n,
        "n_mapped": len(instances),
    }
    (reports / "phase2fv_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("RESULT", result, "vt_ok", vt_ok_n, "kind50", dict(kind50))
    print("consistency", json.dumps(out["consistency"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
