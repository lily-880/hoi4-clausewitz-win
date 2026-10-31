#!/usr/bin/env python3
"""Phase 2ft: tie battle-plan order_index to type-0x35 / COrdersGroup graph (RO).
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
EXEC_VT = cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]
DEL_VT = cmd_layout.ORDERS["COrderDeleteCommand"]["vt"]
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = int(cmd_layout.ISVALID_PATHS["COrderReplaceFallbackCommands"]["vt"])

RTTI_VT = {
    "COrdersGroup": 0x29CED90,
    "COrdersGroupMember": 0x29CED48,
    "COrderInstance": 0x2A02558,
}
TYPE_OG = 0x35
STRIDE = 0x3D0
# historically seen order_index values (also probe live)
HIST_OI = [1, 6, 9, 12, 25]


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
        "scenario": "ITA@1x order_index→type-0x35/OG tie (no Post)",
        "gs": hex(gs),
    }


def rtti_name(b, base, obj):
    try:
        vt = u64(b, obj)
        rva = vt - base
        for name, vr in RTTI_VT.items():
            if rva == vr:
                return name, hex(rva)
        return None, hex(rva)
    except Exception:
        return None, None


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


def heap_scan_vt(b, base, needles, max_samples=48, chunk=4 << 20, time_budget_s=35.0):
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
        EXEC_VT: "COrderExecuteCommand",
        DEL_VT: "COrderDeleteCommand",
        NF_VT: "COrderNewFallbackCommand",
        RF_VT: "COrderReplaceFallbackCommands",
    }
    t0 = time.time()
    counts = {}
    assigns, executes, deletes, nfs, rfs = [], [], [], [], []
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
                # also u32@+0x40 noted in 2fp as 0x35 sometimes
                u40 = u32(b, ptr + 0x40)
                assigns.append(
                    {
                        "addr": hex(ptr),
                        "t": t,
                        "order_index": oi,
                        "units_size": size,
                        "army_indices": armies,
                        "u32_plus40": u40,
                        "u32_plus40_hex": hex(u40),
                    }
                )
            elif name == "COrderExecuteCommand" and len(executes) < 8:
                executes.append({"addr": hex(ptr), "t": t, "order_index": u32(b, ptr + 0x30)})
            elif name == "COrderDeleteCommand" and len(deletes) < 8:
                deletes.append({"addr": hex(ptr), "t": t, "order_index": u32(b, ptr + 0x30)})
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
        "executes": executes,
        "deletes": deletes,
        "fallbacks": nfs,
        "replace_fallbacks": rfs,
    }


def peek_og(b, base, header, og):
    """Document observed fields around OG; scan for small u32 candidates — no invent names."""
    blob = try_read(b, og, 0x80)
    if not blob:
        return {"og": hex(og), "readable": False}
    t8, i8 = struct.unpack_from("<II", blob, 0x8)
    # CPdxArray-shaped qwords: look for plausible (data ptr, size, cap) triples in +0x18..+0x70
    arrays = []
    for off in range(0x18, 0x70, 8):
        if off + 0x18 > len(blob):
            break
        data = struct.unpack_from("<Q", blob, off)[0]
        # size/cap often int32 at +8/+12 relative to array start — try both packing styles
        # style A: {ptr, size:i32, cap:i32} = 0x10
        if off + 16 <= len(blob):
            sz = struct.unpack_from("<i", blob, off + 8)[0]
            cap = struct.unpack_from("<i", blob, off + 12)[0]
            if data > 0x10000 and 0 <= sz <= 512 and sz <= cap <= 4096:
                arrays.append({"off": hex(off), "data": hex(data), "size": sz, "cap": cap, "style": "ptr_i32_i32"})
    # member-like pointers: any qword in image heap that starts with Member VT
    member_ptrs = []
    vt_mem = base + RTTI_VT["COrdersGroupMember"]
    for off in range(0x18, min(0x80, len(blob)), 8):
        q = struct.unpack_from("<Q", blob, off)[0]
        if q < 0x10000:
            continue
        raw = try_read(b, q, 8)
        if raw and struct.unpack("<Q", raw)[0] == vt_mem:
            member_ptrs.append({"off": hex(off), "ptr": hex(q)})
    return {
        "og": hex(og),
        "header": hex(header),
        "plus8_type": t8,
        "plus0c_index": i8,
        "arrays_like": arrays[:6],
        "member_vt_ptrs": member_ptrs[:6],
        "u32_window_0x00_0x40": [hex(struct.unpack_from("<I", blob, i)[0]) for i in range(0, min(0x40, len(blob)), 4)],
    }


def resolve_oi_as_type35(b, base, oi):
    """Test: is battle-plan order_index a type-0x35 handle index?"""
    out = {
        "order_index": oi,
        "resolve_ok": False,
        "header": None,
        "og": None,
        "og_rtti": None,
        "echo_matches": None,
        "plus0c_equals_oi": None,
    }
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception as e:
        out["error"] = str(e)
        return out
    if not hdr:
        out["resolve_null"] = True
        return out
    out["resolve_ok"] = True
    out["header"] = hex(hdr)
    og = hdr + 0x10
    out["og"] = hex(og)
    nm, rva = rtti_name(b, base, og)
    out["og_rtti"] = nm
    out["og_vt_rva"] = rva
    try:
        echo = list(struct.unpack("<II", b.read(hdr + 0x18, 8)))
        out["echo"] = echo
        out["echo_matches"] = echo == [TYPE_OG, oi]
    except Exception:
        pass
    try:
        t8, i8 = struct.unpack("<II", b.read(og + 0x8, 8))
        out["og_plus8_type"] = t8
        out["og_plus0c_index"] = i8
        out["plus0c_equals_oi"] = i8 == oi
    except Exception:
        pass
    out["peek"] = peek_og(b, base, hdr, og)
    return out


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


def main():
    pid = find_pid()
    b = Backend(pid)
    base = b.image_base
    live0 = live_meta(b, base)
    print(f"[2ft] live {live0['ui_date']} pid {pid}", flush=True)
    assert allow_post() is False

    reg = u64(b, base + HANDLE_TYPE_TABLE + TYPE_OG * 8)
    print(f"[2ft] HANDLE_TYPE_TABLE[0x35]={hex(reg)}", flush=True)

    # A1: short stage for live ois (25s), then resolve each as type-0x35
    print("[2ft] stage Assign/Exec/Del/NF 25s…", flush=True)
    sight = stage_watch(b, base, 25.0)
    live_ois = sorted(
        {
            *(a["order_index"] for a in sight["assigns"]),
            *(e["order_index"] for e in sight["executes"]),
            *(d["order_index"] for d in sight["deletes"]),
        }
    )
    print(f"[2ft] sight {sight['sight_counts']} live_ois={live_ois}", flush=True)

    probe_ois = sorted(set(live_ois) | set(HIST_OI))
    print(f"[2ft] resolve(0x35, oi) for {probe_ois}…", flush=True)
    ties = [resolve_oi_as_type35(b, base, oi) for oi in probe_ois]
    tie_ok = [t for t in ties if t.get("resolve_ok") and t.get("og_rtti") == "COrdersGroup" and t.get("plus0c_equals_oi")]
    print(
        f"[2ft] ties resolve_ok={sum(1 for t in ties if t.get('resolve_ok'))} "
        f"og_rtti_OG={sum(1 for t in ties if t.get('og_rtti')=='COrdersGroup')} "
        f"plus0c_eq_oi={len(tie_ok)}",
        flush=True,
    )

    # B: short Instance+OG heap
    print("[2ft] heap Instance+OG+Member ≤35s…", flush=True)
    heap = heap_scan_vt(
        b,
        base,
        {
            "COrderInstance": RTTI_VT["COrderInstance"],
            "COrdersGroup": RTTI_VT["COrdersGroup"],
            "COrdersGroupMember": RTTI_VT["COrdersGroupMember"],
        },
        time_budget_s=35.0,
    )
    print(f"[2ft] heap {heap['counts']}", flush=True)
    pool = expand_pool(b, base, heap["sample_addrs"].get("COrderInstance", []))
    print(f"[2ft] Instance pool len={pool['len']}", flush=True)

    index_map = {"ok": False, "reason": "empty pool"}
    if pool["len"] > 0 and live_ois:
        pbase = int(pool["base"], 16)
        hits = []
        for oi in live_ois:
            slot = pbase + oi * STRIDE
            blob = try_read(b, slot, 8)
            vt_ok = bool(blob) and struct.unpack("<Q", blob)[0] == base + RTTI_VT["COrderInstance"]
            hits.append({"oi": oi, "slot": hex(slot), "vt_match": vt_ok})
        index_map = {
            "ok": any(h["vt_match"] for h in hits),
            "hits": hits,
            "oi_fits": max(live_ois) < pool["len"] if live_ois else None,
        }

    # Cross: live heap OG indices vs probe ois (expect high-index fronts ≠ low oi slots)
    og_heap_idxs = []
    for addr in heap["sample_addrs"].get("COrdersGroup", [])[:16]:
        blob = try_read(b, addr, 0x10)
        if blob:
            t8, i8 = struct.unpack_from("<II", blob, 0x8)
            og_heap_idxs.append({"og": hex(addr), "type": t8, "index": i8})

    a_progress = len(tie_ok) >= 1 and (
        bool(live_ois) or any(t["order_index"] in HIST_OI and t.get("resolve_ok") for t in ties)
    )
    # stronger: at least one LIVE assign oi ties
    live_tie_ok = [t for t in tie_ok if t["order_index"] in live_ois] if live_ois else []
    hist_tie_ok = [t for t in tie_ok if t["order_index"] in HIST_OI]
    b_progress = pool["len"] > 0 and index_map.get("ok")

    nf_ran = False
    nf = {"skipped": True, "reason": "A or B produced progress"}
    if not a_progress and not b_progress:
        print("[2ft] A+B thin → NF/RF 75s…", flush=True)
        nf = stage_watch(b, base, 75.0)
        sight = nf  # replace with longer
        nf_ran = True
        # re-try ties on any new ois
        more = sorted(
            {
                *(a["order_index"] for a in nf["assigns"]),
                *(e["order_index"] for e in nf["executes"]),
                *(d["order_index"] for d in nf["deletes"]),
            }
        )
        for oi in more:
            if oi not in probe_ois:
                ties.append(resolve_oi_as_type35(b, base, oi))
        tie_ok = [t for t in ties if t.get("resolve_ok") and t.get("og_rtti") == "COrdersGroup" and t.get("plus0c_equals_oi")]
        live_ois = sorted(set(live_ois) | set(more))
        live_tie_ok = [t for t in tie_ok if t["order_index"] in live_ois]
        a_progress = len(tie_ok) >= 1
        print(f"[2ft] after NF ties plus0c_eq={len(tie_ok)} live_ois={live_ois}", flush=True)

    live1 = live_meta(b, base)

    if a_progress and (live_tie_ok or hist_tie_ok):
        result = "order_index_is_type35_index"
    elif b_progress:
        result = "order_instance_pool_oi_mapped"
    elif nf_ran:
        result = "nf_midflight_bounded"
    else:
        result = "oi_type35_tie_inconclusive"

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"stage sight {sight.get('sight_counts')} live_ois={live_ois}",
        f"resolve(0x35,oi) probe_ois={probe_ois} resolve_ok={sum(1 for t in ties if t.get('resolve_ok'))} "
        f"OG_rtti={sum(1 for t in ties if t.get('og_rtti')=='COrdersGroup')} plus0c_eq_oi={len(tie_ok)}",
        f"live_oi ties={ [t['order_index'] for t in live_tie_ok] } hist_oi ties={ [t['order_index'] for t in hist_tie_ok] }",
        f"heap Instance={heap['counts'].get('COrderInstance')} OG={heap['counts'].get('COrdersGroup')} "
        f"Member={heap['counts'].get('COrdersGroupMember')} pool_len={pool['len']}",
        f"Assign u32@+0x40 samples={[a.get('u32_plus40_hex') for a in sight.get('assigns',[])[:6]]}",
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
        "live midflight NewFallback hex" if not (nf_ran and nf.get("fallbacks")) else "NF captured this window",
        "order_index→COrderInstance pool-slot proven",
        "stable G_GAMESTATE→pool root pointer path",
        "full G_GAMESTATE→type-0x35-reg owner path",
        "COrdersGroup internal order-slot field names (arrays observed only)",
    ]

    if result == "order_index_is_type35_index":
        next_blocker = (
            "NON-Post: map COrdersGroup internals (members/arrays) for path/units OR "
            "re-probe COrderInstance when live OR bounded NF/RF subject; still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: continue oi↔type-0x35/OG relation OR COrderInstance pool when live "
            "OR bounded NF/RF midflight; still NO ALLOW_POST"
        )

    report = {
        "phase": "2ft",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "967a7ed",
        "live_at_start": live0,
        "live": live1,
        "handle_type_0x35_registry": hex(reg),
        "sight": sight,
        "probe_ois": probe_ois,
        "ties": ties,
        "tie_ok_ois": [t["order_index"] for t in tie_ok],
        "live_tie_ok_ois": [t["order_index"] for t in live_tie_ok],
        "og_heap_indices": og_heap_idxs,
        "heap": {k: v for k, v in heap.items() if k != "sample_addrs"},
        "pool": pool,
        "index_map": index_map,
        "nf_midflight_ran": nf_ran,
        "nf_midflight": nf,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "interpretation": (
            "If resolve(0x35, order_index)→COrdersGroup with +0xc==order_index, then battle-plan "
            "order_index shares the type-0x35 handle index space (same catalog as 2fs). "
            "High-index heap OGs (~300+) may be other groups; no invent beyond handle equality."
        ),
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "phase2ft_oi_to_type35.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2ft",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "ui_date_start": live0["ui_date"],
        "scenario": live1["scenario"],
        "speed_policy": live1["speed_policy"],
        "live_ois": live_ois,
        "tie_ok_ois": [t["order_index"] for t in tie_ok],
        "live_tie_ok_ois": [t["order_index"] for t in live_tie_ok],
        "instance_pool_len": pool["len"],
        "nf_midflight_ran": nf_ran,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "967a7ed",
    }
    (ROOT / "reports" / "phase2ft_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
