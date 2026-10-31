#!/usr/bin/env python3
"""Phase 2gy: SupportAttack/Cancel factory slot MATCH + OG50 walkback (RO).

ONE slice. Instant factory_idx 3620/1415 (+ MOVE 1402 / Strategic 4753) slot
MATCH reaffirm + OG+0x50≡CArmy+0xB8 walkback polish. No midflight leaf hunt.
No Post / no ALLOW_POST / never 5x / no recipe execute.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gy_sa_cancel_factory_og50.json"
SUMMARY = ROOT / "reports" / "phase2gy_summary.json"
DOC = ROOT / "docs" / "PHASE2GY_SA_CANCEL_FACTORY_OG50.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_B8 = 0x29D6FB8
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0


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
        "MOVE": cmd_layout.MOVE,
        "CANCEL": cmd_layout.CANCEL,
        "SUPPORT_ATTACK": cmd_layout.SUPPORT_ATTACK,
        "STRATEGIC": cmd_layout.STRATEGIC,
        "ASSIGN": cmd_layout.ORDERS["COrderAssignCommand"],
    }
    rows = {k: slot_row(b, base, k, c) for k, c in cmds.items()}
    expected = {
        "MOVE": 1402,
        "CANCEL": 1415,
        "SUPPORT_ATTACK": 3620,
        "STRATEGIC": 4753,
    }
    match = {
        k: rows[k]["slot_matches_catalog"] and rows[k]["factory_idx_catalog"] == expected[k]
        for k in expected
    }
    return {
        "expected_idx": expected,
        "match": match,
        "all_focus_match": all(match.values()),
        "sa_3620_match": match["SUPPORT_ATTACK"],
        "cancel_1415_match": match["CANCEL"],
        "move_1402_match": match["MOVE"],
        "strategic_4753_match": match["STRATEGIC"],
        "rows": rows,
    }


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
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs}


def og50_walkback(b, base):
    ok = fail = 0
    ita = 0
    tag = player_tag(b, base)
    samples = []
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
        for p in arr50["ptrs"]:
            if not p:
                continue
            primary = p - CA_MI_OFF
            vt = try_u64(b, primary)
            if vt and (vt - base) == CA_VT_RVA:
                ok += 1
                atag = try_u32(b, primary + CA_TAG)
                if atag == tag:
                    ita += 1
                if len(samples) < 6:
                    samples.append({"oi": oi, "primary": hex(primary), "tag": atag})
            else:
                fail += 1
    return {
        "proxy": "OG+0x50[i] == CArmy+0xB8 (VT 0x29d6fb8)",
        "walkback_ok": ok,
        "walkback_fail": fail,
        "ita_members": ita,
        "samples": samples,
        "handle_type_army": HANDLE_TYPE_ARMY,
    }


def patch_docs(meta, result, fac, walk):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gx `ASSIGN_QUIET_FACTORY1402_MATCH`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gy `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2gy** | `{result}` | SA3620/Cancel1415(+MOVE1402/Strat4753) factory MATCH + "
        f"OG50 walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2gy** |" not in t and "| **2gx** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2gx** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2gy factory+OG50:** result=`{result}` · SA3620={fac['sa_3620_match']} · "
        f"Cancel1415={fac['cancel_1415_match']} · MOVE1402={fac['move_1402_match']} · "
        f"Strat4753={fac['strategic_4753_match']} · walkback "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2gy factory+OG50:**" not in t and "**2gx cheap edge:**" in t:
        idx = t.find("**2gx cheap edge:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2gx · Assign oi≠0 edge + factory corner · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gy · SA/Cancel factory MATCH + OG50 walkback · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2gx — checklist polish (CLOSED)",
        "## Phase 2gj … 2gy — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2gy | SA3620/Cancel1415 factory MATCH + OG50 walkback | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2gy |" not in t2 and "| 2gx |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2gx |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2gx — Assign oi≠0 edge + factory corner. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gy — SA/Cancel factory MATCH + OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x SA3620/Cancel1415 factory MATCH + OG50 walkback (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gy",
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
    walk = og50_walkback(b, base)

    if fac["all_focus_match"] and walk["walkback_fail"] == 0 and walk["walkback_ok"] > 0:
        result = "SA_CANCEL_FACTORY_MATCH_OG50_WALKBACK"
    elif fac["sa_3620_match"] and fac["cancel_1415_match"] and walk["walkback_fail"] == 0:
        result = "SA_CANCEL_MATCH_OG50_OK_PARTIAL_FAMILY"
    elif fac["sa_3620_match"] and fac["cancel_1415_match"]:
        result = "SA_CANCEL_FACTORY_MATCH_OG50_PARTIAL"
    else:
        result = "FACTORY_OR_OG50_PARTIAL"

    next_b = (
        "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
        "plan-dense Assign oi≠0 (2gy factory+OG50 reaffirm); push when GitHub "
        "reachable; still NO ALLOW_POST"
    )
    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk; no midflight leaf hunt",
        f"SA3620={fac['sa_3620_match']} Cancel1415={fac['cancel_1415_match']} MOVE1402={fac['move_1402_match']} Strat4753={fac['strategic_4753_match']}",
        f"OG+0x50 MI walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
        "LAND_POST/SAFE_POST 2gy row",
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
        "Assign oi≠0 units↔OI confirm",
        "ask-user right-click",
        "Capstone/121 re-churn",
        "long midflight empty poll",
    ]

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gy",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "midflight_leaf_hunt": False,
        "result": result,
        "live": meta,
        "factory_corner": fac,
        "og50_walkback": walk,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "f1fb883",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "phase": "2gy",
        "result": result,
        "allow_post": False,
        "live": meta,
        "sa_3620_match": fac["sa_3620_match"],
        "cancel_1415_match": fac["cancel_1415_match"],
        "move_1402_match": fac["move_1402_match"],
        "strategic_4753_match": fac["strategic_4753_match"],
        "walkback_ok": walk["walkback_ok"],
        "walkback_fail": walk["walkback_fail"],
        "next_shortest_blocker": next_b,
        "sha_base": "f1fb883",
        "semantics": (
            f"SA3620/Cancel1415 MATCH; walkback "
            f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}; no midflight"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gy — SA/Cancel factory MATCH + OG50 walkback (RO)",
                "",
                f"**Result:** `{result}`",
                f"**Live:** pid {meta['pid']} · {meta['ui_date']} · hours={meta['hours']} · tag={tag} · @1x",
                f"**Factory MATCH:** SA3620={fac['sa_3620_match']} · Cancel1415={fac['cancel_1415_match']} · MOVE1402={fac['move_1402_match']} · Strat4753={fac['strategic_4753_match']}",
                f"**OG+0x50 walkback:** {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
                "",
                "**allow_post:** **False** · no midflight leaf hunt · never 5x · recipes **NOT executed**",
                "",
                "## Method",
                "",
                "Instant factory table slot RO for SupportAttack/Cancel (+ MOVE/Strategic) + OG+0x50≡CArmy+0xB8 walkback.",
                "Folds 2gx MOVE1402 into land-cmd factory family reaffirm.",
                "",
                f"**Next:** {next_b}",
                "",
                "Script: `scripts/phase2gy_sa_cancel_factory_og50.py`",
                f"*Phase 2gy · {sh} Asia/Shanghai*",
                "",
            ]
        ),
        encoding="utf-8",
    )
    patch_docs(meta, result, fac, walk)
    print(
        json.dumps(
            {
                "result": result,
                "live": {
                    "pid": meta["pid"],
                    "hours": meta["hours"],
                    "ui_date": meta["ui_date"],
                    "speed_policy": meta["speed_policy"],
                    "country_tag_filter": tag,
                    "scenario": scenario,
                    "pending": meta["pending"],
                    "stage_count": meta["stage_count"],
                    "allow_post": False,
                },
                "sa_3620_match": fac["sa_3620_match"],
                "cancel_1415_match": fac["cancel_1415_match"],
                "move_1402_match": fac["move_1402_match"],
                "strategic_4753_match": fac["strategic_4753_match"],
                "walkback": f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
