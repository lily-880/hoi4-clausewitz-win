#!/usr/bin/env python3
"""Phase 2gr: Denser Assign oi≠0 churn (RO).

ONE RO slice. No Post / no ALLOW_POST / no 2fb|2gk execute / never 5x.
A) Brief 1x clock nudge (wait hours tick; never change speed), then ≤90s
   Assign/Unassign pending/stage + bounded heap-edge Assign VT corner.
   Require order_index≠0 → type-0x35 OG / Instance; cross units type=51 →
   CArmy with OG+0x50 ≡ CArmy+0xB8 (2gp/2gq).
B) If A quiet: OG+0x50 MI catalog polish only.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gr_assign_oi_dense.json"
SUMMARY = ROOT / "reports" / "phase2gr_summary.json"

CLOCK_NUDGE_S = 40.0
OBSERVE_S = 90.0
POLL_SLEEP = 0.04
HEAP_MB = 24
HEAP_MAX_HITS = 6
HEAP_SCANS_CAP = 4
HEAP_EVERY_S = 12.0
GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_B8 = 0x29D6FB8
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
CA_PROV = 0x28

ASSIGN = cmd_layout.ORDERS["COrderAssignCommand"]
UNASSIGN = cmd_layout.ORDERS["COrderUnassignCommand"]
FOCUS = {
    ASSIGN["vt"]: "COrderAssignCommand",
    UNASSIGN["vt"]: "COrderUnassignCommand",
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


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, country_tag, scenario):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + 0x34FFBE8)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING) if server else None
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "country_tag_filter": country_tag,
        "scenario": scenario,
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def decode_assign(b, base, addr, name):
    units_data = try_u64(b, addr + 0x28)
    units_size = try_u32(b, addr + 0x34) or 0
    units = []
    if units_data and 0 < units_size <= 64:
        blob = try_read(b, units_data, units_size * 8)
        if blob:
            for j in range(units_size):
                typ, ix = struct.unpack_from("<II", blob, j * 8)
                units.append({"type": typ, "index": ix})
    oi = try_u32(b, addr + 0x48)
    return {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex((try_u64(b, addr) or 0) - base),
        "order_index": oi,
        "units_size": units_size,
        "units": units,
        "assign_to_minimum_order": try_u32(b, addr + 0x4C)
        if name == "COrderAssignCommand"
        else None,
    }


def walk_pending_stage(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    counters = {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "stage_count": scount,
        "pending_nonzero": 1 if pending_h else 0,
    }
    hits = []
    seen = set()
    cur = pending_h
    while cur and cur not in seen and len(hits) < 80:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = FOCUS.get(vt - base)
        if name:
            hits.append({"source": "pending", **decode_assign(b, base, cur, name)})
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
                hits.append(
                    {"source": f"stage[{i}]", **decode_assign(b, base, ptr, name)}
                )
    return hits, counters


def heap_edge_assign(b, base, mb_limit=HEAP_MB, max_hits=HEAP_MAX_HITS):
    """Bounded RO writable-heap scan for Assign/Unassign VT needles."""
    needles = {name: struct.pack("<Q", base + vt) for vt, name in FOCUS.items()}
    found, scanned = [], 0
    try:
        from mem import Proc

        src = Proc(find_pid("hoi4.exe") or find_pid())
        if not hasattr(src, "regions"):
            return {"ok": False, "error": "no regions", "found": [], "scanned_mb": 0}
        for m in src.regions(writable=True, min_size=0x1000):
            start_m, end_m = m["start"], m["end"]
            if base <= start_m < base + 0x4000000:
                continue
            pos = start_m
            while pos < end_m and scanned < (mb_limit << 20) and len(found) < max_hits:
                n = min(1 << 20, end_m - pos)
                data = None
                if hasattr(src, "try_read"):
                    data = src.try_read(pos, n)
                if data is None:
                    try:
                        data = src.read(pos, n)
                    except Exception:
                        data = None
                scanned += n
                if data:
                    for name, needle in needles.items():
                        j = 0
                        while j < len(data) and len(found) < max_hits:
                            k = data.find(needle, j)
                            if k < 0:
                                break
                            addr = pos + k
                            try:
                                found.append(
                                    {
                                        "source": "heap_edge",
                                        **decode_assign(b, base, addr, name),
                                    }
                                )
                            except Exception as e:
                                found.append(
                                    {
                                        "source": "heap_edge",
                                        "addr": hex(addr),
                                        "name": name,
                                        "error": str(e),
                                    }
                                )
                            j = k + 8
                pos += n
            if len(found) >= max_hits:
                break
        return {
            "ok": True,
            "found": found,
            "scanned_mb": round(scanned / (1 << 20), 2),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "found": [], "scanned_mb": 0}


def read_cpdx_ptrs(b, base, arr_addr, max_n=32):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
    except Exception:
        return None
    if not data or size <= 0 or size > 4096:
        return None
    if base <= data < base + 0x4000000:
        return {"size": size, "in_image_sentinel": True, "ptrs": []}
    blob = try_read(b, data, min(size, max_n) * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    ptrs = [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(min(size, max_n))]
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs, "data": hex(data)}


def resolve_og_inst(b, base, oi):
    if not oi:
        return {"oi": oi, "ok": False, "note": "oi_zero_or_missing"}
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception as e:
        return {"oi": oi, "ok": False, "note": f"resolve_err:{e}"}
    if not hdr:
        return {"oi": oi, "ok": False, "note": "resolve_null"}
    og = hdr + 0x10
    vt = try_u64(b, og)
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 8)
    inst = arr98["ptrs"][0] if arr98 and arr98.get("ptrs") else None
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 32)
    return {
        "oi": oi,
        "ok": True,
        "hdr": hex(hdr),
        "og": hex(og),
        "og_vt_rva": hex(vt - base) if vt else None,
        "inst": hex(inst) if inst else None,
        "arr50_size": (arr50 or {}).get("size"),
        "arr50_ptrs": [hex(p) for p in ((arr50 or {}).get("ptrs") or [])],
    }


def army_resolve(b, base, ix):
    try:
        obj = resolve_handle(b, HANDLE_TYPE_ARMY, ix, base)
    except Exception:
        obj = None
    if not obj:
        return {"index": ix, "ok": False}
    vt = try_u64(b, obj)
    mi = try_u64(b, obj + CA_MI_OFF)
    return {
        "index": ix,
        "ok": True,
        "primary": hex(obj),
        "vt_rva": hex(vt - base) if vt else None,
        "mi_b8": hex(obj + CA_MI_OFF),
        "mi_b8_vt_rva": hex(mi - base) if mi else None,
        "mi_b8_ok": bool(mi) and (mi - base) == CA_MI_B8,
        "country_tag": try_u32(b, obj + CA_TAG),
        "province_id": try_u32(b, obj + CA_PROV),
    }


def cross_units_og50(b, base, units, oginfo):
    if not oginfo.get("ok"):
        return {"checked": 0, "in_og50": 0, "rows": []}
    arr50 = set(int(p, 16) for p in (oginfo.get("arr50_ptrs") or []))
    rows = []
    in_n = 0
    for u in units:
        if u.get("type") != HANDLE_TYPE_ARMY:
            continue
        ar = army_resolve(b, base, u["index"])
        mi = int(ar["mi_b8"], 16) if ar.get("mi_b8") else None
        hit = bool(mi) and mi in arr50
        if hit:
            in_n += 1
        rows.append({**ar, "in_og50": hit, "unit_type": u["type"]})
    return {"checked": len(rows), "in_og50": in_n, "rows": rows}


def catalog_polish_b(b, base):
    ok = fail = 0
    ita_in = 0
    samples = []
    oi_with_members = 0
    tag = player_tag(b, base)
    for oi in range(1, 128):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        if not hdr:
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
        if not arr50 or arr50.get("in_image_sentinel") or not arr50.get("ptrs"):
            continue
        oi_with_members += 1
        for p in arr50["ptrs"]:
            if not p:
                continue
            primary = p - CA_MI_OFF
            vt = try_u64(b, primary)
            if vt and (vt - base) == CA_VT_RVA:
                ok += 1
                mi_vt = try_u64(b, p)
                atag = try_u32(b, primary + CA_TAG)
                if atag == tag:
                    ita_in += 1
                if len(samples) < 8:
                    samples.append(
                        {
                            "oi": oi,
                            "elem": hex(p),
                            "primary": hex(primary),
                            "elem_vt": hex(mi_vt - base) if mi_vt else None,
                            "tag": atag,
                        }
                    )
            else:
                fail += 1
    return {
        "proxy": "OG+0x50[i] == CArmy+0xB8 (VT 0x29d6fb8)",
        "walkback_ok": ok,
        "walkback_fail": fail,
        "oi_with_members_1_127": oi_with_members,
        "ita_tag_members_in_sample_ogs": ita_in,
        "samples": samples,
        "deltas_vs_2gq": [
            "oi scan 1..127 (was 1..95)",
            "A denser: clock nudge + heap-edge Assign corner",
            "B reaffirms 2gp/2gq MI identity only — no new field name",
        ],
        "demangled_name": "STUBBED",
    }


def ingest_hit(h, assigns, unassigns, nonzero_hits, b, base, t0, seen):
    name = h.get("name") or "?"
    addr = h.get("addr")
    key = (name, addr, h.get("source"))
    if key in seen:
        return
    seen.add(key)
    if name == "COrderAssignCommand":
        assigns.append(h)
        oi = h.get("order_index") or 0
        if oi != 0 and (h.get("units_size") or 0) > 0:
            oginfo = resolve_og_inst(b, base, oi)
            cross = cross_units_og50(b, base, h.get("units") or [], oginfo)
            nonzero_hits.append(
                {
                    "capture": h,
                    "og": oginfo,
                    "units_og50_cross": cross,
                    "t": round(time.time() - t0, 3),
                }
            )
    elif name == "COrderUnassignCommand":
        unassigns.append(h)
        oi = h.get("order_index") or 0
        if oi != 0:
            oginfo = resolve_og_inst(b, base, oi)
            cross = cross_units_og50(b, base, h.get("units") or [], oginfo)
            nonzero_hits.append(
                {
                    "capture": h,
                    "og": oginfo,
                    "units_og50_cross": cross,
                    "t": round(time.time() - t0, 3),
                }
            )


def main():
    assert allow_post() is False
    scenario = "ITA@1x denser Assign oi≠0 (clock nudge + heap edge; no Post)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gr",
            "result": "NO_LIVE_PROCESS",
            "allow_post": False,
            "next_shortest_blocker": "NON-Post: restore live; still NO ALLOW_POST",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    b = Backend()
    base = b.image_base
    tag = player_tag(b, base)
    meta0 = live_meta(b, base, pid, tag, scenario)

    # Brief 1x clock advance: wait for hours tick; never write speed.
    nudge = {"waited_s": 0.0, "hours_start": meta0["hours"], "hours_end": meta0["hours"], "ticked": False}
    tn0 = time.time()
    while time.time() - tn0 < CLOCK_NUDGE_S:
        m = live_meta(b, base, pid, tag, scenario)
        if m["hours"] > meta0["hours"]:
            nudge["hours_end"] = m["hours"]
            nudge["ticked"] = True
            nudge["waited_s"] = round(time.time() - tn0, 2)
            break
        time.sleep(0.5)
    else:
        nudge["waited_s"] = round(time.time() - tn0, 2)
        nudge["hours_end"] = live_meta(b, base, pid, tag, scenario)["hours"]

    meta_pre = live_meta(b, base, pid, tag, scenario)
    t0 = time.time()
    polls = 0
    sight = Counter()
    assigns, unassigns = [], []
    seen = set()
    last_counters = None
    nonzero_hits = []
    heap_scans = 0
    heap_results = []
    last_heap_t = 0.0
    last_exec = meta_pre.get("exec")

    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = walk_pending_stage(b, base)
        for h in hits:
            sight[h.get("name") or "?"] += 1
            ingest_hit(h, assigns, unassigns, nonzero_hits, b, base, t0, seen)

        now = time.time()
        exec_now = (last_counters or {}).get("exec")
        exec_moved = exec_now is not None and last_exec is not None and exec_now != last_exec
        if exec_now is not None:
            last_exec = exec_now
        due = (now - last_heap_t) >= HEAP_EVERY_S
        if heap_scans < HEAP_SCANS_CAP and (exec_moved or due or heap_scans == 0):
            hr = heap_edge_assign(b, base)
            heap_scans += 1
            last_heap_t = now
            heap_results.append(
                {
                    "poll": polls,
                    "t": round(now - t0, 2),
                    "ok": hr.get("ok"),
                    "scanned_mb": hr.get("scanned_mb"),
                    "n_found": len(hr.get("found") or []),
                    "error": hr.get("error"),
                }
            )
            for h in hr.get("found") or []:
                if h.get("name"):
                    sight[h["name"] + ":heap"] += 1
                    ingest_hit(h, assigns, unassigns, nonzero_hits, b, base, t0, seen)

        if len(nonzero_hits) >= 2:
            break
        time.sleep(POLL_SLEEP)

    observe_s = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, pid, tag, scenario)
    polish = catalog_polish_b(b, base)

    oi0_only = (
        assigns
        and all((a.get("order_index") or 0) == 0 for a in assigns)
        and not nonzero_hits
    )
    quiet = not assigns and not unassigns

    confirmed = [
        h
        for h in nonzero_hits
        if h.get("og", {}).get("ok")
        and (h.get("units_og50_cross", {}).get("checked", 0) > 0)
    ]
    confirmed_in50 = [
        h for h in confirmed if h.get("units_og50_cross", {}).get("in_og50", 0) > 0
    ]

    if confirmed_in50:
        result = "ASSIGN_OI_NONZERO_UNITS_IN_OG50_HIT"
    elif confirmed:
        result = "ASSIGN_OI_NONZERO_OG_RESOLVED_UNITS_NOT_YET_IN_50"
    elif nonzero_hits:
        result = "ASSIGN_OI_NONZERO_SIGHT_OG_RESOLVE_PARTIAL"
    elif oi0_only:
        result = "ASSIGN_OI_ZERO_ONLY_OG50_CATALOG_POLISH"
    elif quiet:
        result = "ASSIGN_QUIET_DENSE_OG50_CATALOG_POLISH"
    else:
        result = "ASSIGN_SIGHT_NO_NONZERO_OI"

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk",
        f"clock_nudge waited={nudge['waited_s']}s hours {nudge['hours_start']}→{nudge['hours_end']} ticked={nudge['ticked']}",
        f"Assign observe {observe_s}s polls={polls} Assign={len(assigns)} Unassign={len(unassigns)} heap_scans={heap_scans}",
        f"nonzero_oi_hits={len(nonzero_hits)} confirmed_og={len(confirmed)} in_og50={len(confirmed_in50)}",
        f"B polish walkback {polish['walkback_ok']}/{polish['walkback_ok']+polish['walkback_fail']} "
        f"oi_with_members={polish['oi_with_members_1_127']} ita≈{polish['ita_tag_members_in_sample_ogs']}",
    ]
    stubbed = [
        "demangled OG+0x50 / MI field name",
        "named movement_dest",
        "ring_embed",
        "2fb/2gk recipe execute",
        "ALLOW_POST / CLAUSEWITZ_ALLOW_POST",
        "tool-gate open",
        "CMove midflight hex",
        "Post inject",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "speed write (never; nudge is wait-only @1x)",
    ]
    if not confirmed_in50:
        stubbed.append(
            "Assign units↔OI with order_index≠0 proven in OG+0x50 this window"
        )

    if confirmed_in50:
        next_b = (
            "NON-Post: Assign oi≠0 units∈OG+0x50 HIT — membership via 2gp MI proxy; "
            "human midflight CMove / SAFE Post still gate ring_embed; push when GitHub "
            "reachable; still NO ALLOW_POST"
        )
    elif confirmed:
        next_b = (
            "NON-Post: oi≠0 OG resolved but units not yet in +0x50 — brief re-sight OR "
            "human midflight CMove / SAFE Post; still NO ALLOW_POST"
        )
    else:
        next_b = (
            "NON-Post: Assign oi≠0 still unconfirmed after dense churn — human midflight "
            "CMove hex / SAFE Post for ring_embed OR later plan-dense window; push when "
            "GitHub reachable; still NO ALLOW_POST"
        )

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gr",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "live_start": meta0,
        "live_pre_observe": meta_pre,
        "live_end": meta1,
        "clock_nudge": nudge,
        "observe_s": observe_s,
        "polls": polls,
        "sight_counts": dict(sight),
        "assign_captures": len(assigns),
        "unassign_captures": len(unassigns),
        "assigns_sample": assigns[:8],
        "unassigns_sample": unassigns[:4],
        "nonzero_oi_hits": nonzero_hits[:8],
        "oi0_only": oi0_only,
        "heap_scans": heap_scans,
        "heap_results": heap_results,
        "catalog_polish_b": polish,
        "last_counters": last_counters,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "83ac9e8",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2gr",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "clock_nudge": nudge,
        "observe_s": observe_s,
        "polls": polls,
        "assign_captures": len(assigns),
        "unassign_captures": len(unassigns),
        "nonzero_oi_hits": len(nonzero_hits),
        "confirmed_og": len(confirmed),
        "confirmed_in_og50": len(confirmed_in50),
        "heap_scans": heap_scans,
        "walkback_ok": polish["walkback_ok"],
        "walkback_fail": polish["walkback_fail"],
        "next_shortest_blocker": next_b,
        "sha_base": "83ac9e8",
        "semantics": (
            f"nudge hours {nudge['hours_start']}→{nudge['hours_end']}; "
            f"Assign oi≠0 hits={len(nonzero_hits)}; in_og50={len(confirmed_in50)}; "
            f"B walkback {polish['walkback_ok']}/{polish['walkback_ok']+polish['walkback_fail']}"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "result": result,
                "live": {
                    "pid": meta1["pid"],
                    "hours": meta1["hours"],
                    "ui_date": meta1["ui_date"],
                    "speed_policy": meta1["speed_policy"],
                    "country_tag_filter": tag,
                    "scenario": scenario,
                    "pending": meta1["pending"],
                    "stage_count": meta1["stage_count"],
                    "allow_post": False,
                },
                "clock_nudge": nudge,
                "observe_s": observe_s,
                "assign": len(assigns),
                "unassign": len(unassigns),
                "nonzero_oi": len(nonzero_hits),
                "in_og50": len(confirmed_in50),
                "heap_scans": heap_scans,
                "walkback": f"{polish['walkback_ok']}/{polish['walkback_ok']+polish['walkback_fail']}",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
