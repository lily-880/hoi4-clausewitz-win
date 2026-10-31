#!/usr/bin/env python3
"""Phase 2gg: ITA relaunch @1x AI-on + bounded multi-leaf RO observe.
Assign/Unassign/NF/RF/Execute/Delete/CMove. No Post. Never 5x. ≤90s.
"""
from __future__ import annotations

import importlib.util
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
MAP_WAIT_S = 180.0
TYPE_OG = 0x35
HANDLE_STRIDE = 8

ASSIGN = cmd_layout.ORDERS["COrderAssignCommand"]
UNASSIGN = cmd_layout.ORDERS["COrderUnassignCommand"]
EXECUTE = cmd_layout.ORDERS["COrderExecuteCommand"]
DELETE = cmd_layout.ORDERS["COrderDeleteCommand"]
NF = cmd_layout.ORDERS["COrderNewFallbackCommand"]

ASSIGN_VT = ASSIGN["vt"]
UNASSIGN_VT = UNASSIGN["vt"]
EXECUTE_VT = EXECUTE["vt"]
DELETE_VT = DELETE["vt"]
NF_VT = NF["vt"]
RF_VT = 0x2A84D38
CMOVE_VT = 0x2A2C790  # offsets.py CMoveCommand_VT
# SupportAttack if present in REMAINING
SUPPORT_VT = None
for _k, _v in getattr(cmd_layout, "REMAINING_ARMY_ORDERS", {}).items():
    if "SupportAttack" in _k:
        SUPPORT_VT = _v.get("vt")
        break

FOCUS = {
    ASSIGN_VT: "COrderAssignCommand",
    UNASSIGN_VT: "COrderUnassignCommand",
    EXECUTE_VT: "COrderExecuteCommand",
    DELETE_VT: "COrderDeleteCommand",
    NF_VT: "COrderNewFallbackCommand",
    RF_VT: "COrderReplaceFallbackCommands",
    CMOVE_VT: "CMoveCommand",
}
if SUPPORT_VT:
    FOCUS[SUPPORT_VT] = "CSupportAttackCommand"


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


