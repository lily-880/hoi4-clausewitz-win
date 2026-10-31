#!/usr/bin/env python3
"""Phase 2gs: Perception + readiness catalog polish (RO).

ONE slice. No Post / no ALLOW_POST / never 5x / no recipe execute.
A) Consolidate CArmy+0x200, OG+0x50≡CArmy+0xB8, Instance+0x70/+0x88,
   Assign units type=51 into LAND_POST perception section; ≤60s path snapshot.
B) SAFE_POST + LAND_POST readiness deltas 2gp–2gr (catalog-only).
"""
from __future__ import annotations

import importlib.util
import json
import struct
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gs_perception_readiness.json"
SUMMARY = ROOT / "reports" / "phase2gs_summary.json"
DOC = ROOT / "docs" / "PHASE2GS_PERCEPTION_READINESS.md"

PATH_S = 60.0
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


def load_gm():
    path = ROOT / "scripts" / "phase2gm_carmy_path_instance_ro.py"
    src = path.read_text(encoding="utf-8")
    # Only strip the module __main__ guard (phase2gm also mentions __name__ inside helpers).
    marker = '\nif __name__ == "__main__":'
    if marker in src:
        src = src.split(marker)[0]
    else:
        marker2 = "\nif __name__ == '__main__':"
        if marker2 in src:
            src = src.split(marker2)[0]
    mod = types.ModuleType("phase2gm_helpers")
    mod.__file__ = str(path)
    sys.modules["phase2gm_helpers"] = mod
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


def prior_catalog():
    """Consolidate proven perception facts from prior phase summaries (no re-churn)."""
    return {
        "carmy_plus_200": {
            "off": "0x200",
            "role": "multi-province path candidate after tag-FP filter (2gm)",
            "2gm": "multi=2 after filter; best_candidate_off=0x200",
            "2gn": "NO_OVERLAP vs Instance+0x70/+0x88 (3 multi × 57 shaped)",
            "2go": "named movement_dest HONEST_EMPTY — do not invent dest",
            "note": "NOT army midflight movement_dest demangle; NOT Instance order path",
        },
        "instance_70_88": {
            "plus_70": "ordered u32 province ids for order/front path (NOT army midflight)",
            "plus_88": "CPdxArray<CProvince*> hub/neighbor over +0x70 prefix",
            "2gm_seed": "ok=14; +0x70 shaped=8; +0x88 CProvince hit",
            "2gn": "+0x200 ⊀ +0x70 (overlap=0)",
        },
        "og50_mi_membership": {
            "proxy": "COrdersGroup+0x50[i] == CArmy+0xB8",
            "mi_vt": "0x29d6fb8",
            "2gp": "walkback 292/292; Assign units type=51 ix 410/445 → ITA CArmy tag=15",
            "2gq": "294/294 quiet Assign oi≠0",
            "2gr": "375/375 (oi 1..127) dense Assign still quiet",
            "demangled_name": "STUBBED",
        },
        "assign_units_type_51": {
            "handle_type": HANDLE_TYPE_ARMY,
            "layout": "CPdxArray@Assign+0x28 size@+0x34 stride8 {u32 type,u32 index}",
            "order_index": "Assign+0x48; oi=0 unset ≠ valid OI (2gp sight); oi≠0 unconfirmed (2gq/2gr quiet)",
            "resolve": "resolve_handle(type=51, ix) → CArmy*; cross MI@+0xB8 ∈ OG+0x50",
        },
    }


