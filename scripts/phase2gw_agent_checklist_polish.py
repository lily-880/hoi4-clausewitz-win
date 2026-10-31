#!/usr/bin/env python3
"""Phase 2gw: Agent-facing LAND_POST checklist polish (RO).

ONE slice. Catalog-only consolidate of 2gu can-feed/HARD_DENY + 2gt/2gv midflight
empty + 2gp–2gr Assign/OG50 + 2gs perception into §6e agent checklist.
Optional ≤60s path + OG50 walkback for live numbers. NO midflight leaf hunt.
No Post / no ALLOW_POST / never 5x / no recipe execute.
"""
from __future__ import annotations

import importlib.util
import json
import re
import struct
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gw_agent_checklist.json"
SUMMARY = ROOT / "reports" / "phase2gw_summary.json"
DOC = ROOT / "docs" / "PHASE2GW_AGENT_CHECKLIST.md"

PATH_S = 60.0
GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_B8 = 0x29D6FB8
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
PRIOR = ("2gp", "2gq", "2gr", "2gs", "2gt", "2gu", "2gv")


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
    marker = '\nif __name__ == "__main__":'
    if marker in src:
        src = src.split(marker)[0]
    else:
        marker2 = "\nif __name__ == '__main__':"
        if marker2 in src:
            src = src.split(marker2)[0]
    mod = types.ModuleType("phase2gm_helpers_gw")
    mod.__file__ = str(path)
    sys.modules["phase2gm_helpers_gw"] = mod
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
    }


def load_priors():
    out = {}
    for ph in PRIOR:
        p = ROOT / "reports" / f"phase{ph}_summary.json"
        if p.exists():
            out[ph] = json.loads(p.read_text(encoding="utf-8"))
    return out


def checklist(priors, path_snap, walk, meta):
    gs = priors.get("2gs") or {}
    gt = priors.get("2gt") or {}
    gv = priors.get("2gv") or {}
    gu = priors.get("2gu") or {}
    return {
        "use_ro_today": [
            {"id": "LOCATE", "item": "Locate CArmy via handle type=51 + country_tag", "gate": "HIT 2gp"},
            {"id": "PATH200", "item": "Read CArmy+0x200 multi-prov candidates (tag-FP; not demangled dest)", "gate": f"LIVE nonempty={path_snap.get('movement_dest_nonempty_count')} multi={path_snap.get('multi_province_cand_count')}"},
            {"id": "INST7088", "item": "Read Instance+0x70/+0x88 order/front maps (≠ midflight; ⊀ +0x200)", "gate": "HIT 2gm/2gn"},
            {"id": "OG50MI", "item": "Membership via OG+0x50 ≡ CArmy+0xB8 (VT 0x29d6fb8)", "gate": f"walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}"},
            {"id": "ASSIGN51", "item": "Resolve Assign units type=51 → CArmy when sighted (oi often 0)", "gate": "HIT 2gp"},
            {"id": "CLOCK", "item": "Read hours/UI/pending/stage/drain/exec", "gate": f"hours={meta.get('hours')} UI={meta.get('ui_date')}"},
        ],
        "do_not_invent": [
            {"id": "MIDFLIGHT", "item": "CMove/SA/Cancel midflight hex for bit_identical rebuild", "gate": f"HONEST_EMPTY 2gt+2gv (move={gv.get('move_hex', gt.get('move_hex', 0))})"},
            {"id": "NAMED_DEST", "item": "Named movement_dest demangle", "gate": "HONEST_EMPTY 2go"},
            {"id": "ASSIGN_OI", "item": "Assign units↔OI when order_index≠0", "gate": f"QUIET 2gq/2gr/2gt/2gv (oi≠0={gv.get('assign_oi_nonzero', 0)})"},
            {"id": "RING", "item": "ring_embed / Dummy recreate in-process", "gate": "STUBBED — needs SAFE Post"},
            {"id": "POST", "item": "Any Post / tool-gate / 2fb|2gk recipe execute", "gate": "HARD_DENY allow_post=False"},
            {"id": "OG50NAME", "item": "Demangled OG+0x50 / MI field name", "gate": "STUBBED"},
        ],
        "midflight_ceiling": {
            "2gt": {"result": gt.get("result"), "hours": (gt.get("live") or {}).get("hours")},
            "2gv": {"result": gv.get("result"), "hours": (gv.get("live") or {}).get("hours")},
            "note": "Non-interactive midflight empty twice — do not re-poll this slice family without human leave or denser war.",
        },
        "feed_ceiling_ref": "LAND_POST §6d (2gu)",
        "can_feed_n_prior": gu.get("can_feed_n"),
        "hard_deny_n_prior": gu.get("hard_deny_n"),
    }


