#!/usr/bin/env python3
"""Phase 2hh: Post-reload perception reaffirm (RO).

After 2hg CLOCK RELOAD_OR_NEW_CAMPAIGN_LIKELY: brief ≤45s PATH200 + OG50
walkback to reaffirm land can-feed on new campaign clock. Fold 2hg CLOCK
into §6f. NO midflight / no oi≠0 poll / no Post / never 5x / no speed write.
"""
from __future__ import annotations

import json
import struct
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hh_post_reload_perception.json"
SUMMARY = ROOT / "reports" / "phase2hh_summary.json"
DOC = ROOT / "docs" / "PHASE2HH_POST_RELOAD_PERCEPTION.md"

PATH_S = 45.0
GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
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


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = i32(b, gs + 0x478)
    hours = i32(b, gs + 0x484)
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
    clock_class = (
        "RELOAD_OR_NEW_CAMPAIGN_LIKELY"
        if isinstance(hours, int) and hours < 100
        else "CLOCK_OBSERVED"
    )
    return {
        "pid": pid,
        "hours": hours,
        "year_at_0x478": year,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "clock_class": clock_class,
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": tag,
        "scenario": "ITA post-reload ≤45s PATH200+OG50 (no Post, no midflight, no oi≠0 poll)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def load_gm():
    path = ROOT / "scripts" / "phase2gm_carmy_path_instance_ro.py"
    src = path.read_text(encoding="utf-8")
    marker = '\nif __name__ == "__main__":'
    if marker in src:
        src = src.split(marker)[0]
    mod = types.ModuleType("phase2gm_helpers_hh")
    mod.__file__ = str(path)
    sys.modules["phase2gm_helpers_hh"] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


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


def patch_docs(meta, result, path_snap, walk):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hg `CLOCK_RELOAD_RING_SEQ_POLISH`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hh `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    # refresh PATH200 / OG50MI live gates in §6f if present
    import re

    t = re.sub(
        r"\| `PATH200` \| multi-prov candidates \| CArmy`\+0x200` tag-FP \(not demangled dest\) — LIVE[^\n]*\|\n",
        f"| `PATH200` | multi-prov candidates | CArmy`+0x200` tag-FP — LIVE 2hh "
        f"nonempty={path_snap.get('movement_dest_nonempty_count')} "
        f"multi={path_snap.get('multi_province_cand_count')} |\n",
        t,
        count=1,
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` \(MI VT `0x29d6fb8`\) — walkback LIVE[^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — walkback "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} (2hh post-reload) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hh** | `{result}` | Post-reload ≤45s PATH200+OG50; 2hg CLOCK fold | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hh** |" not in t and "| **2hg** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hg** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hh post-reload perception:** result=`{result}` · "
        f"carmy={path_snap.get('carmy_rows')} nonempty={path_snap.get('movement_dest_nonempty_count')} "
        f"multi={path_snap.get('multi_province_cand_count')} · "
        f"walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
        f"clock={meta.get('clock_class')} hours={meta.get('hours')} UI={meta.get('ui_date')} · "
        f"allow_post=False.\n"
    )
    if "**2hh post-reload perception:**" not in t and "**2hg clock+seq polish:**" in t:
        idx = t.find("**2hg clock+seq polish:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hg · CLOCK + ring seq polish · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hh · post-reload PATH200+OG50 · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hg — checklist polish (CLOSED)",
        "## Phase 2gj … 2hh — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hh | Post-reload ≤45s PATH200+OG50 perception | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hh |" not in t2 and "| 2hg |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hg |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hg — CLOCK + ring seq polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hh — post-reload PATH200+OG50. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hh",
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
    meta0 = live_meta(b, base, pid, tag)

    gm = load_gm()
    path_snap = gm.bounded_path_poll(
        b, base, tag, seconds=PATH_S, interval=getattr(gm, "PATH_INTERVAL_S", 2.0)
    )
    walk = og50_walkback(b, base)
    meta1 = live_meta(b, base, pid, tag)

    w_ok = walk["walkback_ok"]
    w_fail = walk["walkback_fail"]
    path_ok = isinstance(path_snap.get("carmy_rows"), int) and path_snap.get("carmy_rows", 0) >= 0
    walk_ok = w_ok > 0 and w_fail == 0
    if path_ok and walk_ok and meta1.get("clock_class") == "RELOAD_OR_NEW_CAMPAIGN_LIKELY":
        result = "POST_RELOAD_PERCEPTION_HIT"
    elif path_ok and walk_ok:
        result = "PERCEPTION_HIT_CLOCK_OTHER"
    else:
        result = "POST_RELOAD_PERCEPTION_PARTIAL"

    report = {
        "phase": "2hh",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "live_start": meta0,
        "path_snapshot": {
            "window_s": PATH_S,
            "carmy_rows": path_snap.get("carmy_rows"),
            "movement_dest_nonempty_count": path_snap.get("movement_dest_nonempty_count"),
            "multi_province_cand_count": path_snap.get("multi_province_cand_count"),
            "poll_ticks": path_snap.get("poll_ticks"),
            "elapsed_s": path_snap.get("elapsed_s"),
        },
        "og50_walkback": walk,
        "sha_base": "5ace558",
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
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hh",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "carmy_rows": path_snap.get("carmy_rows"),
        "path_nonempty": path_snap.get("movement_dest_nonempty_count"),
        "path_multi": path_snap.get("multi_province_cand_count"),
        "poll_ticks": path_snap.get("poll_ticks"),
        "walkback_ok": w_ok,
        "walkback_fail": w_fail,
        "ita_members": walk.get("ita_members"),
        "clock_class": meta1.get("clock_class"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hh post-reload perception); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": "5ace558",
        "semantics": "post-reload ≤45s PATH200+OG50; no oi≠0 poll; no midflight; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hh — Post-reload perception (PATH200 + OG50)",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Path (≤{PATH_S:.0f}s):** carmy={path_snap.get('carmy_rows')} · "
                f"nonempty={path_snap.get('movement_dest_nonempty_count')} · "
                f"multi={path_snap.get('multi_province_cand_count')} · "
                f"ticks={path_snap.get('poll_ticks')}",
                "",
                f"**OG+0x50 walkback:** {w_ok}/{w_ok + w_fail} · ita_members={walk.get('ita_members')}",
                "",
                f"**CLOCK:** class={meta1.get('clock_class')} · hours={meta1.get('hours')} · "
                f"year@+0x478={meta1.get('year_at_0x478')} · UI={meta1.get('ui_date')} "
                f"(2hg: reload≠wrap; hours=UI source)",
                "",
                f"**Live:** pid {meta1['pid']} · drain={meta1['drain']} exec={meta1['exec']} · "
                f"pending={meta1['pending']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** After campaign reload, reaffirm land can-feed "
                "(LOCATE/PATH200/OG50MI/CLOCK). No midflight / no oi≠0 poll / no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hh · 2026-10-31 Asia/Shanghai · sha_base 5ace558*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta1, result, path_snap, walk)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
