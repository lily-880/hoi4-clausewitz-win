#!/usr/bin/env python3
"""Phase 2hc: ONE agent-facing LAND_POST readiness consolidate (RO).

Catalog-only fold of 2ha Assign FN/factory + 2hb MOVE-family FN/factory +
OG50 + perception/can-feed/HARD_DENY into §6f. Optional instant live
snapshot (meta + OG50 + FN/factory reaffirm). NO midflight. No Post /
never 5x / no recipe execute.
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

OUT = ROOT / "reports" / "phase2hc_agent_readiness_consolidate.json"
SUMMARY = ROOT / "reports" / "phase2hc_summary.json"
DOC = ROOT / "docs" / "PHASE2HC_AGENT_READINESS_CONSOLIDATE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0

SECTION_6F = """## 6f. ONE agent-facing readiness summary (2hc)

**Status: CLOSED — allow_post False · tool-gate CLOSED · recipes NOT executed · never 5x.**
Folds §6b–§6e + **2ha** Assign FN/factory + **2hb** MOVE-family FN/factory + OG50 into one land-agent card.

### Proven RO constants (session)

| Symbol | Value |
| --- | --- |
| `G_GAMESTATE` / hours UI | `0x33dd6b0` / GS`+0x484` |
| `G_SESSION` | `0x34ffbe8` |
| pending / stage / drain / exec | server`+0x58` / sess`+0x54` / `+0x60` / `+0x6c8` |
| cmd IsValid / Execute slots | VT`+0x48` / VT`+0x50` |

### Land catalogs — factory + live VT FN MATCH

| Family | factory_idx | factory MATCH | VT+0x48/0x50 FN MATCH | Slice |
| --- | --- | --- | --- | --- |
| MOVE / SA / Cancel / Strategic | 1402 / 3620 / 1415 / 4753 | True | True | 2hb (+2gy) |
| Assign / Unassign / Execute | 3350 / 3365 / 3352 | True | True | 2ha (+2gz) |

Layouts (MATCH, still no Post): Strategic 2fa/2fb; MOVE offline skeleton 2gj; Assign units `CPdxArray@+0x28` stride8 `{type,index}`; oi@`+0x48`.

### What land agent can feed today (RO)

| ID | Signal | How / status |
| --- | --- | --- |
| `LOCATE` | CArmy | handle type=51 + country_tag — HIT 2gp |
| `PATH200` | multi-prov candidates | CArmy`+0x200` tag-FP (not demangled dest) — LIVE |
| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` (⊀ `+0x200`) — HIT 2gm/2gn |
| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` (MI VT `0x29d6fb8`) — walkback LIVE |
| `ASSIGN51` | Assign units→CArmy | type=51 when sighted; oi often 0 — HIT 2gp |
| `FACTORY` | cmd factory slots | MOVE/SA/Cancel/Strat + Assign/Unassign/Execute — MATCH 2gy–2hb |
| `FN_VT` | IsValid/Execute | live VT`+0x48`/`+0x50` ≡ catalog — MATCH 2ha/2hb |
| `CLOCK` | hours/UI/counters | pending/stage/drain/exec — HIT |

### HARD_DENY / do not invent

| ID | Item | Gate |
| --- | --- | --- |
| `MIDFLIGHT` | CMove/SA/Cancel midflight hex | HONEST_EMPTY 2gt+2gv — stop re-poll |
| `NAMED_DEST` | named movement_dest | HONEST_EMPTY 2go |
| `ASSIGN_OI` | Assign units↔OI when oi≠0 | QUIET 2gq–2gx |
| `RING` | ring_embed / Dummy recreate | STUBBED — needs SAFE Post |
| `POST` | Post / tool-gate / 2fb\\|2gk execute | HARD_DENY allow_post=False |
| `OG50NAME` | demangled OG`+0x50` name | STUBBED |
| `SPEED5X` | game speed 5x | NEVER |

