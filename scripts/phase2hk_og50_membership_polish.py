#!/usr/bin/env python3
"""Phase 2hk: OG50 membership polish + 2hj matrix fold (RO).

One-shot OG+0x50 ≡ CArmy+0xB8 walkback reaffirm; fold 2hj PATH200 multi-army
matrix (1042/1048 @+0x60; empty 1039/1043/1046/1049) into LAND_POST / SAFE /
§6f. NO midflight / no oi≠0 poll / no PATH200 re-poll / no Post / never 5x /
no speed write.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hk_og50_membership_polish.json"
SUMMARY = ROOT / "reports" / "phase2hk_summary.json"
DOC = ROOT / "docs" / "PHASE2HK_OG50_MEMBERSHIP_POLISH.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
SHA_BASE = "900f7e2"

# Catalog fold from 2hj PATH200_MULTI_ARMY_MATRIX_HIT (no re-poll)
HJ_MATRIX = {
    "result": "PATH200_MULTI_ARMY_MATRIX_HIT",
    "carmy": 6,
    "empty": [1039, 1043, 1046, 1049],
    "nonempty": [{"index": 1048, "province_id": 985, "off60": [3938]}],
    "multi": [{"index": 1042, "province_id": 11819, "off60": [915, 490]}],
    "cand_offs": ["0x60"],
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


def live_meta(b, base, pid, tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    year = i32(b, gs + 0x478)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "year_at_0x478": year,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": tag,
        "scenario": "ITA OG50 membership polish + 2hj matrix fold (no Post, no midflight, no oi≠0)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
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
    ok = fail = ita = 0
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
                if len(samples) < 4:
                    samples.append({"oi": oi, "primary": hex(primary), "tag": atag})
            else:
                fail += 1
    return {
        "proxy": "OG+0x50[i] == CArmy+0xB8 (VT 0x29d6fb8)",
        "walkback_ok": ok,
        "walkback_fail": fail,
        "ita_members": ita,
        "samples": samples,
    }


def patch_docs(meta, result, walk):
    w_tot = walk["walkback_ok"] + walk["walkback_fail"]
    w_s = f"{walk['walkback_ok']}/{w_tot}"
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hj `PATH200_MULTI_ARMY_MATRIX_HIT`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hk `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    t = re.sub(
        r"\| `PATH200` \| multi-prov candidates \| 2hj matrix[^\n]*\|\n",
        "| `PATH200` | multi-prov candidates | 2hj/2hk matrix multi=1042→[915,490] "
        "nonempty=1048→[3938] empty=1039/1043/1046/1049 @+0x60 |\n",
        t,
        count=1,
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — walkback [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — walkback "
        f"{w_s} ita={walk['ita_members']} (2hk polish) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hk** | `{result}` | OG50 walkback polish + 2hj matrix fold into §6f | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hk** |" not in t and "| **2hj** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hj** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hk OG50 membership polish:** result=`{result}` · walkback {w_s} · "
        f"ita_members={walk['ita_members']} · 2hj matrix fold multi=1042 "
        f"nonempty=1048 empty=1039/1043/1046/1049 · hours={meta.get('hours')} "
        f"UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hk OG50 membership polish:**" not in t and "**2hj PATH200 multi-army matrix:**" in t:
        idx = t.find("**2hj PATH200 multi-army matrix:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hj · PATH200 multi-army matrix · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hk · OG50 membership polish + 2hj matrix fold · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hj — checklist polish (CLOSED)",
        "## Phase 2gj … 2hk — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hk | OG50 walkback polish + 2hj PATH200 matrix fold | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hk |" not in t2 and "| 2hj |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hj |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hj — PATH200 multi-army matrix. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hk — OG50 membership polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hk",
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
    meta = live_meta(b, base, pid, tag)
    walk = og50_walkback(b, base)

    w_ok = walk["walkback_ok"]
    w_fail = walk["walkback_fail"]
    if w_fail == 0 and w_ok > 0:
        result = "OG50_MEMBERSHIP_POLISH_HIT"
    elif w_ok > 0:
        result = "OG50_MEMBERSHIP_POLISH_PARTIAL"
    else:
        result = "OG50_MEMBERSHIP_POLISH_EMPTY"

    report = {
        "phase": "2hk",
        "result": result,
        "allow_post": False,
        "live": meta,
        "og50_walkback": walk,
        "hj_matrix_fold": HJ_MATRIX,
        "sha_base": SHA_BASE,
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "speed write",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 long poll",
            "PATH200 re-poll this slice",
            "named movement_dest invent",
        ],
        "semantics": (
            "OG50 membership one-shot polish + catalog fold of 2hj matrix; "
            "demangled OG+0x50 name still STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hk",
        "result": result,
        "allow_post": False,
        "live": meta,
        "walkback_ok": w_ok,
        "walkback_fail": w_fail,
        "ita_members": walk.get("ita_members"),
        "hj_multi": HJ_MATRIX["multi"],
        "hj_nonempty": HJ_MATRIX["nonempty"],
        "hj_empty": HJ_MATRIX["empty"],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hk OG50 polish); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "OG50 walkback polish + 2hj matrix fold; no oi≠0/midflight/PATH200 re-poll; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hk — OG50 membership polish + 2hj matrix fold",
                "",
                f"**Result:** `{result}`",
                "",
                f"**OG+0x50 walkback:** {w_ok}/{w_ok + w_fail} · "
                f"ita_members={walk.get('ita_members')} · samples={walk.get('samples')}",
                "",
                f"**2hj matrix fold (catalog):** multi={HJ_MATRIX['multi']} · "
                f"nonempty={HJ_MATRIX['nonempty']} · empty={HJ_MATRIX['empty']} · "
                f"offs={HJ_MATRIX['cand_offs']}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Membership proxy OG+0x50 ≡ CArmy+0xB8 (VT 0x29d6fb8). "
                "Demangled +0x50 name STUBBED. No PATH200/oi≠0/midflight re-poll. No Post.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hk · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, walk)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
