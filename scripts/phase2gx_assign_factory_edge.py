#!/usr/bin/env python3
"""Phase 2gx: Cheap Assign oi≠0 edge + factory/execlist corner (RO).

ONE slice. ≤30s Assign/Unassign pending/stage only (no long midflight leaf hunt).
Instant MOVE factory_idx 1402 RO reaffirm. Catalog LAND_POST/SAFE 2gx row.
No Post / no ALLOW_POST / never 5x / no recipe execute / no ask right-click.
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
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gx_assign_factory_edge.json"
SUMMARY = ROOT / "reports" / "phase2gx_summary.json"
DOC = ROOT / "docs" / "PHASE2GX_ASSIGN_FACTORY_EDGE.md"

OBSERVE_S = 30.0
POLL_SLEEP = 0.04
GS_PLAYER_TAG = 0x518

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


def factory_idx(tid: int) -> int:
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


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


def factory_corner(b, base):
    """Instant MOVE + Assign factory_idx RO (no Post)."""
    rows = {}
    for key, cmd in (
        ("MOVE", cmd_layout.MOVE),
        ("ASSIGN", ASSIGN),
        ("STRATEGIC", cmd_layout.STRATEGIC),
    ):
        ft = cmd_layout.FACTORY_TABLE
        tid = cmd["type_id"]
        idx = factory_idx(tid)
        idx_cat = cmd.get("factory_idx")
        slot = try_u64(b, base + ft["rva"] + (idx_cat or 0) * 8)
        slot_rva = ((slot - base) & 0xFFFFFFFF) if slot else 0
        rows[key] = {
            "type_id": hex(tid),
            "factory_idx_catalog": idx_cat,
            "factory_idx_formula": idx,
            "idx_formula_matches_catalog": idx == idx_cat,
            "catalog_factory_rva": hex(cmd["factory"]),
            "slot_rva": hex(slot_rva),
            "slot_matches_catalog": slot_rva == cmd["factory"],
            "execute_rva": hex(cmd["execute"]),
            "isvalid_rva": hex(cmd["isvalid"]),
        }
    # execlist corner: drain/exec counters only (RO)
    sess = try_u64(b, base + post_abi.G_SESSION)
    execlist = {}
    if sess:
        execlist = {
            "drain": try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
            "exec": try_u32(b, sess + post_abi.CSession_EXEC_COUNTER),
            "stage_count": try_u32(b, sess + post_abi.CSession_STAGE_COUNT),
            "note": "counters only — no Post / no inject",
        }
    move_ok = rows["MOVE"]["slot_matches_catalog"] and rows["MOVE"]["factory_idx_catalog"] == 1402
    return {
        "move_factory_1402_match": move_ok,
        "commands": rows,
        "execlist_counters": execlist,
    }


def patch_docs(meta, result, assign_stats, fac):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gw checklist: midflight ceiling closed for non-interactive); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gx `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2gx** | `{result}` | ≤30s Assign oi≠0 edge + MOVE factory1402/"
        f"execlist corner | oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2gx** |" not in t and "| **2gw** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2gw** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2gx cheap edge:** result=`{result}` · assign_sight={assign_stats['sight_n']} · "
        f"oi≠0={assign_stats['oi_nonzero_n']} · factory1402_match={fac['move_factory_1402_match']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2gx cheap edge:**" not in t and "**2gw live path" in t:
        idx = t.find("**2gw live path")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2gw · agent checklist catalog polish · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gx · Assign oi≠0 edge + factory corner · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2gw — checklist polish (CLOSED)",
        "## Phase 2gj … 2gx — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2gx | ≤30s Assign oi≠0 edge + factory1402/execlist corner | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2gx |" not in t2 and "| 2gw |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2gw |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2gw — agent checklist catalog polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gx — Assign oi≠0 edge + factory corner. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x ≤30s Assign oi≠0 edge + factory/execlist corner (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gx",
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
    fac = factory_corner(b, base)

    t0 = time.time()
    polls = 0
    sight = Counter()
    assigns = []
    seen = set()
    last_counters = None
    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = walk_pending_stage(b, base)
        for h in hits:
            name = h.get("name") or "?"
            sight[name] += 1
            key = (name, h.get("addr"), h.get("source"))
            if key in seen:
                continue
            seen.add(key)
            assigns.append(h)
            # early stop on oi≠0
            if (h.get("order_index") or 0) != 0:
                break
        if any((a.get("order_index") or 0) != 0 for a in assigns):
            break
        time.sleep(POLL_SLEEP)

    observe_s = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, pid, tag, scenario)
    oi_nz = [a for a in assigns if (a.get("order_index") or 0) != 0]
    oi_z = [a for a in assigns if (a.get("order_index") or 0) == 0]

    if oi_nz:
        result = "ASSIGN_OI_NONZERO_EDGE_HIT"
    elif assigns:
        result = "ASSIGN_OI_ZERO_ONLY_FACTORY_CORNER"
    elif fac.get("move_factory_1402_match"):
        result = "ASSIGN_QUIET_FACTORY1402_MATCH"
    else:
        result = "ASSIGN_QUIET_FACTORY_CORNER_PARTIAL"

    assign_stats = {
        "sight_n": len(assigns),
        "oi_nonzero_n": len(oi_nz),
        "oi_zero_n": len(oi_z),
        "by_name": dict(sight),
    }
    next_b = (
        "NON-Post: Assign oi≠0 HIT this window — catalog units↔OI / OG+0x50 cross; "
        "push when GitHub reachable; still NO ALLOW_POST"
        if oi_nz
        else (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2gx cheap edge quiet); push when GitHub reachable; "
            "still NO ALLOW_POST"
        )
    )
    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk; no long midflight poll",
        f"≤{observe_s}s Assign pending/stage polls={polls} sight={len(assigns)} oi≠0={len(oi_nz)}",
        f"MOVE factory_idx 1402 match={fac.get('move_factory_1402_match')}",
        "LAND_POST/SAFE_POST 2gx row",
    ]
    stubbed = [
        "demangled OG+0x50 / MI field name",
        "named movement_dest",
        "ring_embed execute",
        "2fb/2gk recipe execute",
        "ALLOW_POST / CLAUSEWITZ_ALLOW_POST",
        "tool-gate open",
        "CMove midflight hex",
        "Post inject",
        "ask-user right-click",
        "Capstone/121 re-churn",
        "long midflight empty poll",
    ]
    if not oi_nz:
        stubbed.append("Assign oi≠0 units↔OI this window")

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gx",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "midflight_leaf_hunt": False,
        "result": result,
        "live_start": meta0,
        "live_end": meta1,
        "observe_s": observe_s,
        "polls": polls,
        "assign_stats": assign_stats,
        "assigns_sample": assigns[:8],
        "oi_nonzero_sample": oi_nz[:4],
        "factory_corner": fac,
        "last_counters": last_counters,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "845bd88",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "phase": "2gx",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "observe_s": observe_s,
        "polls": polls,
        "assign_sight": len(assigns),
        "assign_oi_nonzero": len(oi_nz),
        "factory1402_match": fac.get("move_factory_1402_match"),
        "next_shortest_blocker": next_b,
        "sha_base": "845bd88",
        "semantics": (
            f"≤30s Assign edge oi≠0={len(oi_nz)} sight={len(assigns)}; "
            f"factory1402={fac.get('move_factory_1402_match')}; no midflight"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gx — Assign oi≠0 edge + factory/execlist corner (RO)",
                "",
                f"**Result:** `{result}`",
                f"**Live:** pid {meta1['pid']} · {meta1['ui_date']} · hours={meta1['hours']} · tag={tag} · @1x",
                f"**Observe:** {observe_s}s · polls={polls} · assign_sight={len(assigns)} · oi≠0={len(oi_nz)}",
                f"**Factory:** MOVE factory_idx 1402 match={fac.get('move_factory_1402_match')}",
                "",
                "**allow_post:** **False** · no midflight leaf hunt · never 5x · recipes **NOT executed**",
                "",
                "## Method",
                "",
                "≤30s Assign/Unassign pending/stage only + instant factory/execlist corner.",
                "Not another long midflight empty poll.",
                "",
                f"**Next:** {next_b}",
                "",
                "Script: `scripts/phase2gx_assign_factory_edge.py`",
                f"*Phase 2gx · {sh} Asia/Shanghai*",
                "",
            ]
        ),
        encoding="utf-8",
    )
    patch_docs(meta1, result, assign_stats, fac)
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
                "observe_s": observe_s,
                "assign_sight": len(assigns),
                "assign_oi_nonzero": len(oi_nz),
                "factory1402_match": fac.get("move_factory_1402_match"),
                "polls": polls,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