def patch_land_post(meta, path_snap, walk, chk, result):
    p = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = p.read_text(encoding="utf-8")
    use_rows = "\n".join(
        f"| `{x['id']}` | {x['item']} | {x['gate']} |" for x in chk["use_ro_today"]
    )
    deny_rows = "\n".join(
        f"| `{x['id']}` | {x['item']} | {x['gate']} |" for x in chk["do_not_invent"]
    )
    section = f"""
## 6e. Agent checklist — use RO today / do not invent (2gw)

Folds §6b perception + §6c/2gv midflight empty + §6d feed ceiling + 2gp–2gr Assign/OG50.
**Catalog + brief ≤{PATH_S:.0f}s path/walkback only. No midflight leaf hunt. No Post.**

### Use RO today

| ID | Item | Gate |
| --- | --- | --- |
{use_rows}

### Do not invent / HARD_DENY

| ID | Item | Gate |
| --- | --- | --- |
{deny_rows}

**2gw live path (≤{PATH_S:.0f}s @1x):** carmy={path_snap.get('carmy_rows')} nonempty={path_snap.get('movement_dest_nonempty_count')} multi={path_snap.get('multi_province_cand_count')} ticks={path_snap.get('poll_ticks')} · walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · pid={meta.get('pid')} hours={meta.get('hours')} UI={meta.get('ui_date')} allow_post=False.

**Midflight ceiling:** 2gt+2gv both `MIDFLIGHT_HONEST_EMPTY` — stop non-interactive midflight re-polls until human leave or plan-dense Assign window.

"""
    if "## 6e. Agent checklist" in t:
        t = re.sub(
            r"\n## 6e\. Agent checklist.*?(?=\n## |\Z)",
            "\n" + section.lstrip("\n"),
            t,
            count=1,
            flags=re.S,
        )
    else:
        marker = "## 7. Live RO snapshot"
        if marker in t:
            t = t.replace(marker, section.lstrip("\n") + marker, 1)
        else:
            t = t.rstrip() + "\n" + section

    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gv `MIDFLIGHT_HONEST_EMPTY`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gw checklist: midflight ceiling closed for non-interactive); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2gw** | `{result}` | §6e agent checklist (use RO / do not invent); ≤{PATH_S:.0f}s path+walkback; "
        f"no midflight re-poll | midflight hex / oi≠0 / Post HARD_DENY |\n"
    )
    if "| **2gw** |" not in t and "| **2gv** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2gv** |"):
                out.append(row)
        t = "".join(out)
    t = t.replace(
        "*Phase 2gv · midflight RO reaffirm · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gw · agent checklist catalog polish · 2026-10-31 Asia/Shanghai*",
    )
    p.write_text(t, encoding="utf-8")


