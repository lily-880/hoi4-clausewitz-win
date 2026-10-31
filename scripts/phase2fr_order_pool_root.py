#!/usr/bin/env python3
"""Phase 2fr: COrderInstance pool root / index catalog + COrdersGroup +0x8/+0xc handle map (RO).
No Post. Never 5x. allow_post must stay False.
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
STRIDE = 0x3D0
TYPE_OG = 0x35  # observed at COrdersGroup+0x8 in 2fq peeks


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
        "scenario": "ITA@1x order pool root / OG handle map (no Post)",
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


def heap_scan_vt(b, base, needles, max_samples=64, chunk=4 << 20, time_budget_s=50.0):
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


def stage_assigns_and_nf(b, base, seconds: float):
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


def handle_table_slot(b, base, typ):
    """Read HANDLE_TYPE_TABLE[typ] registry pointer (types < 0x64)."""
    if typ >= 0x64:
        return None
    try:
        return u64(b, base + HANDLE_TYPE_TABLE + typ * 8)
    except Exception:
        return None


def map_orders_group_handles(b, base, addrs):
    out = []
    for addr in addrs[:12]:
        blob = try_read(b, addr, 0x40)
        if not blob or len(blob) < 0x18:
            continue
        t8, i8 = struct.unpack_from("<II", blob, 0x8)
        flag10 = struct.unpack_from("<I", blob, 0x10)[0]
        entry = {
            "addr": hex(addr),
            "plus8_type": t8,
            "plus8_type_hex": hex(t8),
            "plus0c_index": i8,
            "plus10_u32": flag10,
            "matches_type_0x35": t8 == TYPE_OG,
        }
        # resolve as handle if type < 0x64
        if t8 < 0x64:
            try:
                ptr = resolve_handle(b, t8, i8, base)
                entry["resolved"] = hex(ptr) if ptr else None
                if ptr:
                    nm, rva = rtti_name(b, base, ptr)
                    entry["resolved_rtti"] = nm
                    entry["resolved_vt_rva"] = rva
                    # echo handle at +0x18 common pattern?
                    try:
                        echo = list(struct.unpack("<II", b.read(ptr + 0x18, 8)))
                        entry["resolved_plus18"] = echo
                        entry["echo_matches"] = echo == [t8, i8]
                    except Exception:
                        pass
            except Exception as e:
                entry["resolve_error"] = str(e)
        # also try resolving self as if group embeds its own handle elsewhere
        out.append(entry)
    return out


def expand_pool(b, base, seeds):
    """Walk ±stride from seeds while VT matches COrderInstance; return sorted unique addrs."""
    vt_abs = base + RTTI_VT["COrderInstance"]
    found = set(seeds)
    # grow outward
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
    return sorted(found)


def test_oi_index_map(b, base, pool, live_ois):
    """Test whether pool_base + oi*STRIDE is a live COrderInstance."""
    if not pool:
        return {"ok": False, "reason": "empty pool"}
    pool_base = pool[0]
    vt_abs = base + RTTI_VT["COrderInstance"]
    results = []
    for oi in live_ois:
        cand = pool_base + oi * STRIDE
        blob = try_read(b, cand, 8)
        hit = bool(blob) and struct.unpack("<Q", blob)[0] == vt_abs
        in_pool = cand in pool
        results.append(
            {
                "order_index": oi,
                "candidate": hex(cand),
                "vt_is_COrderInstance": hit,
                "in_expanded_pool": in_pool,
            }
        )
    return {
        "pool_base": hex(pool_base),
        "pool_len": len(pool),
        "stride": hex(STRIDE),
        "max_oi": max(live_ois) if live_ois else None,
        "oi_fits_pool_len": (max(live_ois) < len(pool)) if live_ois else None,
        "tests": results,
        "any_hit": any(r["vt_is_COrderInstance"] for r in results),
    }


def find_owners_of(b, base, targets, max_per=8, time_budget_s=40.0, chunk=4 << 20):
    needles = {t: struct.pack("<Q", t) for t in targets}
    owners = {t: [] for t in targets}
    scanned = 0
    t0 = time.time()
    for start, end in writable_regions(b, base):
        if time.time() - t0 > time_budget_s:
            break
        if all(len(owners[t]) >= max_per for t in targets):
            break
        pos = start
        while pos < end:
            if time.time() - t0 > time_budget_s:
                break
            if all(len(owners[t]) >= max_per for t in targets):
                break
            nread = min(chunk, end - pos)
            data = try_read(b, pos, nread)
            scanned += nread
            if data:
                for t, needle in needles.items():
                    if len(owners[t]) >= max_per:
                        continue
                    off = 0
                    while len(owners[t]) < max_per:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            slot = pos + i
                            if slot != t:
                                owners[t].append(slot)
                        off = i + 8
            pos += nread
    # classify: CPdxArray header near slot?
    classified = []
    for t, slots in owners.items():
        for slot in slots:
            # peek -0x0..-0x20 for array hdr pointing at t as data[0] or containing t
            info = {"obj": hex(t), "slot": hex(slot)}
            for back in (0, 8, 16, 24, 32, 40, 48):
                hdr = slot - back
                blob = try_read(b, hdr, 0x18)
                if not blob:
                    continue
                data, cap, size, alloc = struct.unpack_from("<QiiQ", blob, 0)
                if 0 < size <= 4096 and size <= cap <= 8192 and data:
                    if data == t or (data <= slot < data + size * 8 and (slot - data) % 8 == 0):
                        idx = 0 if data == t else (slot - data) // 8
                        info["array"] = {
                            "header": hex(hdr),
                            "data": hex(data),
                            "capacity": cap,
                            "size": size,
                            "index": idx,
                        }
                        # owner object RTTI: try hdr-8 as object start (vtable before array field)
                        for obj_back in (0, 8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x40, 0x48, 0x50):
                            oaddr = hdr - obj_back
                            nm, rva = rtti_name(b, base, oaddr)
                            if nm:
                                info["owner_rtti"] = nm
                                info["owner_addr"] = hex(oaddr)
                                info["owner_vt_rva"] = rva
                                info["array_field_off"] = hex(obj_back)
                                break
                        break
            classified.append(info)
    return {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 1),
        "owners": {hex(t): [hex(s) for s in v] for t, v in owners.items()},
        "classified": classified[:40],
    }


def main():
    assert allow_post() is False
    b = Backend()
    base = int(b.image_base)
    live0 = live_meta(b, base)
    print("[2fr] live", live0["ui_date"], "pid", live0["pid"], flush=True)

    # type-0x35 registry slot
    reg35 = handle_table_slot(b, base, TYPE_OG)
    print("[2fr] HANDLE_TYPE_TABLE[0x35]=", hex(reg35) if reg35 else None, flush=True)

    print("[2fr] heap scan order RTTI ≤50s…", flush=True)
    heap = heap_scan_vt(
        b,
        base,
        {"COrderInstance": RTTI_VT["COrderInstance"], "COrdersGroup": RTTI_VT["COrdersGroup"]},
        max_samples=64,
        time_budget_s=50.0,
    )
    print("[2fr] heap", heap["counts"], flush=True)

    seeds = heap["sample_addrs"].get("COrderInstance", [])
    pool = expand_pool(b, base, seeds)
    print("[2fr] expanded pool len", len(pool), "base", hex(pool[0]) if pool else None, flush=True)

    # short assign sight for live ois (25s) — enough for AI traffic
    print("[2fr] Assign/NF sight 25s…", flush=True)
    sight = stage_assigns_and_nf(b, base, seconds=25.0)
    live_ois = sorted({a["order_index"] for a in sight["assigns"]})
    print("[2fr] assigns", len(sight["assigns"]), "ois", live_ois, "counts", sight["sight_counts"], flush=True)

    # if no assigns, reuse prior ois from 2fq for index tests
    test_ois = live_ois or [6, 9, 12]
    index_map = test_oi_index_map(b, base, pool, test_ois)
    print("[2fr] oi→pool any_hit", index_map.get("any_hit"), "fits", index_map.get("oi_fits_pool_len"), flush=True)

    # owner of pool base (+ first few slots)
    owner_targets = []
    if pool:
        owner_targets.append(pool[0])
        if len(pool) > 1:
            owner_targets.append(pool[1])
    print("[2fr] owner scan ≤40s for", [hex(x) for x in owner_targets], flush=True)
    owners = find_owners_of(b, base, owner_targets, max_per=8, time_budget_s=40.0) if owner_targets else {"classified": [], "owners": {}}
    print(
        "[2fr] owner slots",
        {k: len(v) for k, v in (owners.get("owners") or {}).items()},
        "classified",
        len(owners.get("classified") or []),
        flush=True,
    )

    # B: COrdersGroup +0x8/+0xc
    groups = heap["sample_addrs"].get("COrdersGroup", [])[:12]
    # if heap thin on groups, use expand? just samples
    print("[2fr] map COrdersGroup +0x8/+0xc…", flush=True)
    og_map = map_orders_group_handles(b, base, groups)

    # C: NF only if A and B both thin
    a_progress = bool(owners.get("classified")) or index_map.get("any_hit")
    b_progress = any(g.get("resolved") for g in og_map) or any(g.get("matches_type_0x35") for g in og_map)
    nf_extra = None
    nf_ran = False
    if not a_progress and not b_progress:
        print("[2fr] A/B thin — NF/RF ≤70s…", flush=True)
        nf_ran = True
        nf_extra = stage_assigns_and_nf(b, base, seconds=70.0)
    elif not sight["fallbacks"] and not sight["replace_fallbacks"] and (not a_progress or not b_progress):
        # still cheap: skip long NF if we have some progress
        nf_extra = {"skipped": True, "reason": "A or B produced progress; short sight already ran"}

    live1 = live_meta(b, base)

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"heap COrderInstance={heap['counts'].get('COrderInstance', 0)} COrdersGroup={heap['counts'].get('COrdersGroup', 0)}",
        f"expanded COrderInstance pool len={len(pool)} stride=0x3D0 base={hex(pool[0]) if pool else None}",
        f"oi→pool_base+oi*stride any_hit={index_map.get('any_hit')} oi_fits_pool_len={index_map.get('oi_fits_pool_len')} test_ois={test_ois}",
        f"HANDLE_TYPE_TABLE[0x35]={hex(reg35) if reg35 else None}",
        f"COrdersGroup +0x8/+0xc mapped n={len(og_map)} resolved={sum(1 for g in og_map if g.get('resolved'))} type0x35={sum(1 for g in og_map if g.get('matches_type_0x35'))}",
        f"pool-base owners classified={len(owners.get('classified') or [])}",
        f"Assign sight ois={live_ois} counts={sight['sight_counts']}",
    ]

    # result classification
    if index_map.get("any_hit"):
        result = "order_index_pool_index_proven"
    elif any(g.get("resolved_rtti") for g in og_map):
        result = "orders_group_handle_mapped"
    elif any(g.get("matches_type_0x35") for g in og_map) and reg35:
        result = "orders_group_type0x35_documented"
    elif owners.get("classified"):
        result = "pool_owner_partial"
    elif len(pool) > 0 and index_map.get("oi_fits_pool_len") is False:
        result = "pool_index_rejected_size"
    else:
        result = "pool_root_inconclusive"

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
    ]
    if not (sight.get("fallbacks") or (nf_extra or {}).get("fallbacks")):
        stubbed += ["NewFallback subject type-id table", "live midflight NewFallback hex"]
    if not index_map.get("any_hit"):
        stubbed.append("order_index→COrderInstance pool-slot proven")
    if not any(c.get("owner_rtti") for c in (owners.get("classified") or [])):
        stubbed.append("stable G_GAMESTATE→pool root pointer path")

    if index_map.get("any_hit"):
        next_b = "NON-Post: wire Execute order_index@+0x30 through same pool slot; still NO ALLOW_POST"
    elif any(g.get("resolved_rtti") for g in og_map):
        next_b = (
            "NON-Post: walk resolved COrdersGroup handle object for order_index/units cross-link; "
            "still NO ALLOW_POST"
        )
    elif result == "pool_index_rejected_size":
        next_b = (
            "NON-Post: order_index is NOT COrderInstance pool index (len≪ois) — "
            "follow type 0x35 handle registry / COrdersGroup graph; NF/RF midflight; still NO ALLOW_POST"
        )
    else:
        next_b = (
            "NON-Post: deepen type-0x35 handle resolve path or bounded NF/RF subject midflight; "
            "still NO ALLOW_POST"
        )

    report = {
        "phase": "2fr",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "11fe169",
        "live_at_start": live0,
        "live": live1,
        "handle_type_0x35_registry": hex(reg35) if reg35 else None,
        "heap": {
            "scanned_mb": heap["scanned_mb"],
            "elapsed_s": heap["elapsed_s"],
            "counts": heap["counts"],
            "samples": heap["samples"],
        },
        "pool": {
            "stride": hex(STRIDE),
            "addrs": [hex(x) for x in pool],
            "len": len(pool),
            "base": hex(pool[0]) if pool else None,
        },
        "index_map": index_map,
        "owners": owners,
        "orders_group_handle_map": og_map,
        "sight": sight,
        "nf_midflight_ran": nf_ran,
        "nf_midflight": nf_extra,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "push_note": "retry origin push 1–2x; do not burn quota",
    }
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "phase2fr_order_pool_root.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fr",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "ui_date_start": live0["ui_date"],
        "scenario": live1["scenario"],
        "speed_policy": live1["speed_policy"],
        "pool_len": len(pool),
        "pool_base": hex(pool[0]) if pool else None,
        "index_map_any_hit": index_map.get("any_hit"),
        "oi_fits_pool_len": index_map.get("oi_fits_pool_len"),
        "live_order_indices": live_ois,
        "og_mapped_n": len(og_map),
        "og_resolved_n": sum(1 for g in og_map if g.get("resolved")),
        "og_type0x35_n": sum(1 for g in og_map if g.get("matches_type_0x35")),
        "owner_classified_n": len(owners.get("classified") or []),
        "nf_midflight_ran": nf_ran,
        "nf_hits": len((nf_extra or {}).get("fallbacks") or []) if isinstance(nf_extra, dict) else 0,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "parent_sha_base": "11fe169",
    }
    (ROOT / "reports" / "phase2fr_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