def load_fk():
    spec = importlib.util.spec_from_file_location(
        "phase2fk_war_dense_observe", ROOT / "scripts" / "phase2fk_war_dense_observe.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    size = max(0, min(int(size), 32))
    if data_ptr < 0x10000 or size <= 0:
        return {"size": size, "data": hex(data_ptr), "elements": [], "army_resolve_ok": 0}
    raw = try_read(b, data_ptr, size * HANDLE_STRIDE) or b""
    elems = []
    army_ok = 0
    for i in range(size):
        off_i = i * HANDLE_STRIDE
        if off_i + 8 > len(raw):
            break
        typ, ix = struct.unpack_from("<II", raw, off_i)
        resolved = None
        echo = None
        if typ and ix:
            try:
                resolved = resolve_handle(b, typ, ix, base)
            except Exception:
                resolved = None
            if typ == HANDLE_TYPE_ARMY and resolved:
                try:
                    echo = u32(b, resolved + 0x18)
                except Exception:
                    echo = None
                if resolved:
                    army_ok += 1
        elems.append({
            "i": i, "type": typ, "index": ix,
            "note": "HANDLE_TYPE_ARMY" if typ == HANDLE_TYPE_ARMY else None,
            "resolved": hex(resolved) if resolved else None,
            "carmy_plus18_echo": echo,
            "echo_matches_index": (echo == ix) if echo is not None else None,
        })
    return {
        "element_layout": "{u32 type, u32 index}",
        "stride": HANDLE_STRIDE,
        "size": size,
        "data": hex(data_ptr),
        "elements": elems,
        "army_resolve_ok": army_ok,
    }


def decode_assignish(b, base, addr, name):
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
    if name == "COrderAssignCommand":
        f = ASSIGN["fields"]
        data = struct.unpack_from("<Q", blob, f["units_data"])[0]
        cnt = struct.unpack_from("<i", blob, f["units_count"])[0]
        cap = struct.unpack_from("<i", blob, f["units_capacity"])[0]
        oi = struct.unpack_from("<I", blob, f["order_index"])[0]
        out["fields_decoded"]["units"] = decode_units(b, base, data, cnt)
        out["fields_decoded"]["units"]["capacity"] = cap
        out["fields_decoded"]["units"]["count"] = cnt
        out["fields_decoded"]["order_index"] = oi
        og = None
        try:
            og = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            og = None
        out["fields_decoded"]["order_index_as_type35"] = {
            "order_index": oi,
            "resolve_ok": bool(og),
            "og_or_hdr": hex(og) if og else None,
        }
    elif name == "COrderUnassignCommand":
        f = UNASSIGN["fields"]
        data = struct.unpack_from("<Q", blob, f["units_data"])[0]
        cnt = struct.unpack_from("<i", blob, f["units_count"])[0]
        out["fields_decoded"]["units"] = decode_units(b, base, data, cnt)
        out["fields_decoded"]["units"]["count"] = cnt
        out["fields_decoded"]["unassign_group"] = struct.unpack_from("<B", blob, f["unassign_group"])[0]
    elif name == "COrderExecuteCommand":
        f = EXECUTE["fields"]
        oi = struct.unpack_from("<I", blob, f["order_index"])[0]
        eo = struct.unpack_from("<B", blob, f["execute_order"])[0]
        allb = struct.unpack_from("<B", blob, f["all"])[0]
        og = None
        try:
            og = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            og = None
        out["fields_decoded"] = {
            "order_index": oi,
            "execute_order": eo,
            "all": allb,
            "order_index_as_type35": {
                "order_index": oi,
                "resolve_ok": bool(og),
                "og_or_hdr": hex(og) if og else None,
            },
        }
    elif name == "COrderDeleteCommand":
        oi = struct.unpack_from("<I", blob, DELETE["fields"]["order_index"])[0]
        out["fields_decoded"] = {"order_index": oi}
    elif name in ("COrderNewFallbackCommand", "COrderReplaceFallbackCommands"):
        nf_f = NF.get("fields") or {}
        sh = nf_f.get("subject_handle", 0x28)
        if len(blob) >= sh + 8:
            out["fields_decoded"]["subject_handle"] = [
                struct.unpack_from("<I", blob, sh)[0],
                struct.unpack_from("<I", blob, sh + 4)[0],
            ]
        psz = nf_f.get("provinces_size", 0x54)
        if len(blob) >= psz + 4:
            out["fields_decoded"]["provinces_size"] = struct.unpack_from("<i", blob, psz)[0]
    elif name == "CMoveCommand":
        # soft: action embed @+0x28 per offsets
        embed = struct.unpack_from("<Q", blob, 0x28)[0] if len(blob) >= 0x30 else 0
        out["fields_decoded"] = {
            "action_embed_plus28": hex(embed),
            "note": "CMove soft peek only — no Post; 2fb not executed",
        }
    return out


def walk(b, base):
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
            hits.append({"source": "pending", **decode_assignish(b, base, cur, name)})
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
                hits.append({"source": f"stage[{i}]", **decode_assignish(b, base, ptr, name)})
    return hits, counters


def execute_leaf_polish():
    """Preferred B fallback content — always attach; no Capstone."""
    return {
        "COrderExecuteCommand": {
            "vt": hex(EXECUTE_VT),
            "type_id": hex(EXECUTE["type_id"]),
            "factory_idx": EXECUTE["factory_idx"],
            "isvalid": hex(EXECUTE["isvalid"]),
            "execute": hex(EXECUTE["execute"]),
            "fields": EXECUTE["fields"],
            "fields_note": (
                "order_index@+0x30 (u32); execute_order@+0x34 (u8); all@+0x35 (u8). "
                "oi↔type-0x35 same class as Assign (2ft/2fp). posting DISABLED"
            ),
        },
        "COrderDeleteCommand": {
            "vt": hex(DELETE_VT),
            "factory_idx": DELETE["factory_idx"],
            "fields": DELETE["fields"],
            "note": "order_index@+0x30 only",
        },
        "delta_note": (
            "no Capstone; Execute leaf packing documented from cmd_layout (2fn/2ft maps); "
            "factory_idx=3352 isvalid=0x18def40 execute=0x18d6430"
        ),
    }


def main():
    assert allow_post() is False
    scenario = "ITA relaunch @1x AI-on multi-leaf observe (no Post)"

    fk = load_fk()
    relaunch = fk.relaunch_ita()
    if relaunch["rc"] != 0:
        summary = {
            "phase": "2gg",
            "allow_post": False,
            "result": "RELAUNCH_FAIL",
            "relaunch": relaunch,
            "execute_leaf_polish": execute_leaf_polish(),
            "next_shortest_blocker": "NON-Post: fix ITA relaunch then observe; still NO ALLOW_POST",
        }
        (ROOT / "reports" / "phase2gg_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({"result": "RELAUNCH_FAIL", "rc": relaunch["rc"]}, indent=2))
        return 1

    map_wait = fk.wait_map(MAP_WAIT_S)
    if not map_wait.get("ok"):
        summary = {
            "phase": "2gg",
            "allow_post": False,
            "result": "RELAUNCH_MAP_WAIT_FAIL",
            "relaunch": relaunch,
            "map_wait": map_wait,
            "execute_leaf_polish": execute_leaf_polish(),
            "next_shortest_blocker": "NON-Post: map-ready then observe; still NO ALLOW_POST",
        }
        (ROOT / "reports" / "phase2gg_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({"result": "RELAUNCH_MAP_WAIT_FAIL", "map_wait": map_wait}, indent=2))
        return 1

    b = Backend()
    base = b.image_base
    meta0 = live_meta(b, base, scenario)

    t0 = time.time()
    polls = 0
    sight = Counter()
    caps = {k: [] for k in [
        "COrderAssignCommand", "COrderUnassignCommand", "COrderExecuteCommand",
        "COrderDeleteCommand", "COrderNewFallbackCommand", "COrderReplaceFallbackCommands",
        "CMoveCommand", "CSupportAttackCommand",
    ]}
    seen = set()
    last_counters = None

    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = walk(b, base)
        for h in hits:
            name = h.get("name") or "?"
            sight[name] += 1
            addr = h.get("addr")
            key = (name, addr)
            if name in caps and key not in seen:
                seen.add(key)
                caps[name].append(h)
        # early stop on useful Assign or Execute with oi
        if len(caps["COrderAssignCommand"]) >= 2 or (
            caps["COrderAssignCommand"] and caps["COrderExecuteCommand"]
        ):
            break
        time.sleep(INTERVAL_S)

    elapsed = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, scenario)
    polish = execute_leaf_polish()

    n_assign = len(caps["COrderAssignCommand"])
    n_unassign = len(caps["COrderUnassignCommand"])
    n_exec = len(caps["COrderExecuteCommand"])
    n_nf = len(caps["COrderNewFallbackCommand"]) + len(caps["COrderReplaceFallbackCommands"])
    n_move = len(caps["CMoveCommand"]) + len(caps["CSupportAttackCommand"])
    n_del = len(caps["COrderDeleteCommand"])

    units_nz = sum(
        1 for a in caps["COrderAssignCommand"] + caps["COrderUnassignCommand"]
        if (a.get("fields_decoded") or {}).get("units", {}).get("size", 0) > 0
        or (a.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
    )
    oi_ok = sum(
        1 for a in caps["COrderAssignCommand"] + caps["COrderExecuteCommand"]
        if ((a.get("fields_decoded") or {}).get("order_index_as_type35") or {}).get("resolve_ok")
    )

    if n_assign and units_nz:
        result = "ita_assign_edge_hits"
        note = f"Assign={n_assign} units_nz={units_nz} oi35_ok={oi_ok}; Exec={n_exec} Unassign={n_unassign} NF={n_nf} Move={n_move}"
    elif n_assign or n_unassign or n_exec:
        result = "ita_plan_leaf_hits"
        note = f"Assign={n_assign} Unassign={n_unassign} Exec={n_exec} Del={n_del} NF={n_nf} Move={n_move} oi35_ok={oi_ok}"
    elif n_nf or n_move:
        result = "ita_nf_or_move_hits_no_assign"
        note = f"NF={n_nf} Move={n_move}; Assign/Unassign/Exec empty"
    else:
        result = "ita_multi_leaf_empty"
        note = (
            f"ITA@1x hours {meta0['hours']}→{meta1['hours']} bounded {elapsed}s: "
            f"Assign/Unassign/Exec/NF/Move=0; sight={dict(sight)}; Execute leaf polish documented"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        "relaunch ITA -start_tag=ITA -start_speed=1 --allow-ai",
        f"bounded multi-leaf observe {elapsed}s polls={polls}",
        "Execute order_index leaf polish from catalog (2fn/2ft; no Capstone)",
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
        stubbed.append("live midflight Assign/Unassign hex (empty this ITA window)")
    if not n_nf:
        stubbed.append("live midflight NewFallback hex (empty this ITA window)")
    if not n_move:
        stubbed.append("ordinary CMove/SupportAttack live leaf (empty this window)")

    if result == "ita_multi_leaf_empty":
        next_blocker = (
            "NON-Post: ITA day-1 multi-leaf also quiet — longer ITA war-day observe "
            "OR heap/stage corner for lingering Assign; still NO ALLOW_POST"
        )
    elif "assign_edge" in result:
        next_blocker = (
            "NON-Post: deepen live Assign oi→OG member/instance walk from ITA hits; "
            "still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: more ITA plan-leaf samples OR name CMove midflight fields; "
            "still NO ALLOW_POST"
        )

    detail = {
        "phase": "2gg",
        "allow_post": False,
        "relaunch": relaunch,
        "map_wait": map_wait,
        "live_start": meta0,
        "live_end": meta1,
        "observe": {
            "elapsed_s": elapsed,
            "polls": polls,
            "last_counters": last_counters,
            "sight_counts": dict(sight),
            "captures": {k: v[:8] for k, v in caps.items() if v},
            "units_nonzero_assignish": units_nz,
            "oi_type35_resolve_ok": oi_ok,
        },
        "execute_leaf_polish": polish,
    }
    summary = {
        "phase": "2gg",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta1,
        "relaunch_ok": True,
        "map_wait_s": map_wait.get("elapsed_s"),
        "observe_s": elapsed,
        "polls": polls,
        "assign_captures": n_assign,
        "unassign_captures": n_unassign,
        "execute_captures": n_exec,
        "nf_rf_captures": n_nf,
        "move_captures": n_move,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "execute_leaf_polish_delta": polish["delta_note"],
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "phase2gg_ita_observe.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    (out / "phase2gg_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "elapsed_s": elapsed,
        "polls": polls,
        "sight": dict(sight),
        "assign": n_assign,
        "unassign": n_unassign,
        "exec": n_exec,
        "nf": n_nf,
        "move": n_move,
        "ui_start": meta0.get("ui_date"),
        "ui_end": meta1.get("ui_date"),
        "pid": meta1.get("pid"),
        "map_wait_s": map_wait.get("elapsed_s"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