def patch_safe_post(result):
    p = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        "## Phase 2gj … 2gv — checklist polish (CLOSED)",
        "## Phase 2gj … 2gw — checklist polish (CLOSED)",
    )
    row = (
        f"| 2gw | §6e agent checklist + ≤60s path/walkback; no midflight re-poll | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2gw |" not in t and "| 2gv |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2gv |"):
                out.append(row)
        t = "".join(out)
    t = t.replace(
        "*Phase 2gv — midflight RO reaffirm. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gw — agent checklist catalog polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    p.write_text(t, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x agent checklist polish + ≤60s path/walkback (no Post, no midflight)"
    priors = load_priors()
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gw",
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
    path_snap = gm.bounded_path_poll(
        b, base, tag, seconds=PATH_S, interval=getattr(gm, "PATH_INTERVAL_S", 2.0)
    )
    walk = og50_walkback(b, base)
    meta1 = live_meta(b, base, pid, tag, scenario)
    chk = checklist(priors, path_snap, walk, meta1)

    result = "AGENT_CHECKLIST_CATALOG_POLISH"
    next_b = (
        "NON-Post: agent checklist ready — human midflight CMove hex / SAFE Post "
        "for ring_embed OR later plan-dense Assign oi≠0; push when GitHub reachable; "
        "still NO ALLOW_POST"
    )
    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk; no midflight leaf hunt",
        f"≤{PATH_S:.0f}s path snapshot carmy={path_snap.get('carmy_rows')} nonempty={path_snap.get('movement_dest_nonempty_count')} multi={path_snap.get('multi_province_cand_count')}",
        f"OG+0x50 MI walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
        "LAND_POST §6e agent checklist + SAFE_POST 2gw row",
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
        "another long midflight empty poll",
    ]

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gw",
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
        "path_snapshot": {
            "window_s": PATH_S,
            "carmy_rows": path_snap.get("carmy_rows"),
            "movement_dest_nonempty_count": path_snap.get("movement_dest_nonempty_count"),
            "multi_province_cand_count": path_snap.get("multi_province_cand_count"),
            "poll_ticks": path_snap.get("poll_ticks"),
            "elapsed_s": path_snap.get("elapsed_s"),
        },
        "og50_walkback": walk,
        "checklist": chk,
        "prior_keys": sorted(priors.keys()),
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "be13d55",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2gw",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "path_nonempty": path_snap.get("movement_dest_nonempty_count"),
        "path_multi": path_snap.get("multi_province_cand_count"),
        "carmy_rows": path_snap.get("carmy_rows"),
        "walkback_ok": walk["walkback_ok"],
        "walkback_fail": walk["walkback_fail"],
        "use_ro_n": len(chk["use_ro_today"]),
        "do_not_invent_n": len(chk["do_not_invent"]),
        "next_shortest_blocker": next_b,
        "sha_base": "be13d55",
        "semantics": (
            f"§6e checklist; path nonempty={path_snap.get('movement_dest_nonempty_count')} "
            f"multi={path_snap.get('multi_province_cand_count')}; "
            f"walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}; no midflight"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gw — Agent checklist catalog polish (RO)",
                "",
                f"**Result:** `{result}`",
                f"**Live:** pid {meta1['pid']} · {meta1['ui_date']} · hours={meta1['hours']} · tag={tag} · @1x",
                f"**Path:** ≤{PATH_S:.0f}s · carmy={path_snap.get('carmy_rows')} · nonempty={path_snap.get('movement_dest_nonempty_count')} · multi={path_snap.get('multi_province_cand_count')}",
                f"**OG+0x50 walkback:** {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
                f"**Checklist:** use_ro={len(chk['use_ro_today'])} · do_not_invent={len(chk['do_not_invent'])}",
                "",
                "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · no midflight leaf hunt · 2fb/2gk **NOT executed**",
                "",
                "## See LAND_POST §6e",
                "",
                "Use RO today: LOCATE / PATH200 / INST7088 / OG50MI / ASSIGN51 / CLOCK",
                "Do not invent: MIDFLIGHT / NAMED_DEST / ASSIGN_OI / RING / POST / OG50NAME",
                "",
                "**Midflight ceiling:** 2gt+2gv both empty — no further non-interactive midflight re-polls this family.",
                "",
                f"**Next:** {next_b}",
                "",
                "Script: `scripts/phase2gw_agent_checklist_polish.py`",
                "Reports: `reports/phase2gw_agent_checklist.json`, `reports/phase2gw_summary.json`",
                "",
                f"*Phase 2gw · {sh} Asia/Shanghai*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_land_post(meta1, path_snap, walk, chk, result)
    patch_safe_post(result)

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
                "use_ro_n": len(chk["use_ro_today"]),
                "do_not_invent_n": len(chk["do_not_invent"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
