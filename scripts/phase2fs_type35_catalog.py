#!/usr/bin/env python3
"""Phase 2fs: deepen type-0x35 handle table ownership / index→OG catalog (RO).
Also short COrderInstance re-probe. No Post. Never 5x. allow_post stays False.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
import cmd_layout
import post_abi
from handle import (
    resolve_handle,
    HANDLE_TYPE_ARMY,
    HANDLE_TYPE_TABLE,
    HANDLE_HASH_MUL,
    _sx32,
)

assert allow_post() is False, "allow_post must stay False"

ASSIGN_VT = cmd_layout.ORDERS["COrderAssignCommand"]["vt"]
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = int(cmd_layout.ISVALID_PATHS["COrderReplaceFallbackCommands"]["vt"])

RTTI_VT = {
    "COrdersGroup": 0x29CED90,
    "COrdersGroupMember": 0x29CED48,
    "COrderInstance": 0x2A02558,
}
TYPE_OG = 0x35
STRIDE = 0x3D0


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


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
        "scenario": "ITA@1x type-0x35 catalog / Instance re-probe (no Post)",
        "gs": hex(gs),
        "gs_int": gs,
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


def heap_scan_vt(b, base, needles, max_samples=64, chunk=4 << 20, time_budget_s=40.0):
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


def dump_reg_layout(b, reg):
    raw = try_read(b, reg, 0x40)
    if not raw:
        return {"reg": hex(reg), "readable": False}
    words = [struct.unpack_from("<Q", raw, i)[0] for i in range(0, 0x40, 8)]
    u32s = [struct.unpack_from("<I", raw, i)[0] for i in range(0, 0x40, 4)]
    buckets = words[1] if len(words) > 1 else 0
    mask = u32s[5] if len(u32s) > 5 else None  # +0x14
    return {
        "reg": hex(reg),
        "readable": True,
        "qwords": [hex(x) for x in words],
        "u32s": [hex(x) for x in u32s],
        "buckets": hex(buckets) if buckets else None,
        "mask": mask,
        "mask_hex": hex(mask) if mask is not None else None,
        "slot_count_estimate": (mask + 1) if mask is not None else None,
        # common extras (document observed only)
        "plus00_q": hex(words[0]),
        "plus08_buckets": hex(buckets),
        "plus10_u32": hex(u32s[4]),
        "plus14_mask": hex(u32s[5]),
        "plus18_u32": hex(u32s[6]),
        "plus1c_u32": hex(u32s[7]),
        "plus20_q": hex(words[4]),
        "plus28_q": hex(words[5]),
        "plus30_q": hex(words[6]),
        "plus38_q": hex(words[7]),
    }


def walk_type35_catalog(b, base, reg, typ=TYPE_OG, max_entries=4096):
    """Enumerate hash table entries for typ by probing every bucket + chain walk
    matching resolve_handle's layout. Document only; no invent of field names beyond
    what handle.py already encodes.
    """
    buckets = u64(b, reg + 8)
    mask = u32(b, reg + 0x14)
    entries = []
    by_index = {}
    t0 = time.time()
    # For each bucket index h in [0, mask], walk chain like resolve_handle
    for h in range(mask + 1):
        if len(entries) >= max_entries:
            break
        rax = buckets + h * 24
        try:
            first_u8 = u8(b, rax + 4)
        except Exception:
            continue
        if first_u8 < 1:
            continue
        cl = 1
        cur = rax
        while True:
            try:
                etyp = u32(b, cur + 0x8)
                eidx = u32(b, cur + 0xC)
                eptr = u64(b, cur + 0x10)
            except Exception:
                break
            if etyp == typ:
                obj = eptr - 0x10
                nm, rva = rtti_name(b, base, obj)
                # echo at obj+0x18
                echo = None
                echo_ok = None
                try:
                    echo = list(struct.unpack("<II", b.read(obj + 0x18, 8)))
                    echo_ok = echo == [etyp, eidx]
                except Exception:
                    pass
                # also check if obj+0x10 is COrdersGroup VT (obj itself may be header)
                # 2fr: resolved = OG_addr - 0x10, so OG RTTI is at obj+0x10
                og_addr = obj + 0x10
                og_nm, og_rva = rtti_name(b, base, og_addr)
                rec = {
                    "bucket_h": h,
                    "slot": hex(cur),
                    "index": eidx,
                    "obj_header": hex(obj),
                    "obj_ptr_field": hex(eptr),
                    "header_rtti": nm,
                    "header_vt_rva": rva,
                    "og_candidate": hex(og_addr),
                    "og_rtti": og_nm,
                    "og_vt_rva": og_rva,
                    "echo_plus18": echo,
                    "echo_matches": echo_ok,
                    "resolve_check": None,
                }
                # cross-check resolve_handle
                try:
                    got = resolve_handle(b, typ, eidx, base)
                    rec["resolve_check"] = hex(got) if got else None
                    rec["resolve_matches_header"] = got == obj
                except Exception as e:
                    rec["resolve_error"] = str(e)
                entries.append(rec)
                by_index[eidx] = rec
            cl += 1
            cur += 0x18
            try:
                lim = u8(b, cur + 4)
            except Exception:
                break
            if cl > lim or cl > 128:
                break
    return {
        "buckets": hex(buckets),
        "mask": mask,
        "bucket_slots": mask + 1,
        "entries_n": len(entries),
        "indices": sorted(by_index.keys()),
        "index_min": min(by_index) if by_index else None,
        "index_max": max(by_index) if by_index else None,
        "og_rtti_n": sum(1 for e in entries if e.get("og_rtti") == "COrdersGroup"),
        "echo_ok_n": sum(1 for e in entries if e.get("echo_matches")),
        "resolve_ok_n": sum(1 for e in entries if e.get("resolve_matches_header")),
        "elapsed_s": round(time.time() - t0, 3),
        "entries_sample": entries[:24],
        "entries_all": entries,  # kept for cross-check; trimmed in report write if huge
    }


def cross_check_og_heap(b, base, og_addrs, by_index):
    """For each live COrdersGroup, compare +0xc index against catalog."""
    out = []
    hit = 0
    miss = 0
    for addr in og_addrs:
        blob = try_read(b, addr, 0x20)
        if not blob or len(blob) < 0x10:
            continue
        t8, i8 = struct.unpack_from("<II", blob, 0x8)
        cat = by_index.get(i8)
        row = {
            "og": hex(addr),
            "plus8_type": t8,
            "plus0c_index": i8,
            "in_catalog": cat is not None,
        }
        if cat:
            hit += 1
            # catalog says header = og - 0x10
            row["catalog_header"] = cat["obj_header"]
            row["expected_header"] = hex(addr - 0x10)
            row["header_match"] = cat["obj_header"] == hex(addr - 0x10)
            row["catalog_og_rtti"] = cat.get("og_rtti")
        else:
            miss += 1
        out.append(row)
    return {
        "checked": len(out),
        "catalog_hit": hit,
        "catalog_miss": miss,
        "header_match_n": sum(1 for r in out if r.get("header_match")),
        "rows": out,
    }


def find_reg_owner_static(b, base, reg, gs):
    """Cheap ownership probes: does HANDLE_TYPE_TABLE slot equal reg (already known);
    does G_GAMESTATE or nearby statics point at reg? Scan a few known RVAs only — no invent.
    Also scan first 0x800 of gs for a qword == reg (bounded).
    """
    findings = []
    # confirm table slot
    slot = base + HANDLE_TYPE_TABLE + TYPE_OG * 8
    try:
        slot_val = u64(b, slot)
        findings.append(
            {
                "kind": "HANDLE_TYPE_TABLE_slot",
                "addr": hex(slot),
                "rva": hex(HANDLE_TYPE_TABLE + TYPE_OG * 8),
                "value": hex(slot_val),
                "equals_reg": slot_val == reg,
            }
        )
    except Exception as e:
        findings.append({"kind": "HANDLE_TYPE_TABLE_slot", "error": str(e)})

    # bounded gs peek for pointer == reg
    gs_hits = []
    raw = try_read(b, gs, 0x800)
    if raw:
        needle = struct.pack("<Q", reg)
        off = 0
        while True:
            i = raw.find(needle, off)
            if i < 0:
                break
            if i % 8 == 0:
                gs_hits.append(hex(i))
            off = i + 8
            if len(gs_hits) >= 8:
                break
    findings.append({"kind": "gs_qword_eq_reg", "offs": gs_hits, "n": len(gs_hits)})

    # also check if reg+0 points into image (vtable-like)
    try:
        q0 = u64(b, reg)
        findings.append(
            {
                "kind": "reg_plus0",
                "value": hex(q0),
                "in_image": base <= q0 < base + b.image_size,
                "rva_if_image": hex(q0 - base) if base <= q0 < base + b.image_size else None,
            }
        )
    except Exception:
        pass
    return findings


def stage_nf(b, base, seconds: float):
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
            if name == "COrderAssignCommand" and len(assigns) < 8:
                oi = u32(b, ptr + 0x48)
                assigns.append({"addr": hex(ptr), "t": t, "order_index": oi})
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


def main():
    pid = find_pid()
    b = Backend(pid)
    base = b.image_base
    live0 = live_meta(b, base)
    print(f"[2fs] live {live0['ui_date']} pid {pid}", flush=True)
    assert allow_post() is False

    reg = u64(b, base + HANDLE_TYPE_TABLE + TYPE_OG * 8)
    print(f"[2fs] HANDLE_TYPE_TABLE[0x35]={hex(reg)}", flush=True)
    reg_layout = dump_reg_layout(b, reg)

    print("[2fs] walk type-0x35 catalog…", flush=True)
    cat = walk_type35_catalog(b, base, reg)
    by_index = {e["index"]: e for e in cat["entries_all"]}
    print(
        f"[2fs] catalog entries={cat['entries_n']} indices={cat['index_min']}..{cat['index_max']} "
        f"og_rtti={cat['og_rtti_n']} echo_ok={cat['echo_ok_n']} resolve_ok={cat['resolve_ok_n']}",
        flush=True,
    )

    print("[2fs] ownership probes…", flush=True)
    owners = find_reg_owner_static(b, base, reg, live0["gs_int"])

    print("[2fs] heap scan OG+Instance ≤40s…", flush=True)
    heap = heap_scan_vt(
        b,
        base,
        {"COrdersGroup": RTTI_VT["COrdersGroup"], "COrderInstance": RTTI_VT["COrderInstance"]},
        max_samples=32,
        time_budget_s=40.0,
    )
    print(f"[2fs] heap {heap['counts']}", flush=True)

    og_addrs = heap["sample_addrs"].get("COrdersGroup", [])
    cross = cross_check_og_heap(b, base, og_addrs, by_index)
    print(
        f"[2fs] OG cross-check hit={cross['catalog_hit']} miss={cross['catalog_miss']} "
        f"header_match={cross['header_match_n']}",
        flush=True,
    )

    pool = expand_pool(b, base, heap["sample_addrs"].get("COrderInstance", []))
    print(f"[2fs] Instance pool len={pool['len']} base={pool['base']}", flush=True)

    # oi→slot only if pool live
    index_map = {"ok": False, "reason": "empty pool"}
    if pool["len"] > 0:
        # short assign sight for ois
        sight_short = stage_nf(b, base, 15.0)
        ois = sorted({a["order_index"] for a in sight_short["assigns"]})
        pbase = int(pool["base"], 16)
        hits = []
        for oi in ois:
            slot = pbase + oi * STRIDE
            blob = try_read(b, slot, 8)
            vt_ok = False
            if blob:
                vt_ok = struct.unpack("<Q", blob)[0] == base + RTTI_VT["COrderInstance"]
            hits.append({"oi": oi, "slot": hex(slot), "vt_match": vt_ok})
        index_map = {
            "ok": any(h["vt_match"] for h in hits) if hits else False,
            "test_ois": ois,
            "hits": hits,
            "oi_fits": (max(ois) < pool["len"]) if ois else None,
            "sight": sight_short,
        }
        print(f"[2fs] oi→pool {index_map}", flush=True)
        sight = sight_short
        nf_ran = False
        nf = {"skipped": True, "reason": "A progressed and/or Instance path took short sight"}
    else:
        sight = {"elapsed_s": 0, "sight_counts": {}, "assigns": [], "fallbacks": [], "replace_fallbacks": []}

    a_progress = cat["entries_n"] > 0 and cross["catalog_hit"] > 0
    b_progress = pool["len"] > 0 and index_map.get("ok")

    nf_ran = False
    nf = {"skipped": True, "reason": "A or B produced progress"}
    if not a_progress and not b_progress:
        print("[2fs] A+B thin → bounded NF/RF 75s…", flush=True)
        nf = stage_nf(b, base, 75.0)
        sight = nf
        nf_ran = True
        print(f"[2fs] NF sight {nf['sight_counts']}", flush=True)
    elif not pool["len"]:
        # A progressed; optional tiny assign peek already skipped — keep NF skipped
        pass

    live1 = live_meta(b, base)

    # trim entries_all from report (keep sample + indices list)
    cat_report = {k: v for k, v in cat.items() if k != "entries_all"}

    if a_progress:
        result = "type35_index_og_catalog_documented"
    elif b_progress:
        result = "order_instance_pool_oi_mapped"
    elif nf_ran:
        result = "nf_midflight_bounded"
    else:
        result = "type35_deepen_inconclusive"

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"HANDLE_TYPE_TABLE[0x35]={hex(reg)} mask={reg_layout.get('mask')} buckets={reg_layout.get('buckets')}",
        f"type-0x35 catalog entries={cat['entries_n']} indices={cat['index_min']}..{cat['index_max']} "
        f"og_rtti={cat['og_rtti_n']} echo_ok={cat['echo_ok_n']} resolve_ok={cat['resolve_ok_n']}",
        f"OG heap cross-check hit={cross['catalog_hit']}/{cross['checked']} header_match={cross['header_match_n']}",
        f"heap COrderInstance={heap['counts'].get('COrderInstance')} COrdersGroup={heap['counts'].get('COrdersGroup')}",
        f"Instance pool len={pool['len']}",
        f"ownership probes: {json.dumps(owners)[:200]}",
    ]
    if nf_ran:
        works.append(f"NF midflight {nf.get('elapsed_s')}s counts={nf.get('sight_counts')}")

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
        "live midflight NewFallback hex" if not (nf_ran and nf.get("fallbacks")) else "NF empty this window",
        "order_index→COrderInstance pool-slot proven",
        "stable G_GAMESTATE→pool root pointer path",
        "full G_GAMESTATE→type-0x35-reg owner path" if not any(
            f.get("kind") == "gs_qword_eq_reg" and f.get("n", 0) > 0 for f in owners
        ) else "gs→reg pointer noted",
    ]

    next_blocker = (
        "NON-Post: use type-0x35 index catalog as OG root OR re-probe COrderInstance when live "
        "OR bounded NF/RF subject midflight; still NO ALLOW_POST"
    )
    if a_progress:
        next_blocker = (
            "NON-Post: tie battle-plan order_index to type-0x35/OG graph OR re-probe "
            "COrderInstance pool when Instances live; NF/RF midflight still open; still NO ALLOW_POST"
        )

    report = {
        "phase": "2fs",
        "ts": datetime.utcnow().isoformat() + "Z",
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "6b77760",
        "live_at_start": {k: v for k, v in live0.items() if k != "gs_int"},
        "live": {k: v for k, v in live1.items() if k != "gs_int"},
        "reg_layout": reg_layout,
        "catalog": cat_report,
        "ownership": owners,
        "heap": {k: v for k, v in heap.items() if k != "sample_addrs"},
        "og_cross_check": cross,
        "pool": pool,
        "index_map": index_map,
        "sight": sight,
        "nf_midflight_ran": nf_ran,
        "nf_midflight": nf if nf_ran else nf,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "push_note": "push+sync PC; one try",
    }

    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "phase2fs_type35_catalog.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fs",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "ui_date_start": live0["ui_date"],
        "scenario": live1["scenario"],
        "speed_policy": live1["speed_policy"],
        "catalog_entries": cat["entries_n"],
        "catalog_og_rtti_n": cat["og_rtti_n"],
        "og_cross_hit": cross["catalog_hit"],
        "instance_pool_len": pool["len"],
        "nf_midflight_ran": nf_ran,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "6b77760",
    }
    (ROOT / "reports" / "phase2fs_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
