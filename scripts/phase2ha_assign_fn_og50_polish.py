#!/usr/bin/env python3
"""Phase 2ha: Assign/Unassign/Execute IsValid/Execute FN polish + OG50 (RO).

ONE slice. Live VT+0x48/VT+0x50 FN address MATCH vs catalog for Assign/
Unassign/Execute; factory_idx 3350/3365/3352 reaffirm; OG+0x50 walkback
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
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ha_assign_fn_og50_polish.json"
SUMMARY = ROOT / "reports" / "phase2ha_summary.json"
DOC = ROOT / "docs" / "PHASE2HA_ASSIGN_FN_OG50_POLISH.md"

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
    }


def fn_row(b, base, name, cmd):
    """Live VT+0x48 IsValid / VT+0x50 Execute vs catalog."""
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
        "isvalid_kind": cmd.get("isvalid_kind"),
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
        "ASSIGN": cmd_layout.ORDERS["COrderAssignCommand"],
        "UNASSIGN": cmd_layout.ORDERS["COrderUnassignCommand"],
        "EXECUTE": cmd_layout.ORDERS["COrderExecuteCommand"],
    }
    slots = {k: slot_row(b, base, k, c) for k, c in cmds.items()}
    fns = {k: fn_row(b, base, k, c) for k, c in cmds.items()}
    expected = {"ASSIGN": 3350, "UNASSIGN": 3365, "EXECUTE": 3352}
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
        "assign_3350_match": fac_match["ASSIGN"],
        "unassign_3365_match": fac_match["UNASSIGN"],
        "execute_3352_match": fac_match["EXECUTE"],
        "slots": slots,
        "fns": fns,
        "vt_slots": {
            "isvalid_off": hex(post_abi.CCommand_VT_ISVALID),
            "execute_off": hex(post_abi.CCommand_VT_EXECUTE),
        },
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
        "ca_mi_b8_rva": hex(CA_MI_B8),
    }


def patch_docs(meta, result, polish, walk):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gz `ASSIGN_UNASSIGN_EXECUTE_FACTORY_MATCH`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2ha `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2ha** | `{result}` | Assign/Unassign/Execute VT+0x48/0x50 FN MATCH + "
        f"factory3350/3365/3352 + OG50 {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2ha** |" not in t and "| **2gz** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2gz** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ha FN+OG50:** result=`{result}` · all_fn={polish['all_fn_match']} · "
        f"all_factory={polish['all_factory_match']} · walkback "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2ha FN+OG50:**" not in t and "**2gz factory Assign/Unassign/Execute:**" in t:
        idx = t.find("**2gz factory Assign/Unassign/Execute:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2gz · Assign/Unassign/Execute factory MATCH · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ha · Assign FN IsValid/Execute + OG50 polish · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2gz — checklist polish (CLOSED)",
        "## Phase 2gj … 2ha — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ha | Assign/Unassign/Execute VT FN + OG50 polish | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ha |" not in t2 and "| 2gz |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2gz |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2gz — Assign/Unassign/Execute factory MATCH. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ha — Assign FN IsValid/Execute + OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x Assign/Unassign/Execute VT FN + OG50 polish (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ha",
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
    walk = og50_walkback(b, base)

    if polish["all_fn_match"] and polish["all_factory_match"] and walk["walkback_fail"] == 0 and walk["walkback_ok"] > 0:
        result = "ASSIGN_FN_MATCH_OG50_WALKBACK"
    elif polish["all_fn_match"] and polish["all_factory_match"]:
        result = "ASSIGN_FN_FACTORY_MATCH_OG50_PARTIAL"
    elif polish["all_fn_match"]:
        result = "ASSIGN_FN_MATCH_FACTORY_PARTIAL"
    else:
        result = "ASSIGN_FN_POLISH_PARTIAL"

    report = {
        "phase": "2ha",
        "result": result,
        "allow_post": False,
        "live": meta,
        "polish": polish,
        "og50": walk,
        "semantics": "VT+0x48/0x50 FN MATCH + factory3350/3365/3352 + OG50; no midflight; no Post",
        "sha_base": "b740baf",
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
        "phase": "2ha",
        "result": result,
        "allow_post": False,
        "live": meta,
        "all_fn_match": polish["all_fn_match"],
        "all_factory_match": polish["all_factory_match"],
        "assign_fn_match": polish["fn_match"]["ASSIGN"],
        "unassign_fn_match": polish["fn_match"]["UNASSIGN"],
        "execute_fn_match": polish["fn_match"]["EXECUTE"],
        "walkback_ok": walk["walkback_ok"],
        "walkback_fail": walk["walkback_fail"],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2ha FN+OG50 reaffirm); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": "b740baf",
        "semantics": "Assign/Unassign/Execute VT FN MATCH + OG50; no midflight",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    fn_lines = []
    for k in ("ASSIGN", "UNASSIGN", "EXECUTE"):
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
                "# Phase 2ha — Assign FN IsValid/Execute + OG50 polish",
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
                f"**OG50:** walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
                f"ita_members={walk['ita_members']}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"pending={meta['pending']} stage={meta['stage_count']} · allow_post=False",
                "",
                "**Semantics:** Live VT+0x48 IsValid / VT+0x50 Execute MATCH catalog for "
                "Assign/Unassign/Execute; factory slot reaffirm; OG50 walkback. No midflight / "
                "no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2ha · 2026-10-31 Asia/Shanghai · sha_base b740baf*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, polish, walk)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
