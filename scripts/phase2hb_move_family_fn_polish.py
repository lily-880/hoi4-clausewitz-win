#!/usr/bin/env python3
"""Phase 2hb: MOVE/SA/Cancel/Strategic IsValid+Execute FN polish (RO).

ONE slice. Live VT+0x48/VT+0x50 FN address MATCH vs catalog for MOVE /
SupportAttack / Cancel / Strategic; factory_idx 1402/3620/1415/4753
reaffirm. No midflight. No Post / no ALLOW_POST / never 5x / no recipe.
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

OUT = ROOT / "reports" / "phase2hb_move_family_fn_polish.json"
SUMMARY = ROOT / "reports" / "phase2hb_summary.json"
DOC = ROOT / "docs" / "PHASE2HB_MOVE_FAMILY_FN_POLISH.md"

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
    }


def fn_row(b, base, name, cmd):
    vt_rva = cmd["vt"]
    vt_abs = base + vt_rva
    live_isvalid = try_u64(b, vt_abs + post_abi.CCommand_VT_ISVALID)
    live_execute = try_u64(b, vt_abs + post_abi.CCommand_VT_EXECUTE)
    live_isvalid_rva = ((live_isvalid - base) & 0xFFFFFFFF) if live_isvalid else 0
    live_execute_rva = ((live_execute - base) & 0xFFFFFFFF) if live_execute else 0
    cat_isvalid = cmd["isvalid"]
    cat_execute = cmd["execute"]
    return {
        "name": name,
        "vt_rva": hex(vt_rva),
        "catalog_isvalid_rva": hex(cat_isvalid),
        "live_vt48_isvalid_rva": hex(live_isvalid_rva),
        "isvalid_match": live_isvalid_rva == cat_isvalid,
        "catalog_execute_rva": hex(cat_execute),
        "live_vt50_execute_rva": hex(live_execute_rva),
        "execute_match": live_execute_rva == cat_execute,
        "fn_both_match": live_isvalid_rva == cat_isvalid and live_execute_rva == cat_execute,
        "factory_idx": cmd.get("factory_idx"),
    }


def factory_and_fn(b, base):
    cmds = {
        "MOVE": cmd_layout.MOVE,
        "CANCEL": cmd_layout.CANCEL,
        "SUPPORT_ATTACK": cmd_layout.SUPPORT_ATTACK,
        "STRATEGIC": cmd_layout.STRATEGIC,
    }
    slots = {k: slot_row(b, base, k, c) for k, c in cmds.items()}
    fns = {k: fn_row(b, base, k, c) for k, c in cmds.items()}
    expected = {
        "MOVE": 1402,
        "CANCEL": 1415,
        "SUPPORT_ATTACK": 3620,
        "STRATEGIC": 4753,
    }
    fac_match = {
        k: slots[k]["slot_matches_catalog"] and slots[k]["factory_idx_catalog"] == expected[k]
        for k in expected
    }
    fn_match = {k: fns[k]["fn_both_match"] for k in expected}
    return {
        "expected_idx": expected,
        "factory_match": fac_match,
        "fn_match": fn_match,
        "all_factory_match": all(fac_match.values()),
        "all_fn_match": all(fn_match.values()),
        "move_1402_match": fac_match["MOVE"],
        "cancel_1415_match": fac_match["CANCEL"],
        "sa_3620_match": fac_match["SUPPORT_ATTACK"],
        "strategic_4753_match": fac_match["STRATEGIC"],
        "slots": slots,
        "fns": fns,
        "vt_slots": {
            "isvalid_off": hex(post_abi.CCommand_VT_ISVALID),
            "execute_off": hex(post_abi.CCommand_VT_EXECUTE),
        },
        "note": "MOVE and STRATEGIC share catalog execute RVA (documented)",
    }


def patch_docs(meta, result, polish):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2ha `ASSIGN_FN_MATCH_OG50_WALKBACK`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hb `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2hb** | `{result}` | MOVE/SA/Cancel/Strategic VT+0x48/0x50 FN MATCH + "
        f"factory1402/3620/1415/4753 | oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hb** |" not in t and "| **2ha** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ha** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hb move-family FN:** result=`{result}` · all_fn={polish['all_fn_match']} · "
        f"all_factory={polish['all_factory_match']} · MOVE1402={polish['move_1402_match']} · "
        f"SA3620={polish['sa_3620_match']} · Cancel1415={polish['cancel_1415_match']} · "
        f"Strat4753={polish['strategic_4753_match']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hb move-family FN:**" not in t and "**2ha FN+OG50:**" in t:
        idx = t.find("**2ha FN+OG50:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ha · Assign FN IsValid/Execute + OG50 polish · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hb · MOVE/SA/Cancel/Strategic FN polish · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ha — checklist polish (CLOSED)",
        "## Phase 2gj … 2hb — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hb | MOVE/SA/Cancel/Strategic VT FN polish | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hb |" not in t2 and "| 2ha |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ha |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ha — Assign FN IsValid/Execute + OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hb — MOVE/SA/Cancel/Strategic FN. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x MOVE/SA/Cancel/Strategic VT FN polish (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hb",
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
    polish = factory_and_fn(b, base)

    if polish["all_fn_match"] and polish["all_factory_match"]:
        result = "MOVE_FAMILY_FN_FACTORY_MATCH"
    elif polish["all_fn_match"]:
        result = "MOVE_FAMILY_FN_MATCH_FACTORY_PARTIAL"
    elif polish["all_factory_match"]:
        result = "MOVE_FAMILY_FACTORY_MATCH_FN_PARTIAL"
    else:
        result = "MOVE_FAMILY_FN_POLISH_PARTIAL"

    report = {
        "phase": "2hb",
        "result": result,
        "allow_post": False,
        "live": meta,
        "polish": polish,
        "semantics": "MOVE/SA/Cancel/Strategic VT+0x48/0x50 FN MATCH + factory; no midflight; no Post",
        "sha_base": "7488820",
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 this window (FN polish only)",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hb",
        "result": result,
        "allow_post": False,
        "live": meta,
        "all_fn_match": polish["all_fn_match"],
        "all_factory_match": polish["all_factory_match"],
        "move_fn_match": polish["fn_match"]["MOVE"],
        "cancel_fn_match": polish["fn_match"]["CANCEL"],
        "sa_fn_match": polish["fn_match"]["SUPPORT_ATTACK"],
        "strategic_fn_match": polish["fn_match"]["STRATEGIC"],
        "move_1402_match": polish["move_1402_match"],
        "cancel_1415_match": polish["cancel_1415_match"],
        "sa_3620_match": polish["sa_3620_match"],
        "strategic_4753_match": polish["strategic_4753_match"],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hb move-family FN reaffirm); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": "7488820",
        "semantics": "MOVE/SA/Cancel/Strategic VT FN MATCH; no midflight",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    fn_lines = []
    for k in ("MOVE", "CANCEL", "SUPPORT_ATTACK", "STRATEGIC"):
        f = polish["fns"][k]
        fn_lines.append(
            f"| {k} | {f['vt_rva']} | {f['factory_idx']} | "
            f"{f['catalog_isvalid_rva']} / live {f['live_vt48_isvalid_rva']} "
            f"match={f['isvalid_match']} | "
            f"{f['catalog_execute_rva']} / live {f['live_vt50_execute_rva']} "
            f"match={f['execute_match']} |"
        )

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hb — MOVE/SA/Cancel/Strategic FN polish",
                "",
                f"**Result:** `{result}`",
                "",
                f"**FN:** all_fn_match={polish['all_fn_match']} · "
                f"all_factory_match={polish['all_factory_match']}",
                "",
                "| cmd | vt | factory_idx | isvalid (cat/live) | execute (cat/live) |",
                "|-----|-----|-------------|--------------------|--------------------|",
                *fn_lines,
                "",
                "Note: MOVE and STRATEGIC share catalog execute RVA (documented).",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"pending={meta['pending']} stage={meta['stage_count']} · allow_post=False",
                "",
                "**Semantics:** Live VT+0x48 IsValid / VT+0x50 Execute MATCH catalog for "
                "MOVE/SupportAttack/Cancel/Strategic; factory slot reaffirm. No midflight / "
                "no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hb · 2026-10-31 Asia/Shanghai · sha_base 7488820*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, polish)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
