#!/usr/bin/env python3
"""Phase 2gf: Assign/Unassign edge deepen — midflight hex + units packing + oi↔0x35.
No Post. Never 5x. allow_post False. ≤90s. Capstone not re-run.
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
from handle import resolve_handle, HANDLE_TYPE_ARMY, HANDLE_TYPE_TABLE

assert allow_post() is False

OBSERVE_S = 90.0
INTERVAL_S = 0.07
TYPE_OG = 0x35
HANDLE_STRIDE = 8

ASSIGN = cmd_layout.ORDERS["COrderAssignCommand"]
UNASSIGN = cmd_layout.ORDERS["COrderUnassignCommand"]
EXECUTE = cmd_layout.ORDERS["COrderExecuteCommand"]
NF = cmd_layout.ORDERS["COrderNewFallbackCommand"]

ASSIGN_VT = ASSIGN["vt"]
UNASSIGN_VT = UNASSIGN["vt"]
EXECUTE_VT = EXECUTE["vt"]
NF_VT = NF["vt"]
RF_VT = 0x2A84D38

FOCUS = {
    ASSIGN_VT: "COrderAssignCommand",
    UNASSIGN_VT: "COrderUnassignCommand",
    EXECUTE_VT: "COrderExecuteCommand",
    NF_VT: "COrderNewFallbackCommand",
    RF_VT: "COrderReplaceFallbackCommands",
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
        "cmdline_expect": "-gdpr-compliant -start_tag=ETH -start_speed=1",
        "gs": hex(gs),
    }


def decode_units(b, data_ptr: int, size: int) -> dict:
    size = max(0, min(size, 32))
    raw = try_read(b, data_ptr, size * HANDLE_STRIDE) or b""
    elems = []
    for i in range(size):
        off = i * HANDLE_STRIDE
        if off + 8 > len(raw):
            break
        typ, ix = struct.unpack_from("<II", raw, off)
        ptr = None
        army_echo = None
        if typ and ix:
            try:
                ptr = resolve_handle(b, typ, ix, None)  # base filled below by caller? need base
            except TypeError:
                ptr = None
        elems.append({
            "i": i,
            "type": typ,
            "type_hex": hex(typ),
            "index": ix,
            "note": "HANDLE_TYPE_ARMY" if typ == HANDLE_TYPE_ARMY else None,
            "as_list": [typ, ix],
        })
    return {
        "element_layout": "{u32 type, u32 index}",
        "stride": HANDLE_STRIDE,
        "size": size,
        "elements": elems,
        "type_histogram": dict(Counter(e["type"] for e in elems)),
    }


def decode_units_with_base(b, base, data_ptr: int, size: int) -> dict:
    size = max(0, min(int(size), 32))
    if data_ptr < 0x10000 or size <= 0:
        return {"size": size, "data": hex(data_ptr), "elements": [], "type_histogram": {}}
    raw = try_read(b, data_ptr, size * HANDLE_STRIDE) or b""
    elems = []
    for i in range(size):
        off = i * HANDLE_STRIDE
        if off + 8 > len(raw):
            break
        typ, ix = struct.unpack_from("<II", raw, off)
        resolved = None
        army18 = None
        if typ and ix:
            try:
                resolved = resolve_handle(b, typ, ix, base)
            except Exception:
                resolved = None
            if typ == HANDLE_TYPE_ARMY and resolved:
                try:
                    army18 = u32(b, resolved + 0x18)
                except Exception:
                    army18 = None
        elems.append({
            "i": i,
            "type": typ,
            "type_hex": hex(typ),
            "index": ix,
            "note": "HANDLE_TYPE_ARMY" if typ == HANDLE_TYPE_ARMY else None,
            "resolved": hex(resolved) if resolved else None,
            "carmy_plus18_echo": army18,
            "echo_matches_index": (army18 == ix) if army18 is not None else None,
        })
    return {
        "element_layout": "{u32 type, u32 index}",
        "stride": HANDLE_STRIDE,
        "size": size,
        "data": hex(data_ptr),
        "elements": elems,
        "type_histogram": dict(Counter(e["type"] for e in elems)),
        "army_resolve_ok": sum(1 for e in elems if e.get("note") == "HANDLE_TYPE_ARMY" and e.get("resolved")),
    }


def decode_assign(b, base, addr: int, name: str) -> dict:
    f = ASSIGN["fields"] if name == "COrderAssignCommand" else UNASSIGN["fields"]
    blob = try_read(b, addr, 0x58) or b""
    out = {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(struct.unpack_from("<Q", blob, 0)[0] - base) if len(blob) >= 8 else None,
        "hex": blob.hex(),
        "fields_decoded": {},
    }
    if len(blob) < 0x50:
        return out
    ud = f["units_data"]
    ucap = f["units_capacity"]
    ucnt = f["units_count"]
    data = struct.unpack_from("<Q", blob, ud)[0]
    cap = struct.unpack_from("<i", blob, ucap)[0]
    cnt = struct.unpack_from("<i", blob, ucnt)[0]
    out["fields_decoded"]["units"] = decode_units_with_base(b, base, data, cnt)
    out["fields_decoded"]["units"]["capacity"] = cap
    out["fields_decoded"]["units"]["count"] = cnt
    if name == "COrderAssignCommand":
        oi = struct.unpack_from("<I", blob, f["order_index"])[0]
        atm = struct.unpack_from("<B", blob, f["assign_to_minimum_order"])[0]
        out["fields_decoded"]["order_index"] = oi
        out["fields_decoded"]["assign_to_minimum_order"] = atm
        # oi ↔ type-0x35
        og_ptr = None
        try:
            og_ptr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            og_ptr = None
        out["fields_decoded"]["order_index_as_type35"] = {
            "order_index": oi,
            "resolve_ok": bool(og_ptr),
            "og_or_hdr": hex(og_ptr) if og_ptr else None,
            "note": "battle-plan slot as HANDLE type 0x35 (COrdersGroup) — 2ft/2fp class",
        }
        # soft u32@+0x40 sometimes seen as 0x35 in 2ft
        if len(blob) >= 0x44:
            u40 = struct.unpack_from("<I", blob, 0x40)[0]
            out["fields_decoded"]["u32_plus40"] = {"value": u40, "hex": hex(u40), "eq_0x35": u40 == TYPE_OG}
    else:
        ug = struct.unpack_from("<B", blob, f["unassign_group"])[0]
        uagi = struct.unpack_from("<B", blob, f["unassign_army_group_instances"])[0]
        out["fields_decoded"]["unassign_group"] = ug
        out["fields_decoded"]["unassign_army_group_instances"] = uagi
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
    while cur and cur not in seen and len(hits) < 80:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = FOCUS.get(vt - base)
        if name in ("COrderAssignCommand", "COrderUnassignCommand"):
            hits.append({"source": "pending", **decode_assign(b, base, cur, name)})
        elif name:
            hits.append({"source": "pending", "name": name, "addr": hex(cur), "vt_rva": hex(vt - base)})
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
            if name in ("COrderAssignCommand", "COrderUnassignCommand"):
                hits.append({"source": f"stage[{i}]", **decode_assign(b, base, ptr, name)})
            elif name:
                hits.append({"source": f"stage[{i}]", "name": name, "addr": hex(ptr), "vt_rva": hex(vt - base)})
    return hits, counters


def isvalid_polish():
    """Preferred B: catalog IsValid/Execute polish — no Capstone."""
    out = {}
    for name, o in [
        ("COrderAssignCommand", ASSIGN),
        ("COrderUnassignCommand", UNASSIGN),
        ("COrderExecuteCommand", EXECUTE),
        ("COrderNewFallbackCommand", NF),
    ]:
        out[name] = {
            "vt": hex(o["vt"]),
            "type_id": hex(o["type_id"]),
            "factory_idx": o["factory_idx"],
            "isvalid": hex(o["isvalid"]),
            "execute": hex(o["execute"]),
            "serialize": hex(o["serialize"]),
            "deserialize": hex(o["deserialize"]),
            "fields": o.get("fields"),
            "fields_note": o.get("fields_note"),
        }
    # ISVALID_PATHS NF gate only (already known)
    isp = getattr(cmd_layout, "ISVALID_PATHS", {}).get("COrderNewFallbackCommand") or {}
    out["COrderNewFallbackCommand"]["isvalid_calls_from_ISVALID_PATHS"] = isp.get("isvalid_calls")
    out["delta_note"] = (
        "no Capstone; documented Assign isvalid=0x18de900 execute=0x18d41b0 factory_idx=3350; "
        "Unassign isvalid=0x18e01d0 execute=0x18db050 factory_idx=3365; "
        "packing already 2fn/2fo (units CPdxArray@+0x28 size@+0x34 stride8 {type,index})"
    )
    return out


def main():
    assert allow_post() is False
    scenario = "ETH@1x Assign/Unassign edge deepen (no Post)"

    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gf",
            "allow_post": False,
            "result": "NO_LIVE_PROCESS",
            "isvalid_polish": isvalid_polish(),
            "next_shortest_blocker": "NON-Post: restore live then Assign observe; still NO ALLOW_POST",
        }
        (ROOT / "reports" / "phase2gf_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2)[:1200])
        return 1

    b = Backend()
    base = b.image_base
    meta0 = live_meta(b, base, scenario)

    try:
        reg35 = u64(b, base + HANDLE_TYPE_TABLE + TYPE_OG * 8)
    except Exception:
        reg35 = 0

    t0 = time.time()
    polls = 0
    sight = Counter()
    assigns = []
    unassigns = []
    other = Counter()
    last_counters = None
    seen_addrs = set()

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
            elif name not in ("COrderAssignCommand", "COrderUnassignCommand"):
                other[name] += 1
        # early stop on rich Assign with units
        rich = [
            a for a in assigns
            if (a.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
        ]
        if rich and len(assigns) >= 2:
            break
        time.sleep(INTERVAL_S)

    elapsed = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, scenario)
    polish = isvalid_polish()

    oi_ties = []
    for a in assigns:
        t = (a.get("fields_decoded") or {}).get("order_index_as_type35") or {}
        if t:
            oi_ties.append(t)
    army_ok = sum(
        (a.get("fields_decoded") or {}).get("units", {}).get("army_resolve_ok", 0)
        for a in assigns + unassigns
    )
    units_nonzero = sum(
        1 for a in assigns + unassigns
        if (a.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
    )
    oi_resolve_ok = sum(1 for t in oi_ties if t.get("resolve_ok"))

    if assigns and units_nonzero and oi_resolve_ok:
        result = "assign_edge_units_and_oi_type35_deepened"
        note = (
            f"Assign captures={len(assigns)} Unassign={len(unassigns)}; "
            f"units_nonzero={units_nonzero} army_resolve_ok_sum={army_ok}; "
            f"oi→0x35 resolve_ok={oi_resolve_ok}/{len(oi_ties)}"
        )
    elif assigns and units_nonzero:
        result = "assign_edge_units_packing_confirmed"
        note = (
            f"Assign={len(assigns)} Unassign={len(unassigns)} units_nonzero={units_nonzero} "
            f"army_resolve_ok_sum={army_ok}; oi→0x35 resolve_ok={oi_resolve_ok}/{len(oi_ties)}"
        )
    elif assigns or unassigns:
        result = "assign_unassign_hex_seen_thin_units"
        note = f"Assign={len(assigns)} Unassign={len(unassigns)} but units mostly empty this window"
    else:
        result = "assign_unassign_edge_empty"
        note = (
            f"ETH@1x hours {meta0['hours']}→{meta1['hours']} bounded {elapsed}s: "
            f"Assign/Unassign=0 on pending/stage; sight={dict(sight)}; "
            f"IsValid polish documented from catalog (no Capstone)"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        f"bounded Assign/Unassign observe {elapsed}s polls={polls}",
        "IsValid/Execute/factory_idx catalog polish (deltas only)",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
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
        "live midflight NewFallback hex",
    ]
    if not assigns and not unassigns:
        stubbed.append("live midflight Assign/Unassign hex (empty this window)")

    if result == "assign_unassign_edge_empty":
        next_blocker = (
            "NON-Post: Assign/Unassign quiet on ETH war-day pending/stage — "
            "ITA relaunch for denser plan churn OR deepen Execute order_index leaf; "
            "still NO ALLOW_POST"
        )
    elif "oi_type35" in result:
        next_blocker = (
            "NON-Post: walk live oi→OG internals (member/instance) from Assign edge OR "
            "Unassign group semantic; still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: more Assign ois for oi→0x35/OG member walk OR Unassign group decode; "
            "still NO ALLOW_POST"
        )

    detail = {
        "phase": "2gf",
        "allow_post": False,
        "live_start": meta0,
        "live_end": meta1,
        "handle_type_0x35_registry": hex(reg35),
        "observe": {
            "elapsed_s": elapsed,
            "polls": polls,
            "last_counters": last_counters,
            "sight_counts": dict(sight),
            "other_focus_counts": dict(other),
            "assigns": assigns[:10],
            "unassigns": unassigns[:8],
            "oi_type35_ties": oi_ties[:12],
            "units_nonzero_cmds": units_nonzero,
            "army_resolve_ok_sum": army_ok,
        },
        "isvalid_polish": polish,
    }
    summary = {
        "phase": "2gf",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta1,
        "observe_s": elapsed,
        "polls": polls,
        "assign_captures": len(assigns),
        "unassign_captures": len(unassigns),
        "units_nonzero_cmds": units_nonzero,
        "oi_type35_resolve_ok": oi_resolve_ok,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "isvalid_polish_delta": polish["delta_note"],
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "phase2gf_assign_unassign.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    (out / "phase2gf_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "elapsed_s": elapsed,
        "polls": polls,
        "assigns": len(assigns),
        "unassigns": len(unassigns),
        "units_nonzero": units_nonzero,
        "oi_type35_ok": oi_resolve_ok,
        "sight": dict(sight),
        "ui_start": meta0.get("ui_date"),
        "ui_end": meta1.get("ui_date"),
        "pid": meta1.get("pid"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