def patch_land_post(live, path_snap, walk):
    p = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = p.read_text(encoding="utf-8")
    section = f"""
## 6b. Perception map (2gm–2gs consolidate — RO only)

| Layer | Proven | Semantics / ceiling |
| --- | --- | --- |
| `CArmy+0x200` | 2gm multi after tag-FP; 2gn **NO_OVERLAP** vs Instance`+0x70`/`+0x88` | Multi-prov **candidate** only — **not** demangled `movement_dest`; **not** order path |
| Instance`+0x70` / `+0x88` | ordered u32 provinces / `CProvince*` hub (2gm seed) | Order/front path — **≠** army midflight dest |
| **OG+0x50 ≡ CArmy+0xB8** | MI VT `0x29d6fb8`; walkback **{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}** (2gs live; was 375 @2gr) | Membership **proxy** — demangled +0x50 name **STUBBED** |
| Assign units type=`{HANDLE_TYPE_ARMY}` | 2gp: ix 410/445 → ITA CArmy tag=15; oi@`+0x48` | oi=0 unset; **oi≠0 units↔OI** quiet through 2gq/2gr dense |
| Named `movement_dest` | 2go PE **HONEST_EMPTY** | Do not invent |

**2gs live path snapshot (≤{PATH_S:.0f}s @1x):** carmy_rows={path_snap.get('carmy_rows')} nonempty={path_snap.get('movement_dest_nonempty_count')} multi={path_snap.get('multi_province_cand_count')} ticks={path_snap.get('poll_ticks')} hours={live.get('hours')} UI={live.get('ui_date')} allow_post=False.

"""
    if "## 6b. Perception map" in t:
        # replace existing 6b through next ## 
        import re
        t = re.sub(
            r"\n## 6b\. Perception map.*?(?=\n## |\Z)",
            "\n" + section.lstrip("\n"),
            t,
            count=1,
            flags=re.S,
        )
    else:
        # insert after §6 block (before ## 7)
        marker = "## 7. Live RO snapshot"
        if marker not in t:
            raise SystemExit("LAND_POST missing §7 marker")
        t = t.replace(marker, section + marker, 1)

    t = t.replace(
        "**2gm–2gr perception:** `CArmy+0x200` multi (tag-FP). **2gn:** no +0x200↔+0x70 overlap. **2go:** named `movement_dest` **HONEST_EMPTY**. **2gp–2gr:** **OG+0x50 ≡ CArmy+0xB8** MI membership (walkback **375/375**). **2gq/2gr A:** Assign oi≠0 confirm **quiet** (dense clock+heap still empty).\n\n**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later plan-dense Assign oi≠0 window; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        "**2gm–2gs perception (see §6b):** `CArmy+0x200` multi (tag-FP) ⊀ Instance`+0x70`; named dest empty; **OG+0x50 ≡ CArmy+0xB8** walkback live; Assign type=51 resolve proven; Assign oi≠0 **quiet** through dense 2gr.\n\n**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later plan-dense Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    old_row = "| **2gr** | `ASSIGN_QUIET_DENSE_OG50_CATALOG_POLISH` | Clock nudge 205→206 + ≤90s pending/heap Assign oi≠0 **quiet**; B walkback **375/375** (oi 1..127) | oi≠0 units↔OI unconfirmed; Post/ring HARD_DENY |\n"
    new_row = old_row + "| **2gs** | `PERCEPTION_READINESS_CATALOG_POLISH` | §6b perception map; ≤60s path snapshot; OG50 walkback reaffirm; SAFE_POST 2gp–2gr deltas | Post/ring HARD_DENY; oi≠0 still open |\n"
    if old_row in t and "| **2gs** |" not in t:
        t = t.replace(old_row, new_row)
    t = t.replace(
        "*Phase 2gr · denser Assign oi≠0 quiet + OG50 catalog 375/375 · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gs · perception+readiness catalog polish · 2026-10-31 Asia/Shanghai*",
    )
    p.write_text(t, encoding="utf-8")


def patch_safe_post():
    p = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        "## Phase 2gj … 2gr — checklist polish (CLOSED)",
        "## Phase 2gj … 2gs — checklist polish (CLOSED)",
    )
    old = "| 2gr | denser Assign oi≠0 (clock nudge + heap edge); B catalog polish | **QUIET** on A; walkback 375/375 (Post still CLOSED) |\n"
    new = old + "| 2gs | perception §6b + readiness catalog; ≤60s path snapshot | **DOCS/RO polish** (Post still CLOSED) |\n"
    if old in t and "| 2gs |" not in t:
        t = t.replace(old, new)
    t = t.replace(
        "*Phase 2gr — denser Assign oi≠0 quiet + catalog 375/375. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gs — perception+readiness catalog polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    p.write_text(t, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x perception+readiness catalog polish (no Post)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gs",
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

    gm = load_gm()
    # force ≤60s window
    path_snap = gm.bounded_path_poll(b, base, tag, seconds=PATH_S, interval=getattr(gm, "PATH_INTERVAL_S", 2.0))
    walk = og50_walkback(b, base)
    meta1 = live_meta(b, base, pid, tag, scenario)
    catalog = prior_catalog()

    result = "PERCEPTION_READINESS_CATALOG_POLISH"
    next_b = (
        "NON-Post: perception catalog consolidated — human midflight CMove hex / SAFE Post "
        "for ring_embed OR later plan-dense Assign oi≠0; push when GitHub reachable; "
        "still NO ALLOW_POST"
    )
    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk",
        f"≤{PATH_S:.0f}s path snapshot carmy={path_snap.get('carmy_rows')} nonempty={path_snap.get('movement_dest_nonempty_count')} multi={path_snap.get('multi_province_cand_count')}",
        f"OG+0x50 MI walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
        "LAND_POST §6b perception map + SAFE_POST 2gs row",
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
        "Capstone/121 re-churn",
    ]

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gs",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "live_start": meta0,
        "live_end": meta1,
        "path_snapshot": {
            "window_s": PATH_S,
            "carmy_rows": path_snap.get("carmy_rows"),
            "movement_dest_nonempty_count": path_snap.get("movement_dest_nonempty_count"),
            "multi_province_cand_count": path_snap.get("multi_province_cand_count"),
            "tag_singleton_fps_filtered": path_snap.get("tag_singleton_fps_filtered"),
            "poll_ticks": path_snap.get("poll_ticks"),
            "elapsed_s": path_snap.get("elapsed_s"),
            "armies_sample": (path_snap.get("armies_sample") or [])[:8],
        },
        "og50_walkback": walk,
        "perception_catalog": catalog,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "2d17a16",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2gs",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "path_nonempty": path_snap.get("movement_dest_nonempty_count"),
        "path_multi": path_snap.get("multi_province_cand_count"),
        "carmy_rows": path_snap.get("carmy_rows"),
        "walkback_ok": walk["walkback_ok"],
        "walkback_fail": walk["walkback_fail"],
        "next_shortest_blocker": next_b,
        "sha_base": "2d17a16",
        "semantics": (
            f"§6b catalog; path nonempty={path_snap.get('movement_dest_nonempty_count')} "
            f"multi={path_snap.get('multi_province_cand_count')}; "
            f"walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gs — Perception + readiness catalog polish (RO)",
                "",
                f"**Result:** `{result}`",
                f"**Live:** pid {meta1['pid']} · {meta1['ui_date']} · hours={meta1['hours']} · tag={tag} · @1x",
                f"**Path snapshot:** ≤{PATH_S:.0f}s · carmy={path_snap.get('carmy_rows')} · nonempty={path_snap.get('movement_dest_nonempty_count')} · multi={path_snap.get('multi_province_cand_count')} · ticks={path_snap.get('poll_ticks')}",
                f"**OG+0x50 MI walkback:** {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
                "",
                "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**",
                "",
                "## Consolidated perception (see LAND_POST §6b)",
                "",
                "- `CArmy+0x200` multi candidate (tag-FP) — ⊀ Instance`+0x70`/`+0x88`",
                "- Instance`+0x70`/`+0x88` = order/front path (not midflight dest)",
                "- **OG+0x50 ≡ CArmy+0xB8** membership proxy (VT `0x29d6fb8`)",
                "- Assign units type=51 → CArmy; oi@`+0x48` ≠0 still unconfirmed",
                "- Named `movement_dest` HONEST_EMPTY",
                "",
                "## Works / stubbed",
                "",
                "- Works: §6b map; ≤60s path RO; walkback reaffirm; SAFE_POST 2gs",
                "- Stubbed: demangled +0x50; named dest; ring_embed; Post; Assign oi≠0 HIT",
                "",
                "**Next shortest blocker (NON-Post):** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; push when GitHub reachable; still **NO ALLOW_POST**.",
                "",
                "Script: `scripts/phase2gs_perception_readiness_polish.py`",
                "Reports: `reports/phase2gs_perception_readiness.json`, `reports/phase2gs_summary.json`",
                "",
                f"*Phase 2gs · {sh} Asia/Shanghai*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_land_post(meta1, path_snap, walk)
    patch_safe_post()

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
                "path": {
                    "carmy": path_snap.get("carmy_rows"),
                    "nonempty": path_snap.get("movement_dest_nonempty_count"),
                    "multi": path_snap.get("multi_province_cand_count"),
                    "ticks": path_snap.get("poll_ticks"),
                },
                "walkback": f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
