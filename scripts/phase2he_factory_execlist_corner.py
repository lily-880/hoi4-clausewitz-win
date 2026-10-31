#!/usr/bin/env python3
"""Phase 2he: Factory family MATCH + Dummy execlist/ring corner (RO).

ONE slice. Instant full land-family factory_idx MATCH + CDummyServer
execlist/ring/pending head-tail-count corner. NO Assign oi≠0 hunt.
NO midflight. No Post / never 5x / no recipe execute.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2he_factory_execlist_corner.json"
SUMMARY = ROOT / "reports" / "phase2he_summary.json"
DOC = ROOT / "docs" / "PHASE2HE_FACTORY_EXECLIST_CORNER.md"

GS_PLAYER_TAG = 0x518


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


def slot_row(b, base, name, cmd):
    ft = cmd_layout.FACTORY_TABLE
    tid = cmd["type_id"]
    idx = factory_idx(tid)
    idx_cat = cmd.get("factory_idx")
    slot = try_u64(b, base + ft["rva"] + (idx_cat or 0) * 8)
    slot_rva = ((slot - base) & 0xFFFFFFFF) if slot else 0
    return {
        "name": name,
        "type_id": hex(tid),
        "factory_idx_catalog": idx_cat,
        "factory_idx_formula": idx,
        "idx_formula_matches_catalog": idx == idx_cat,
        "catalog_factory_rva": hex(cmd["factory"]),
        "slot_rva": hex(slot_rva),
        "slot_matches_catalog": slot_rva == cmd["factory"],
    }


def factory_family(b, base):
    cmds = {
        "MOVE": (cmd_layout.MOVE, 1402),
        "CANCEL": (cmd_layout.CANCEL, 1415),
        "SUPPORT_ATTACK": (cmd_layout.SUPPORT_ATTACK, 3620),
        "STRATEGIC": (cmd_layout.STRATEGIC, 4753),
        "ASSIGN": (cmd_layout.ORDERS["COrderAssignCommand"], 3350),
        "UNASSIGN": (cmd_layout.ORDERS["COrderUnassignCommand"], 3365),
        "EXECUTE": (cmd_layout.ORDERS["COrderExecuteCommand"], 3352),
    }
    rows = {}
    match = {}
    for k, (cmd, exp) in cmds.items():
        row = slot_row(b, base, k, cmd)
        rows[k] = row
        match[k] = row["slot_matches_catalog"] and row["factory_idx_catalog"] == exp
    return {
        "expected": {k: exp for k, (_, exp) in cmds.items()},
        "match": match,
        "all_match": all(match.values()),
        "rows": rows,
    }


def execlist_ring_corner(b, base):
    """One-shot DummyServer execlist/ring/pending structure (RO)."""
    sess = try_u64(b, base + post_abi.G_SESSION)
    if not sess:
        return {"error": "no_session"}
    server = try_u64(b, sess + post_abi.CSession_SERVER)
    if not server:
        return {"error": "no_server", "sess": hex(sess)}
    vt = try_u64(b, server)
    vt_rva = ((vt - base) & 0xFFFFFFFF) if vt else 0
    # pending list: head@+0x58, tail@+0x60, count@+0x68
    pend_head = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    pend_tail = try_u64(b, server + post_abi.CDummyServer_PENDING + 8) or 0
    pend_count = try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
    # execlist: head@+0x40, tail@+0x48, count@+0x50
    exec_head = try_u64(b, server + post_abi.CDummyServer_EXECLIST) or 0
    exec_tail = try_u64(b, server + post_abi.CDummyServer_EXECLIST + 8) or 0
    exec_count = try_u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10)
    # ring @+0xA0 (pointer / opaque — RO presence only)
    ring_ptr = try_u64(b, server + post_abi.CDummyServer_RING) or 0
    stage_count = try_u32(b, sess + post_abi.CSession_STAGE_COUNT)
    drain = try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = try_u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    return {
        "server": hex(server),
        "server_vt_rva": hex(vt_rva),
        "server_vt_matches_dummy": vt_rva == post_abi.CDummyServer_VT,
        "pending": {
            "head": hex(pend_head) if pend_head else "0",
            "tail": hex(pend_tail) if pend_tail else "0",
            "count": pend_count,
            "empty": pend_head == 0 and (pend_count or 0) == 0,
        },
        "execlist": {
            "off": hex(post_abi.CDummyServer_EXECLIST),
            "head": hex(exec_head) if exec_head else "0",
            "tail": hex(exec_tail) if exec_tail else "0",
            "count": exec_count,
            "empty": exec_head == 0 and (exec_count or 0) == 0,
        },
        "ring": {
            "off": hex(post_abi.CDummyServer_RING),
            "ptr": hex(ring_ptr) if ring_ptr else "0",
            "present": ring_ptr != 0,
            "note": "RO presence only — no ring push / no Post",
        },
        "session_counters": {
            "stage_count": stage_count,
            "drain": drain,
            "exec": exec_c,
        },
        "offsets": {
            "pending_head": hex(post_abi.CDummyServer_PENDING),
            "execlist_head": hex(post_abi.CDummyServer_EXECLIST),
            "ring": hex(post_abi.CDummyServer_RING),
            "dummy_vt": hex(post_abi.CDummyServer_VT),
        },
        "semantics": "one-shot structure corner; empty lists are honest quiet, not a poll miss",
    }


def patch_docs(meta, result, fac, corner):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hd `SAFEPOST_6F_POINTERS_POLISH`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2he `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2he** | `{result}` | Full land factory MATCH + Dummy execlist/ring/pending corner | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2he** |" not in t and "| **2hd** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hd** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2he factory+execlist corner:** result=`{result}` · all_factory={fac['all_match']} · "
        f"dummy_vt={corner.get('server_vt_matches_dummy')} · "
        f"execlist_empty={corner.get('execlist', {}).get('empty')} · "
        f"pending_empty={corner.get('pending', {}).get('empty')} · "
        f"ring_present={corner.get('ring', {}).get('present')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2he factory+execlist corner:**" not in t and "**2hd SAFE_POST §6f pointers:**" in t:
        idx = t.find("**2hd SAFE_POST §6f pointers:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hd · SAFE_POST §6f pointers · 2026-10-31 Asia/Shanghai*",
        "*Phase 2he · factory + execlist/ring corner · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hd — checklist polish (CLOSED)",
        "## Phase 2gj … 2he — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2he | Full land factory MATCH + Dummy execlist/ring corner | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2he |" not in t2 and "| 2hd |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hd |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hd — SAFE_POST §6f pointers. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2he — factory + execlist/ring corner. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x factory family + Dummy execlist/ring corner (no Post, no midflight, no oi≠0 poll)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2he",
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
    meta = live_meta(b, base, pid, tag, scenario)
    fac = factory_family(b, base)
    corner = execlist_ring_corner(b, base)

    dummy_ok = corner.get("server_vt_matches_dummy") is True
    struct_ok = (
        dummy_ok
        and "execlist" in corner
        and "pending" in corner
        and "ring" in corner
    )

    if fac["all_match"] and struct_ok:
        result = "FACTORY_EXECLIST_RING_CORNER"
    elif fac["all_match"]:
        result = "FACTORY_MATCH_EXECLIST_PARTIAL"
    elif struct_ok:
        result = "EXECLIST_CORNER_FACTORY_PARTIAL"
    else:
        result = "FACTORY_EXECLIST_PARTIAL"

    report = {
        "phase": "2he",
        "result": result,
        "allow_post": False,
        "live": meta,
        "factory": fac,
        "execlist_ring_corner": corner,
        "semantics": "full land factory MATCH + Dummy execlist/ring/pending one-shot; no oi≠0 poll; no midflight; no Post",
        "sha_base": "51674fd",
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 long poll this window",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2he",
        "result": result,
        "allow_post": False,
        "live": meta,
        "all_factory_match": fac["all_match"],
        "dummy_vt_match": dummy_ok,
        "execlist_empty": corner.get("execlist", {}).get("empty"),
        "pending_empty": corner.get("pending", {}).get("empty"),
        "ring_present": corner.get("ring", {}).get("present"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2he factory+execlist corner); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": "51674fd",
        "semantics": "factory family MATCH + execlist/ring corner; no oi≠0 poll; no midflight",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2he — Factory + Dummy execlist/ring corner",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Factory:** all_match={fac['all_match']} · "
                + " · ".join(f"{k}={v}" for k, v in fac["match"].items()),
                "",
                f"**DummyServer:** vt_match={dummy_ok} · "
                f"execlist_empty={corner.get('execlist', {}).get('empty')} · "
                f"pending_empty={corner.get('pending', {}).get('empty')} · "
                f"ring_present={corner.get('ring', {}).get('present')}",
                "",
                f"**Offsets:** execlist@{hex(post_abi.CDummyServer_EXECLIST)} · "
                f"pending@{hex(post_abi.CDummyServer_PENDING)} · "
                f"ring@{hex(post_abi.CDummyServer_RING)} · "
                f"VT `{hex(post_abi.CDummyServer_VT)}`",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"pending={meta['pending']} stage={meta['stage_count']} · allow_post=False",
                "",
                "**Semantics:** Instant full land-family factory MATCH + one-shot Dummy "
                "execlist/ring/pending structure corner. Empty lists = honest quiet. "
                "No Assign oi≠0 poll / no midflight / no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2he · 2026-10-31 Asia/Shanghai · sha_base 51674fd*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, fac, corner)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
