#!/usr/bin/env python3
"""Phase 2gc: bounded NF/RF midflight RO observe @1x ITA (60–90s max).
No Post. Never 5x. allow_post False. No relaunch. Honest empty OK.
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
import post_abi
import cmd_layout

assert allow_post() is False, "allow_post must stay False"

WINDOW_S = 75.0
INTERVAL_S = 0.05
HEAP_EVERY = 40  # every ~2s
HEAP_MB = 192
NF_SIZE = 0x60  # 2fl proven

NF = cmd_layout.ORDERS["COrderNewFallbackCommand"]
NF_VT = NF["vt"]
RF_VT = 0x2A84D38  # catalog (not in ORDERS top-level; from cmd_layout role table)
AG_VT = 0x2A86158  # CSetSelectedArmyGroupFallback ≈ 44589400

WATCH = {
    NF_VT: "COrderNewFallbackCommand",
    RF_VT: "COrderReplaceFallbackCommands",
    AG_VT: "CSetSelectedArmyGroupFallback",
    # light context (not focus)
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]: "COrderExecuteCommand",
    cmd_layout.ORDERS.get("COrderNewFrontCommand", {}).get("vt") or 0: "COrderNewFrontCommand",
}
WATCH = {k: v for k, v in WATCH.items() if k}


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


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def live_meta(b, base):
    gs = None
    for cand in (0x2A0A0A8, 0x2A09F28, 0x2A0A000):
        p = try_u64(b, base + cand)
        if not p:
            continue
        h = None
        try:
            h = i32(b, p + 0x484)
        except Exception:
            pass
        if h is not None and 0 <= h < 200000:
            gs = p
            hours = h
            break
    if gs is None:
        return {"pid": find_pid(), "error": "gs not found"}
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "pid": find_pid(),
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x bounded NF/RF midflight (no Post)",
        "gs": hex(gs),
    }


def decode_nf(blob: bytes, base: int, addr: int, name: str) -> dict:
    fields = NF.get("fields") or {}
    out = {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(struct.unpack_from("<Q", blob, 0)[0] - base),
        "type_id_at_plus8": struct.unpack_from("<I", blob, 8)[0] if len(blob) >= 12 else None,
        "hex": blob[:NF_SIZE].hex() if len(blob) >= NF_SIZE else blob.hex(),
        "fields_decoded": {},
    }
    if len(blob) < NF_SIZE:
        out["short"] = True
        return out
    # subject_handle is often 8 bytes (two u32) at +0x28
    sh = fields.get("subject_handle", 0x28)
    out["fields_decoded"]["subject_handle"] = [
        struct.unpack_from("<I", blob, sh)[0],
        struct.unpack_from("<I", blob, sh + 4)[0],
    ]
    # units CPdxArray-ish at +0x30
    ud = fields.get("units_data", 0x30)
    ucap = fields.get("units_capacity", 0x38)
    ucnt = fields.get("units_count", 0x3C)
    out["fields_decoded"]["units"] = {
        "data": hex(struct.unpack_from("<Q", blob, ud)[0]),
        "capacity": struct.unpack_from("<i", blob, ucap)[0],
        "count": struct.unpack_from("<i", blob, ucnt)[0],
    }
    pd = fields.get("provinces_data", 0x48)
    pcap = fields.get("provinces_capacity", 0x50)
    psz = fields.get("provinces_size", 0x54)
    out["fields_decoded"]["provinces"] = {
        "data": hex(struct.unpack_from("<Q", blob, pd)[0]),
        "capacity": struct.unpack_from("<i", blob, pcap)[0],
        "size": struct.unpack_from("<i", blob, psz)[0],
    }
    # sample province ids if size small
    psz_v = out["fields_decoded"]["provinces"]["size"]
    pdata = struct.unpack_from("<Q", blob, pd)[0]
    if 0 < psz_v <= 32 and pdata > 0x10000:
        # caller fills via Backend later
        out["fields_decoded"]["provinces"]["data_int"] = pdata
        out["fields_decoded"]["provinces"]["size_int"] = psz_v
    return out


def dump_focus(b, base, addr, name):
    blob = try_read(b, addr, 0x80) or b""
    if name in ("COrderNewFallbackCommand", "COrderReplaceFallbackCommands"):
        rec = decode_nf(blob, base, addr, name)
        prov = rec.get("fields_decoded", {}).get("provinces", {})
        if prov.get("data_int") and prov.get("size_int"):
            raw = try_read(b, prov["data_int"], min(prov["size_int"], 16) * 4) or b""
            ids = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(len(raw) // 4)]
            rec["fields_decoded"]["provinces"]["ids_sample"] = ids
        return rec
    vt = struct.unpack_from("<Q", blob, 0)[0] - base if len(blob) >= 8 else None
    return {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(vt) if vt is not None else None,
        "hex": blob[:0x40].hex(),
    }


def walk_ptr_list(b, base, head, limit=64):
    hits = []
    seen = set()
    cur = head
    while cur and cur not in seen and len(hits) < limit:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = WATCH.get(vt - base)
        if name:
            try:
                hits.append({"source": "pending", **dump_focus(b, base, cur, name)})
            except Exception as e:
                hits.append({"source": "pending", "addr": hex(cur), "name": name, "error": str(e)})
        nxt = try_u64(b, cur + 8)
        if nxt is None or nxt == cur:
            break
        cur = nxt
    return hits


def sample_queues(b, base, sess, server):
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    seq = u32(b, server + 0xD0)
    counters = {"drain": drain, "exec": exec_c, "seq": seq, "stage_count": scount}
    watched = walk_ptr_list(b, base, pending_h)
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            name = WATCH.get(vt - base)
            if not name:
                continue
            try:
                watched.append({"source": f"stage[{i}]", **dump_focus(b, base, ptr, name)})
            except Exception as e:
                watched.append({"source": f"stage[{i}]", "addr": hex(ptr), "name": name, "error": str(e)})
    return watched, counters


def heap_scan_nf(b, base, mb=HEAP_MB):
    """RO writable-heap scan for NF/RF VT needles; bounded MB."""
    try:
        from mem import Proc
        from process import find_pid as fp

        src = Proc(fp("hoi4.exe"))
    except Exception as e:
        return {"error": repr(e), "hits": []}
    needles = {
        "COrderNewFallbackCommand": struct.pack("<Q", base + NF_VT),
        "COrderReplaceFallbackCommands": struct.pack("<Q", base + RF_VT),
    }
    found, scanned = [], 0
    try:
        regions = list(src.regions(writable=True, min_size=0x1000))
    except Exception as e:
        return {"error": repr(e), "hits": []}
    for m in regions:
        start_m, end_m = m["start"], m["end"]
        if base <= start_m < base + 0x4000000:
            continue
        pos = start_m
        while pos < end_m and scanned < (mb << 20) and len(found) < 6:
            n = min(1 << 20, end_m - pos)
            data = None
            try:
                data = src.try_read(pos, n) if hasattr(src, "try_read") else src.read(pos, n)
            except Exception:
                data = None
            scanned += n
            if data:
                for name, needle in needles.items():
                    j = 0
                    while True:
                        j = data.find(needle, j)
                        if j < 0:
                            break
                        addr = pos + j
                        try:
                            found.append({"source": "heap", **dump_focus(b, base, addr, name)})
                        except Exception as e:
                            found.append({"source": "heap", "addr": hex(addr), "name": name, "error": str(e)})
                        j += 8
                        if len(found) >= 6:
                            break
            pos += n
        if len(found) >= 6:
            break
    return {"scanned_mb": scanned >> 20, "hits": found}


def main():
    assert allow_post() is False
    b = Backend()
    base = b.image_base
    meta = live_meta(b, base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)

    t0 = time.time()
    polls = 0
    sight = {}
    first = {}
    last = {}
    nf_rf_captures = []
    edge_events = 0
    prev = None
    heap_runs = 0
    heap_hits_total = 0

    deadline = t0 + WINDOW_S
    while time.time() < deadline:
        polls += 1
        watched, counters = sample_queues(b, base, sess, server)
        if prev is not None and (
            counters["drain"] != prev["drain"]
            or counters["exec"] != prev["exec"]
            or counters["seq"] != prev["seq"]
        ):
            edge_events += 1
            # burst a few RO samples on edge
            for _ in range(8):
                w2, counters = sample_queues(b, base, sess, server)
                watched.extend(w2)
                if any(h.get("name", "").startswith("COrder") and "Fallback" in h.get("name", "") for h in w2):
                    break
        prev = dict(counters)

        for hit in watched:
            name = hit.get("name") or "?"
            sight[name] = sight.get(name, 0) + 1
            meta_h = {
                "source": hit.get("source"),
                "addr": hit.get("addr"),
                "poll": polls,
                "counters": dict(counters),
            }
            if name not in first:
                first[name] = meta_h
            last[name] = meta_h
            if name in ("COrderNewFallbackCommand", "COrderReplaceFallbackCommands"):
                # dedupe by addr
                if not any(c.get("addr") == hit.get("addr") for c in nf_rf_captures):
                    nf_rf_captures.append(hit)

        if HEAP_EVERY and polls % HEAP_EVERY == 0 and len(nf_rf_captures) < 3:
            heap_runs += 1
            hs = heap_scan_nf(b, base)
            for hit in hs.get("hits") or []:
                heap_hits_total += 1
                name = hit.get("name")
                sight[f"heap:{name}"] = sight.get(f"heap:{name}", 0) + 1
                if name in ("COrderNewFallbackCommand", "COrderReplaceFallbackCommands"):
                    if not any(c.get("addr") == hit.get("addr") for c in nf_rf_captures):
                        nf_rf_captures.append(hit)

        # early stop if we already have decoded NF/RF with nonempty provinces/units
        rich = [
            c for c in nf_rf_captures
            if (c.get("fields_decoded") or {}).get("provinces", {}).get("size", 0) > 0
            or (c.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
        ]
        if rich:
            break

        time.sleep(INTERVAL_S)

    elapsed = round(time.time() - t0, 2)
    meta2 = live_meta(b, base)

    if nf_rf_captures:
        rich = [
            c for c in nf_rf_captures
            if (c.get("fields_decoded") or {}).get("provinces", {}).get("size", 0) > 0
            or (c.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
        ]
        if rich:
            result = "nf_rf_midflight_hex_captured_nonempty"
            note = f"captured {len(nf_rf_captures)} NF/RF objs; nonempty subject fields in {len(rich)}"
        else:
            result = "nf_rf_midflight_hex_captured_empty_fields"
            note = f"captured {len(nf_rf_captures)} NF/RF objs but units/provinces empty this window"
    else:
        result = "nf_rf_midflight_empty_window"
        note = (
            f"bounded {elapsed}s @1x ITA: no NF/RF on pending/stage/heap; "
            f"honest empty (peace-time ITA may not emit fallback cmds)"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        f"bounded window {elapsed}s polls={polls} edges={edge_events} heap_runs={heap_runs}",
        "watched NF/RF/AG + Assign/Execute/NewFront on pending/stage",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "war-dense relaunch (B preferred this slice)",
        "named CArmy path-field offsets",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "named +0x100 elem class beyond allocator soft-VT",
        "named +0xe0 role beyond u32 province stream",
        "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
    ]
    if result.startswith("nf_rf_midflight_empty"):
        stubbed.append("live midflight NewFallback hex (empty this peace-time window)")
        next_blocker = (
            "NON-Post: war-dense ETH/ITA relaunch for NF/RF or named CArmy path; still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: deepen NF subject_handle semantic from live hex OR war-dense named CArmy path; "
            "still NO ALLOW_POST"
        )

    detail = {
        "phase": "2gc",
        "allow_post": False,
        "window_s": WINDOW_S,
        "elapsed_s": elapsed,
        "polls": polls,
        "edge_events": edge_events,
        "heap_runs": heap_runs,
        "heap_hits_total": heap_hits_total,
        "watch_vts": {hex(k): v for k, v in WATCH.items()},
        "sight_counts": sight,
        "sight_first": first,
        "sight_last": last,
        "nf_rf_captures": nf_rf_captures[:8],
        "last_counters": prev,
        "live_start": meta,
        "live_end": meta2,
    }
    summary = {
        "phase": "2gc",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta2,
        "window": {"elapsed_s": elapsed, "polls": polls, "edges": edge_events, "heap_runs": heap_runs},
        "sight_counts": sight,
        "nf_rf_capture_count": len(nf_rf_captures),
        "nf_rf_captures_sample": nf_rf_captures[:4],
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "phase2gc_nf_rf_midflight.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    (out / "phase2gb_summary.json")  # noqa keep prior
    (out / "phase2gc_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "elapsed_s": elapsed,
        "polls": polls,
        "captures": len(nf_rf_captures),
        "sight": sight,
        "ui_date": meta2.get("ui_date"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