### Human-gated next (still CLOSED — do not ask user to right-click / enable Post)

```
[ ] A  Ordinary CMove (+ embed) live midflight hex  — OR Strategic-only + human SAFE Post for ring_embed
[ ] B  Ring-embed recreate proof on captured buffer
[ ] C  Human CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] D  Dedicated tool-gate open + NEVER_POST
[ ] E  ONE land MOVE|Strategic Post @1x; verify; pause; unset
```

Until A–B green and human does C: **gate stays CLOSED**.

"""


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


def check_cmd(b, base, name, cmd, expected_idx):
    ft = cmd_layout.FACTORY_TABLE
    idx_cat = cmd.get("factory_idx")
    slot = try_u64(b, base + ft["rva"] + (idx_cat or 0) * 8)
    slot_rva = ((slot - base) & 0xFFFFFFFF) if slot else 0
    fac_ok = slot_rva == cmd["factory"] and idx_cat == expected_idx
    vt_abs = base + cmd["vt"]
    live_isv = try_u64(b, vt_abs + post_abi.CCommand_VT_ISVALID)
    live_exe = try_u64(b, vt_abs + post_abi.CCommand_VT_EXECUTE)
    isv_rva = ((live_isv - base) & 0xFFFFFFFF) if live_isv else 0
    exe_rva = ((live_exe - base) & 0xFFFFFFFF) if live_exe else 0
    fn_ok = isv_rva == cmd["isvalid"] and exe_rva == cmd["execute"]
    return {
        "name": name,
        "factory_idx": idx_cat,
        "factory_match": fac_ok,
        "fn_match": fn_ok,
        "both": fac_ok and fn_ok,
    }


def snapshot_families(b, base):
    cmds = {
        "MOVE": (cmd_layout.MOVE, 1402),
        "CANCEL": (cmd_layout.CANCEL, 1415),
        "SUPPORT_ATTACK": (cmd_layout.SUPPORT_ATTACK, 3620),
        "STRATEGIC": (cmd_layout.STRATEGIC, 4753),
        "ASSIGN": (cmd_layout.ORDERS["COrderAssignCommand"], 3350),
        "UNASSIGN": (cmd_layout.ORDERS["COrderUnassignCommand"], 3365),
        "EXECUTE": (cmd_layout.ORDERS["COrderExecuteCommand"], 3352),
    }
    rows = {k: check_cmd(b, base, k, c, exp) for k, (c, exp) in cmds.items()}
    move_fam = all(rows[k]["both"] for k in ("MOVE", "CANCEL", "SUPPORT_ATTACK", "STRATEGIC"))
    assign_fam = all(rows[k]["both"] for k in ("ASSIGN", "UNASSIGN", "EXECUTE"))
    return {
        "rows": rows,
        "move_family_all": move_fam,
        "assign_family_all": assign_fam,
        "all_families": move_fam and assign_fam,
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
        "handle_type_army": HANDLE_TYPE_ARMY,
    }


def patch_docs(meta, result, fam, walk):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")

    # Insert §6f before ## 7 if missing
    if "## 6f. ONE agent-facing readiness summary (2hc)" not in t:
        live_line = (
            f"**2hc live:** result=`{result}` · move_family={fam['move_family_all']} · "
            f"assign_family={fam['assign_family_all']} · walkback "
            f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
            f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n\n"
        )
        block = SECTION_6F + live_line
        if "## 7. Live RO snapshot" in t:
            t = t.replace("## 7. Live RO snapshot", block + "## 7. Live RO snapshot")
        elif "## 8. Phase deltas" in t:
            t = t.replace("## 8. Phase deltas", block + "## 8. Phase deltas")

    # Annotate §2 factory note
    old_note = "Factory table live MATCH: ORDERS 26/26 (2fg); STRATEGIC idx 4753 (2fd/2fe); MOVE/CANCEL filled (2fe)."
    new_note = (
        "Factory table live MATCH: ORDERS 26/26 (2fg); STRATEGIC idx 4753 (2fd/2fe); "
        "MOVE/CANCEL filled (2fe). **2ha/2hb live VT+0x48/0x50 FN MATCH** for "
        "Assign/Unassign/Execute + MOVE/SA/Cancel/Strategic; factory 3350/3365/3352 + "
        "1402/3620/1415/4753 reaffirm (2gz–2hb)."
    )
    if old_note in t and "2ha/2hb live VT" not in t:
        t = t.replace(old_note, new_note)

    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hb `MOVE_FAMILY_FN_FACTORY_MATCH`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hc `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )

    row = (
        f"| **2hc** | `{result}` | §6f ONE agent-facing readiness (2ha+2hb FN/factory + "
        f"OG50 + can-feed/HARD_DENY); live walkback "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hc** |" not in t and "| **2hb** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hb** |"):
                out.append(row)
        t = "".join(out)

    note = (
        f"**2hc readiness consolidate:** result=`{result}` · move_family={fam['move_family_all']} · "
        f"assign_family={fam['assign_family_all']} · walkback "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hc readiness consolidate:**" not in t and "**2hb move-family FN:**" in t:
        idx = t.find("**2hb move-family FN:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]

    t = t.replace(
        "*Phase 2hb · MOVE/SA/Cancel/Strategic FN polish · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hc · ONE agent-facing readiness consolidate · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hb — checklist polish (CLOSED)",
        "## Phase 2gj … 2hc — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hc | §6f ONE agent readiness (2ha+2hb FN/factory + OG50 + HARD_DENY) | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hc |" not in t2 and "| 2hb |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hb |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hb — MOVE/SA/Cancel/Strategic FN. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hc — ONE agent readiness consolidate. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x §6f agent readiness consolidate (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hc",
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
    fam = snapshot_families(b, base)
    walk = og50_walkback(b, base)

    if fam["all_families"] and walk["walkback_fail"] == 0 and walk["walkback_ok"] > 0:
        result = "AGENT_READINESS_ONE_SUMMARY"
    elif fam["all_families"]:
        result = "AGENT_READINESS_CATALOG_OG50_PARTIAL"
    else:
        result = "AGENT_READINESS_CATALOG_PARTIAL"

    report = {
        "phase": "2hc",
        "result": result,
        "allow_post": False,
        "live": meta,
        "families": fam,
        "og50": walk,
        "section": "6f",
        "semantics": "§6f ONE agent summary: 2ha+2hb FN/factory + OG50 + can-feed/HARD_DENY; no midflight; no Post",
        "sha_base": "9a68a5f",
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "ask right-click",
            "long midflight empty poll",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hc",
        "result": result,
        "allow_post": False,
        "live": meta,
        "move_family_all": fam["move_family_all"],
        "assign_family_all": fam["assign_family_all"],
        "walkback_ok": walk["walkback_ok"],
        "walkback_fail": walk["walkback_fail"],
        "section_6f": True,
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hc §6f readiness card); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": "9a68a5f",
        "semantics": "§6f ONE agent readiness; FN/factory reaffirm + OG50; no midflight",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hc — ONE agent-facing readiness consolidate",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Families:** move_family_all={fam['move_family_all']} · "
                f"assign_family_all={fam['assign_family_all']}",
                "",
                f"**OG50:** walkback {walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
                f"ita_members={walk['ita_members']}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"pending={meta['pending']} stage={meta['stage_count']} · allow_post=False",
                "",
                "**Semantics:** Catalog §6f folds 2ha Assign FN/factory + 2hb MOVE-family "
                "FN/factory + OG50 + perception/can-feed/HARD_DENY into one agent card. "
                "Instant live reaffirm only. No midflight / no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hc · 2026-10-31 Asia/Shanghai · sha_base 9a68a5f*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, fam, walk)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
