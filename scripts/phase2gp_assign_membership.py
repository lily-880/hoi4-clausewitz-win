#!/usr/bin/env python3
"""Phase 2gp: Assign-stage membership sight ≤90s + OG+0x50↔CArmy MI cross (RO).

ONE RO slice. No Post / no ALLOW_POST / no 2fb|2gk execute / never 5x.
A) Bounded Assign/Unassign pending/stage observe (≤90s, early-rich stop).
B) If A quiet (or always as membership proxy): deepen OG+0x50 MI elems
   ↔ live CArmy primary/MI-subobject pointer cross.
Document hits or honest empty.
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

import army_subjects
import cmd_layout
import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gp_assign_membership.json"
SUMMARY = ROOT / "reports" / "phase2gp_summary.json"
DOC = ROOT / "docs" / "PHASE2GP_ASSIGN_MEMBERSHIP.md"

OBSERVE_S = 90.0
POLL_SLEEP = 0.05
INDEX_LO, INDEX_HI = 400, 1600
GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_VT = 0x29D6FB8  # WINDOWS_OFFSETS CArmy MI
CA_MI_OTHER = (0x29D6F48, 0x29D7000)
WIDE_OIS = tuple(range(1, 96))
# MI subobject deltas to probe within CArmy body
MI_DELTAS = (
    0, 8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58,
    0x60, 0x68, 0x70, 0x78, 0x80, 0x88, 0x90, 0x98, 0xA0, 0xA8, 0xB0,
    0xB8, 0xC0,  # +0xB8 = VT 0x29d6fb8 (OG+0x50 elem class)
    0x100, 0x110, 0x120, 0x128, 0x130, 0x138, 0x140, 0x148, 0x150,
    0x158, 0x160, 0x180, 0x1A0, 0x1C0, 0x1E0, 0x1F0, 0x200, 0x210,
    0x220, 0x228, 0x230, 0x238, 0x240, 0x248, 0x250, 0x280, 0x2A0,
    0x2B0, 0x2C0, 0x300,
)

ASSIGN = cmd_layout.ORDERS["COrderAssignCommand"]
UNASSIGN = cmd_layout.ORDERS["COrderUnassignCommand"]
ASSIGN_VT = ASSIGN["vt"]
UNASSIGN_VT = UNASSIGN["vt"]
FOCUS = {
    ASSIGN_VT: "COrderAssignCommand",
    UNASSIGN_VT: "COrderUnassignCommand",
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
    f = ASSIGN["fields"] if name == "COrderAssignCommand" else UNASSIGN["fields"]
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
        "assign_to_minimum_order": try_u32(b, addr + 0x4C) if name == "COrderAssignCommand" else None,
        "fields_note": f.get("note") if isinstance(f, dict) else None,
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
                hits.append({"source": f"stage[{i}]", **decode_assign(b, base, ptr, name)})
    return hits, counters


def read_cpdx_ptrs(b, base, arr_addr, max_n=32):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
        cap = i32(b, arr_addr + 0x8)
    except Exception:
        return None
    if not data or size < 0 or size > 4096 or cap < size:
        return {"plausible": False, "size": size, "cap": cap, "data": hex(data) if data else None, "ptrs": []}
    # sentinel: data in image
    in_img = base <= data < base + 0x4000000
    ptrs = []
    if not in_img and 0 < size <= max_n:
        blob = try_read(b, data, size * 8)
        if blob:
            for j in range(size):
                ptrs.append(struct.unpack_from("<Q", blob, j * 8)[0])
    return {
        "plausible": True,
        "size": size,
        "cap": cap,
        "data": hex(data),
        "in_image_sentinel": in_img,
        "ptrs": ptrs,
    }


def resolve_og(b, base, oi):
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        return None
    if not hdr:
        return None
    # conventional body = hdr+0x10 for type-0x35
    og = hdr + 0x10
    vt = try_u64(b, og)
    if vt is None:
        return None
    return {"oi": oi, "hdr": hdr, "og": og, "vt_rva": hex(vt - base)}


def inst_from_og98(b, base, og):
    arr = read_cpdx_ptrs(b, base, og + 0x98, max_n=8)
    if not arr or not arr["ptrs"]:
        return None, arr
    return arr["ptrs"][0], arr


def build_army_mi_map(b, base, armies):
    """For each live CArmy primary, find MI subobject addrs (VT match)."""
    mi_to_army = {}  # mi_addr -> army row
    army_mis = []
    for a in armies:
        primary = a["army"]
        found = []
        for d in MI_DELTAS:
            cand = primary + d
            vt = try_u64(b, cand)
            if vt is None:
                continue
            rva = vt - base
            if rva in (CA_MI_VT, *CA_MI_OTHER):
                found.append({"delta": d, "mi": cand, "vt_rva": hex(rva)})
                mi_to_army[cand] = {
                    "index": a["index"],
                    "primary": primary,
                    "delta": d,
                    "vt_rva": hex(rva),
                    "province_id": a.get("province_id"),
                }
        army_mis.append({
            "index": a["index"],
            "primary": hex(primary),
            "mi_hits": [{"delta": x["delta"], "mi": hex(x["mi"]), "vt_rva": x["vt_rva"]} for x in found],
        })
    return mi_to_army, army_mis


def cross_og50_membership(b, base, armies, mi_to_army):
    """Preferred B: OG+0x50 elem ptrs ↔ live CArmy MI / primary / embedded ptr."""
    primary_set = {a["army"]: a for a in armies}
    primary_addrs = set(primary_set.keys())
    rows = []
    total_elems = 0
    mi_match = 0
    primary_direct = 0
    embedded_army_ptr = 0
    trusted_links = []

    for oi in WIDE_OIS:
        oginfo = resolve_og(b, base, oi)
        if not oginfo:
            continue
        og = oginfo["og"]
        inst, arr98 = inst_from_og98(b, base, og)
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, max_n=24)
        if not arr50 or arr50.get("in_image_sentinel") or arr50.get("size", 0) <= 0:
            continue
        elems = []
        for p in arr50["ptrs"]:
            if not p or p < 0x10000:
                continue
            total_elems += 1
            vt = try_u64(b, p)
            vt_rva = hex(vt - base) if vt else None
            rec = {
                "ptr": hex(p),
                "vt_rva": vt_rva,
                "mi_match": None,
                "primary_direct": False,
                "embedded_army": None,
                "plus08_is_og": False,
                "plus20_is_inst": False,
            }
            raw = try_read(b, p, 0x80) or b""
            if len(raw) >= 0x28:
                q8 = struct.unpack_from("<Q", raw, 0x8)[0]
                q20 = struct.unpack_from("<Q", raw, 0x20)[0]
                rec["plus08_is_og"] = q8 == og
                rec["plus20_is_inst"] = bool(inst) and q20 == inst
            # direct primary?
            if p in primary_addrs:
                primary_direct += 1
                rec["primary_direct"] = True
                a = primary_set[p]
                link = {
                    "kind": "primary_direct",
                    "oi": oi,
                    "army_index": a["index"],
                    "elem": hex(p),
                    "trusted": True,
                }
                trusted_links.append(link)
                rec["mi_match"] = {"index": a["index"], "delta": 0, "via": "primary_eq"}
            # MI subobject match
            elif p in mi_to_army:
                mi_match += 1
                m = mi_to_army[p]
                rec["mi_match"] = {
                    "index": m["index"],
                    "delta": m["delta"],
                    "primary": hex(m["primary"]),
                    "via": "mi_vt_at_army_plus_delta",
                }
                link = {
                    "kind": "mi_subobject",
                    "oi": oi,
                    "army_index": m["index"],
                    "elem": hex(p),
                    "delta": m["delta"],
                    "trusted": True,
                }
                trusted_links.append(link)
            else:
                # scan elem blob for live army primary ptr
                if len(raw) >= 8:
                    for off in range(0, min(len(raw), 0x78), 8):
                        q = struct.unpack_from("<Q", raw, off)[0]
                        if q in primary_addrs:
                            embedded_army_ptr += 1
                            a = primary_set[q]
                            rec["embedded_army"] = {
                                "off": hex(off),
                                "index": a["index"],
                                "primary": hex(q),
                            }
                            trusted_links.append({
                                "kind": "embedded_primary_ptr",
                                "oi": oi,
                                "army_index": a["index"],
                                "elem": hex(p),
                                "off": hex(off),
                                "trusted": True,
                            })
                            break
            elems.append(rec)
        if elems:
            rows.append({
                "oi": oi,
                "og": hex(og),
                "inst": hex(inst) if inst else None,
                "arr50_size": arr50["size"],
                "elems": elems,
                "mi_matched": sum(1 for e in elems if e.get("mi_match")),
                "embedded": sum(1 for e in elems if e.get("embedded_army")),
            })

    # dedupe trusted by (kind, oi, army_index)
    uniq = {}
    for t in trusted_links:
        key = (t["kind"], t["oi"], t["army_index"])
        uniq[key] = t
    trusted_links = list(uniq.values())

    return {
        "ogs_with_50": len(rows),
        "total_elems": total_elems,
        "mi_match_count": mi_match,
        "primary_direct_count": primary_direct,
        "embedded_army_ptr_count": embedded_army_ptr,
        "trusted_link_count": len(trusted_links),
        "trusted_links_sample": trusted_links[:40],
        "oi_rows_sample": rows[:16],
        "army_with_mi_vt": sum(1 for a in [] ),  # filled by caller
    }, rows


def membership_from_assign(b, base, assigns, mi_to_army, armies):
    """If Assign captured units, resolve army↔OI beyond oi_u32 noise."""
    primary_by_ix = {a["index"]: a for a in armies}
    links = []
    for a in assigns:
        oi = a.get("order_index")
        for u in a.get("units") or []:
            if u.get("type") != HANDLE_TYPE_ARMY:
                continue
            ix = u.get("index")
            row = primary_by_ix.get(ix)
            links.append({
                "source": "assign_units",
                "oi": oi,
                "army_index": ix,
                "army_resolved": bool(row),
                "assign_addr": a.get("addr"),
                "trusted": bool(row) and oi is not None,
            })
    return links


def main():
    assert allow_post() is False
    scenario = "ITA@1x Assign membership ≤90s + OG+0x50↔CArmy MI cross (no Post)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gp",
            "result": "NO_LIVE_PROCESS",
            "allow_post": False,
            "next_shortest_blocker": "NON-Post: restore live then Assign/membership; still NO ALLOW_POST",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    b = Backend()
    base = b.image_base
    tag = player_tag(b, base)
    meta0 = live_meta(b, base, pid, tag, scenario)

    # --- Preferred A: bounded Assign observe ---
    t0 = time.time()
    polls = 0
    sight = Counter()
    assigns, unassigns = [], []
    seen_addrs = set()
    last_counters = None
    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = walk_pending_stage(b, base)
        for h in hits:
            name = h.get("name") or "?"
            sight[name] += 1
            addr = h.get("addr")
            if name == "COrderAssignCommand" and addr not in seen_addrs:
                seen_addrs.add(addr)
                assigns.append(h)
            elif name == "COrderUnassignCommand" and addr not in seen_addrs:
                seen_addrs.add(addr)
                unassigns.append(h)
        # early-rich stop: enough Assign with units
        rich = [a for a in assigns if (a.get("units_size") or 0) > 0]
        if len(rich) >= 3:
            break
        time.sleep(POLL_SLEEP)
    observe_s = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, pid, tag, scenario)

    # --- Preferred B: OG+0x50 ↔ live CArmy MI cross ---
    armies = army_subjects.iter_armies_by_index(b, base, INDEX_LO, INDEX_HI, country_tag=tag)
    mi_to_army, army_mis = build_army_mi_map(b, base, armies)
    armies_with_mi = sum(1 for a in army_mis if a["mi_hits"])
    cross, oi_rows = cross_og50_membership(b, base, armies, mi_to_army)
    cross["army_with_mi_vt"] = armies_with_mi
    cross["live_armies"] = len(armies)
    cross["mi_map_size"] = len(mi_to_army)
    # sample which deltas appear on live armies
    delta_counts = Counter()
    for a in army_mis:
        for h in a["mi_hits"]:
            delta_counts[h["delta"]] += 1
    cross["mi_delta_histogram"] = {hex(k): v for k, v in sorted(delta_counts.items())}
    cross["army_mi_sample"] = army_mis[:12]

    assign_links = membership_from_assign(b, base, assigns, mi_to_army, armies)

    # classify result
    a_quiet = len(assigns) == 0 and len(unassigns) == 0
    trusted_n = cross["trusted_link_count"]
    if trusted_n > 0 and a_quiet:
        result = "OG50_CARMY_MI_MEMBERSHIP_HIT"
    elif trusted_n > 0 and not a_quiet:
        result = "ASSIGN_SIGHT_PLUS_OG50_MI_HIT"
    elif not a_quiet and any(x.get("trusted") for x in assign_links):
        result = "ASSIGN_UNITS_MEMBERSHIP_HIT"
    elif not a_quiet:
        result = "ASSIGN_SIGHT_NO_TRUSTED_MEMBERSHIP"
    elif trusted_n == 0:
        result = "ASSIGN_QUIET_OG50_MEMBERSHIP_HONEST_EMPTY"
    else:
        result = "MEMBERSHIP_PROBE_DONE"

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk",
        f"Assign observe {observe_s}s polls={polls} Assign={len(assigns)} Unassign={len(unassigns)}",
        f"live ITA armies={len(armies)} with_MI_vt={armies_with_mi} mi_map={len(mi_to_army)}",
        f"OG+0x50 ogs={cross['ogs_with_50']} elems={cross['total_elems']} "
        f"mi_match={cross['mi_match_count']} primary_direct={cross['primary_direct_count']} "
        f"embedded={cross['embedded_army_ptr_count']} trusted={trusted_n}",
    ]
    stubbed = [
        "named demangled movement_dest",
        "proven army↔OI membership field beyond MI/Assign proxy" if trusted_n == 0 else
        "demangled field name for OG+0x50 / MI membership (proxy only)",
        "ring_embed",
        "2fb/2gk recipe execute",
        "ALLOW_POST / CLAUSEWITZ_ALLOW_POST",
        "tool-gate open",
        "CMove midflight hex",
        "Post inject",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
    ]
    if a_quiet:
        stubbed.append("live midflight Assign/Unassign hex (quiet this window)")

    if trusted_n > 0:
        next_b = (
            "NON-Post: OG+0x50↔CArmy MI membership proxy HIT — deepen Instance-side "
            "confirmation / demangle MI VT OR human midflight CMove / SAFE Post for ring_embed; "
            "push when GitHub reachable; still NO ALLOW_POST"
        )
    elif a_quiet:
        next_b = (
            "NON-Post: Assign quiet + OG+0x50 membership HONEST_EMPTY this window — "
            "human midflight CMove hex / SAFE Post for ring_embed OR denser plan-churn sight; "
            "push when GitHub reachable; still NO ALLOW_POST"
        )
    else:
        next_b = (
            "NON-Post: Assign sight without trusted membership — decode units↔OI further OR "
            "human midflight CMove / SAFE Post; still NO ALLOW_POST"
        )

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gp",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "live_start": meta0,
        "live_end": meta1,
        "observe_s": observe_s,
        "polls": polls,
        "sight_counts": dict(sight),
        "assign_captures": len(assigns),
        "unassign_captures": len(unassigns),
        "assigns_sample": assigns[:8],
        "unassigns_sample": unassigns[:4],
        "assign_membership_links": assign_links[:24],
        "last_counters": last_counters,
        "og50_cross": cross,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "b3844b3",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2gp",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "observe_s": observe_s,
        "polls": polls,
        "assign_captures": len(assigns),
        "unassign_captures": len(unassigns),
        "trusted_og50_links": trusted_n,
        "mi_match_count": cross["mi_match_count"],
        "ogs_with_50": cross["ogs_with_50"],
        "live_armies": len(armies),
        "army_with_mi_vt": armies_with_mi,
        "next_shortest_blocker": next_b,
        "sha_base": "b3844b3",
        "semantics": (
            f"Assign={'quiet' if a_quiet else 'sight'}; "
            f"OG+0x50↔CArmy MI trusted_links={trusted_n}"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # compact stdout
    print(json.dumps({
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
        "observe_s": observe_s,
        "assign": len(assigns),
        "unassign": len(unassigns),
        "trusted_og50": trusted_n,
        "mi_match": cross["mi_match_count"],
        "ogs50": cross["ogs_with_50"],
        "armies": len(armies),
        "army_mi": armies_with_mi,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
