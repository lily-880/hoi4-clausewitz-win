#!/usr/bin/env python3
"""Phase 2gz: Assign/Unassign/Execute factory slot MATCH (RO).

ONE slice. Instant factory_idx 3350/3365/3352 (+ MOVE 1402) slot MATCH
reaffirm. No midflight leaf hunt. No Post / no ALLOW_POST / never 5x /
no recipe execute.
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

OUT = ROOT / "reports" / "phase2gz_assign_unassign_execute_factory.json"
SUMMARY = ROOT / "reports" / "phase2gz_summary.json"
DOC = ROOT / "docs" / "PHASE2GZ_ASSIGN_UNASSIGN_EXECUTE_FACTORY.md"

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
        "execute_rva": hex(cmd["execute"]),
        "isvalid_rva": hex(cmd["isvalid"]),
    }


def factory_corner(b, base):
    cmds = {
        "ASSIGN": cmd_layout.ORDERS["COrderAssignCommand"],
        "UNASSIGN": cmd_layout.ORDERS["COrderUnassignCommand"],
        "EXECUTE": cmd_layout.ORDERS["COrderExecuteCommand"],
        "MOVE": cmd_layout.MOVE,
    }
    rows = {k: slot_row(b, base, k, c) for k, c in cmds.items()}
    expected = {
        "ASSIGN": 3350,
        "UNASSIGN": 3365,
        "EXECUTE": 3352,
        "MOVE": 1402,
    }
    match = {
        k: rows[k]["slot_matches_catalog"] and rows[k]["factory_idx_catalog"] == expected[k]
        for k in expected
    }
    return {
        "expected_idx": expected,
        "match": match,
        "all_focus_match": all(match[k] for k in ("ASSIGN", "UNASSIGN", "EXECUTE")),
        "assign_3350_match": match["ASSIGN"],
        "unassign_3365_match": match["UNASSIGN"],
        "execute_3352_match": match["EXECUTE"],
        "move_1402_match": match["MOVE"],
        "rows": rows,
    }


def patch_docs(meta, result, fac):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gy `SA_CANCEL_FACTORY_MATCH_OG50_WALKBACK`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gz `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2gz** | `{result}` | Assign3350/Unassign3365/Execute3352(+MOVE1402) factory MATCH | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2gz** |" not in t and "| **2gy** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2gy** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2gz factory Assign/Unassign/Execute:** result=`{result}` · "
        f"Assign3350={fac['assign_3350_match']} · Unassign3365={fac['unassign_3365_match']} · "
        f"Execute3352={fac['execute_3352_match']} · MOVE1402={fac['move_1402_match']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2gz factory Assign/Unassign/Execute:**" not in t and "**2gy factory+OG50:**" in t:
        idx = t.find("**2gy factory+OG50:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2gy · SA/Cancel factory MATCH + OG50 walkback · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gz · Assign/Unassign/Execute factory MATCH · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2gy — checklist polish (CLOSED)",
        "## Phase 2gj … 2gz — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2gz | Assign3350/Unassign3365/Execute3352 factory MATCH | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2gz |" not in t2 and "| 2gy |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2gy |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2gy — SA/Cancel factory MATCH + OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gz — Assign/Unassign/Execute factory MATCH. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x Assign3350/Unassign3365/Execute3352 factory MATCH (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gz",
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
    fac = factory_corner(b, base)

    if fac["all_focus_match"] and fac["move_1402_match"]:
        result = "ASSIGN_UNASSIGN_EXECUTE_FACTORY_MATCH"
    elif fac["all_focus_match"]:
        result = "ASSIGN_UNASSIGN_EXECUTE_MATCH_MOVE_PARTIAL"
    elif fac["assign_3350_match"] and fac["unassign_3365_match"]:
        result = "ASSIGN_UNASSIGN_MATCH_EXECUTE_PARTIAL"
    else:
        result = "ASSIGN_FAMILY_FACTORY_PARTIAL"

    report = {
        "phase": "2gz",
        "result": result,
        "allow_post": False,
        "live": meta,
        "factory": fac,
        "semantics": "Assign3350/Unassign3365/Execute3352 MATCH; no midflight; no Post",
        "sha_base": "a19a549",
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 this window (catalog only)",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2gz",
        "result": result,
        "allow_post": False,
        "live": meta,
        "assign_3350_match": fac["assign_3350_match"],
        "unassign_3365_match": fac["unassign_3365_match"],
        "execute_3352_match": fac["execute_3352_match"],
        "move_1402_match": fac["move_1402_match"],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2gz Assign/Unassign/Execute factory reaffirm); "
            "push when GitHub reachable; still NO ALLOW_POST"
        ),
        "sha_base": "a19a549",
        "semantics": "Assign3350/Unassign3365/Execute3352 MATCH; no midflight",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gz — Assign/Unassign/Execute factory MATCH",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Factory:** Assign3350={fac['assign_3350_match']} · "
                f"Unassign3365={fac['unassign_3365_match']} · "
                f"Execute3352={fac['execute_3352_match']} · "
                f"MOVE1402={fac['move_1402_match']}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"pending={meta['pending']} stage={meta['stage_count']} · allow_post=False",
                "",
                "**Semantics:** Instant factory slot MATCH reaffirm for Assign/Unassign/Execute "
                "(+ MOVE). No midflight leaf hunt. No Post / no recipe execute / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2gz · 2026-10-31 Asia/Shanghai · sha_base a19a549*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, fac)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
