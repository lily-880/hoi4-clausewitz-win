#!/usr/bin/env python3
"""Phase 2gh: longer ITA war-day observe + heap/stage Assign corner.
Current process. No Post. Never 5x. ≤90s. allow_post False.
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
import post_abi
import cmd_layout
from handle import resolve_handle, HANDLE_TYPE_ARMY

assert allow_post() is False

OBSERVE_S = 90.0
INTERVAL_S = 0.07
HEAP_EVERY = 40
HEAP_MB = 48
TYPE_OG = 0x35
HANDLE_STRIDE = 8
CMOVE_VT = 0x2A2C790
RF_VT = 0x2A84D38

ASSIGN = cmd_layout.ORDERS["COrderAssignCommand"]
UNASSIGN = cmd_layout.ORDERS["COrderUnassignCommand"]
EXECUTE = cmd_layout.ORDERS["COrderExecuteCommand"]
DELETE = cmd_layout.ORDERS["COrderDeleteCommand"]
NF = cmd_layout.ORDERS["COrderNewFallbackCommand"]

FOCUS = {
    ASSIGN["vt"]: "COrderAssignCommand",
    UNASSIGN["vt"]: "COrderUnassignCommand",
    EXECUTE["vt"]: "COrderExecuteCommand",
    DELETE["vt"]: "COrderDeleteCommand",
    NF["vt"]: "COrderNewFallbackCommand",
    RF_VT: "COrderReplaceFallbackCommands",
    CMOVE_VT: "CMoveCommand",
}
# heap needles: plan leaves only (Preferred B)
HEAP_FOCUS = {
    ASSIGN["vt"]: "COrderAssignCommand",
    UNASSIGN["vt"]: "COrderUnassignCommand",
    EXECUTE["vt"]: "COrderExecuteCommand",
}


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


def live_meta(b, base, scenario: str):
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
        "scenario": scenario,
        "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1",
        "gs": hex(gs),
    }


def decode_units(b, base, data_ptr, size):
    size = max(0, min(int(size), 24))
    if data_ptr < 0x10000 or size <= 0:
        return {"size": size, "data": hex(data_ptr), "elements": [], "army_resolve_ok": 0}
    raw = try_read(b, data_ptr, size * HANDLE_STRIDE) or b""
    elems = []
    army_ok = 0
    for i in range(size):
        o = i * HANDLE_STRIDE
        if o + 8 > len(raw):
            break
        typ, ix = struct.unpack_from("<II", raw, o)
        resolved = None
        if typ and ix:
            try:
                resolved = resolve_handle(b, typ, ix, base)
            except Exception:
                resolved = None
            if typ == HANDLE_TYPE_ARMY and resolved:
                army_ok += 1
        elems.append({
            "i": i, "type": typ, "index": ix,
            "note": "HANDLE_TYPE_ARMY" if typ == HANDLE_TYPE_ARMY else None,
            "resolved": hex(resolved) if resolved else None,
        })
    return {"size": size, "data": hex(data_ptr), "elements": elems, "army_resolve_ok": army_ok}


def decode_leaf(b, base, addr, name):
    blob = try_read(b, addr, 0x58) or b""
    out = {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(struct.unpack_from("<Q", blob, 0)[0] - base) if len(blob) >= 8 else None,
        "hex": blob.hex(),
        "fields_decoded": {},
    }
    if len(blob) < 0x40:
        return out
    if name == "COrderAssignCommand":
        f = ASSIGN["fields"]
        data = struct.unpack_from("<Q", blob, f["units_data"])[0]
        cnt = struct.unpack_from("<i", blob, f["units_count"])[0]
        oi = struct.unpack_from("<I", blob, f["order_index"])[0]
        out["fields_decoded"]["units"] = decode_units(b, base, data, cnt)
        out["fields_decoded"]["units"]["count"] = cnt
        out["fields_decoded"]["order_index"] = oi
        og = None
        try:
            og = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            og = None
        out["fields_decoded"]["order_index_as_type35"] = {
            "order_index": oi, "resolve_ok": bool(og),
            "og_or_hdr": hex(og) if og else None,
        }
    elif name == "COrderUnassignCommand":
        f = UNASSIGN["fields"]
        data = struct.unpack_from("<Q", blob, f["units_data"])[0]
        cnt = struct.unpack_from("<i", blob, f["units_count"])[0]
        out["fields_decoded"]["units"] = decode_units(b, base, data, cnt)
        out["fields_decoded"]["units"]["count"] = cnt
    elif name == "COrderExecuteCommand":
        f = EXECUTE["fields"]
        oi = struct.unpack_from("<I", blob, f["order_index"])[0]
        og = None
        try:
            og = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            og = None
        out["fields_decoded"] = {
            "order_index": oi,
            "execute_order": struct.unpack_from("<B", blob, f["execute_order"])[0],
            "all": struct.unpack_from("<B", blob, f["all"])[0],
            "order_index_as_type35": {
                "order_index": oi, "resolve_ok": bool(og),
                "og_or_hdr": hex(og) if og else None,
            },
        }
    elif name in ("COrderNewFallbackCommand", "COrderReplaceFallbackCommands"):
        sh = (NF.get("fields") or {}).get("subject_handle", 0x28)
        if len(blob) >= sh + 8:
            out["fields_decoded"]["subject_handle"] = list(struct.unpack_from("<II", blob, sh))
    elif name == "CMoveCommand" and len(blob) >= 0x30:
        out["fields_decoded"] = {"action_embed_plus28": hex(struct.unpack_from("<Q", blob, 0x28)[0])}
    return out


def walk_pending_stage(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    counters = {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "seq": u32(b, server + 0xD0),
        "stage_count": scount,
    }
    hits = []
    seen = set()
    cur = pending_h
    while cur and cur not in seen and len(hits) < 96:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = FOCUS.get(vt - base)
        if name:
            hits.append({"source": "pending", **decode_leaf(b, base, cur, name)})
        nxt = try_u64(b, cur + 8)
        if not nxt or nxt == cur:
            break
        cur = nxt
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            name = FOCUS.get(vt - base)
            if name:
                hits.append({"source": f"stage[{i}]", **decode_leaf(b, base, ptr, name)})
    return hits, counters


def heap_scan_plan(b, base, mb=HEAP_MB):
    """Bounded writable-heap VT needle scan for Assign/Unassign/Execute."""
    try:
        from mem import Proc
        src = Proc(find_pid())
    except Exception as e:
        return {"error": repr(e), "hits": [], "scanned_mb": 0}
    needles = {name: struct.pack("<Q", base + vt) for vt, name in HEAP_FOCUS.items()}
    found, scanned = [], 0
    try:
        regions = list(src.regions(writable=True, min_size=0x1000))
    except Exception as e:
        return {"error": repr(e), "hits": [], "scanned_mb": 0}
    for m in regions:
        start_m, end_m = m["start"], m["end"]
        if base <= start_m < base + 0x4000000:
            continue
        pos = start_m
        while pos < end_m and scanned < (mb << 20) and len(found) < 8:
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
                            found.append({"source": "heap", **decode_leaf(b, base, addr, name)})
                        except Exception as e:
                            found.append({"source": "heap", "addr": hex(addr), "name": name, "error": str(e)})
                        j += 8
                        if len(found) >= 8:
                            break
            pos += n
        if len(found) >= 8:
            break
    return {"scanned_mb": scanned >> 20, "hits": found}


def main():
    assert allow_post() is False
    scenario = "ITA longer war-day + heap Assign corner @1x (no Post)"

    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gh",
            "allow_post": False,
            "result": "NO_LIVE_PROCESS",
            "next_shortest_blocker": "NON-Post: restore ITA@1x then observe; still NO ALLOW_POST",
        }
        (ROOT / "reports" / "phase2gh_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2)[:800])
        return 1

    b = Backend()
    base = b.image_base
    meta0 = live_meta(b, base, scenario)

    t0 = time.time()
    polls = 0
    sight = Counter()
    caps = {k: [] for k in FOCUS.values()}
    heap_caps = {k: [] for k in HEAP_FOCUS.values()}
    seen = set()
    heap_seen = set()
    last_counters = None
    heap_runs = 0
    heap_mb_total = 0
    last_heap = None

    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = walk_pending_stage(b, base)
        for h in hits:
            name = h.get("name") or "?"
            sight[name] += 1
            key = (name, h.get("addr"))
            if name in caps and key not in seen:
                seen.add(key)
                caps[name].append(h)

        if polls % HEAP_EVERY == 1:
            heap_runs += 1
            last_heap = heap_scan_plan(b, base)
            heap_mb_total = max(heap_mb_total, last_heap.get("scanned_mb") or 0)
            for h in last_heap.get("hits") or []:
                name = h.get("name") or "?"
                sight[f"heap:{name}"] += 1
                key = (name, h.get("addr"))
                if name in heap_caps and key not in heap_seen:
                    heap_seen.add(key)
                    heap_caps[name].append(h)

        # early stop on useful Assign (pending or heap) with units
        rich = [
            a for a in caps.get("COrderAssignCommand", []) + heap_caps.get("COrderAssignCommand", [])
            if (a.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
            or (a.get("fields_decoded") or {}).get("units", {}).get("size", 0) > 0
        ]
        if rich:
            break
        time.sleep(INTERVAL_S)

    elapsed = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, scenario)

    n_assign = len(caps["COrderAssignCommand"]) + len(heap_caps["COrderAssignCommand"])
    n_unassign = len(caps["COrderUnassignCommand"]) + len(heap_caps["COrderUnassignCommand"])
    n_exec = len(caps["COrderExecuteCommand"]) + len(heap_caps["COrderExecuteCommand"])
    n_nf = len(caps["COrderNewFallbackCommand"]) + len(caps["COrderReplaceFallbackCommands"])
    n_move = len(caps["CMoveCommand"])
    pending_assign = len(caps["COrderAssignCommand"])
    heap_assign = len(heap_caps["COrderAssignCommand"])

    units_nz = sum(
        1 for a in caps["COrderAssignCommand"] + heap_caps["COrderAssignCommand"]
        + caps["COrderUnassignCommand"] + heap_caps["COrderUnassignCommand"]
        if (a.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
        or (a.get("fields_decoded") or {}).get("units", {}).get("size", 0) > 0
    )
    oi_ok = sum(
        1 for a in caps["COrderAssignCommand"] + heap_caps["COrderAssignCommand"]
        + caps["COrderExecuteCommand"] + heap_caps["COrderExecuteCommand"]
        if ((a.get("fields_decoded") or {}).get("order_index_as_type35") or {}).get("resolve_ok")
    )

    if pending_assign and units_nz:
        result = "ita_warday_assign_pending_hits"
        note = f"pending Assign={pending_assign} heap_Assign={heap_assign} units_nz={units_nz} oi35={oi_ok}"
    elif heap_assign and units_nz:
        result = "ita_warday_assign_heap_corner_hits"
        note = f"heap Assign={heap_assign} (pending={pending_assign}) units_nz={units_nz} oi35={oi_ok}; Exec={n_exec}"
    elif n_assign or n_unassign or n_exec:
        result = "ita_warday_plan_leaf_thin"
        note = f"Assign={n_assign} Unassign={n_unassign} Exec={n_exec} (pending_A={pending_assign} heap_A={heap_assign}) units_nz={units_nz}"
    elif n_nf or n_move:
        result = "ita_warday_nf_or_move_only"
        note = f"NF={n_nf} Move={n_move}; plan leaves empty"
    else:
        result = "ita_warday_and_heap_empty"
        note = (
            f"ITA war-day hours {meta0['hours']}→{meta1['hours']} bounded {elapsed}s: "
            f"pending/stage plan leaves=0; heap Assign/Unassign/Exec=0 "
            f"(runs={heap_runs} mb≤{heap_mb_total}); sight={dict(sight)}"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        "current-process longer ITA war-day observe (no relaunch)",
        f"bounded {elapsed}s polls={polls} hours {meta0['hours']}→{meta1['hours']}",
        f"heap Assign/Unassign/Execute corner runs={heap_runs} scanned_mb≤{heap_mb_total}",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "named +0x100 elem class beyond allocator soft-VT",
        "named +0xe0 role beyond u32 province stream",
        "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        "demangled CArmy path field names",
    ]
    if not n_assign and not n_unassign:
        stubbed.append("live midflight Assign/Unassign hex (empty pending+heap this window)")
    if not n_nf:
        stubbed.append("live midflight NewFallback hex")
    if not n_move:
        stubbed.append("ordinary CMove live leaf")

    if result == "ita_warday_and_heap_empty":
        next_blocker = (
            "NON-Post: RO ceiling — ITA war-day pending+heap plan leaves empty through denser hours; "
            "next cheapest catalog-only Post-readiness checklist consolidate OR "
            "pause-and-UI-plan scenario (still no ask-user right-click / no Post); still NO ALLOW_POST"
        )
    elif "heap_corner" in result:
        next_blocker = (
            "NON-Post: deepen heap Assign units/oi→0x35 from live hex; still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: deepen live Assign oi→OG member walk from war-day hits; still NO ALLOW_POST"
        )

    detail = {
        "phase": "2gh",
        "allow_post": False,
        "live_start": meta0,
        "live_end": meta1,
        "observe": {
            "elapsed_s": elapsed,
            "polls": polls,
            "last_counters": last_counters,
            "sight_counts": dict(sight),
            "pending_stage_captures": {k: v[:6] for k, v in caps.items() if v},
            "heap_captures": {k: v[:6] for k, v in heap_caps.items() if v},
            "heap_runs": heap_runs,
            "heap_scanned_mb_max": heap_mb_total,
            "last_heap_meta": {k: last_heap.get(k) for k in ("scanned_mb", "error") if last_heap} if last_heap else None,
            "units_nonzero": units_nz,
            "oi_type35_ok": oi_ok,
        },
    }
    summary = {
        "phase": "2gh",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta1,
        "observe_s": elapsed,
        "polls": polls,
        "pending_assign": pending_assign,
        "heap_assign": heap_assign,
        "assign_total": n_assign,
        "unassign_total": n_unassign,
        "execute_total": n_exec,
        "nf_total": n_nf,
        "move_total": n_move,
        "heap_runs": heap_runs,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "phase2gh_ita_warday_heap.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    (out / "phase2gh_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "elapsed_s": elapsed,
        "polls": polls,
        "sight": dict(sight),
        "pending_assign": pending_assign,
        "heap_assign": heap_assign,
        "exec": n_exec,
        "nf": n_nf,
        "move": n_move,
        "heap_runs": heap_runs,
        "ui_start": meta0.get("ui_date"),
        "ui_end": meta1.get("ui_date"),
        "hours": [meta0.get("hours"), meta1.get("hours")],
        "pid": meta1.get("pid"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
