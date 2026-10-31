#!/usr/bin/env python3
"""Phase 2hd: SAFE_POST / PHASE2HC §6f pointer polish (RO).

ONE slice. Fold §6f agent card into SAFE_POST pointer section + expand
PHASE2HC doc pointers. Optional instant live snapshot (meta + OG50 +
family FN/factory reaffirm). NO midflight. No Post / never 5x / no recipe.
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

OUT = ROOT / "reports" / "phase2hd_safepost_6f_pointers.json"
SUMMARY = ROOT / "reports" / "phase2hd_summary.json"
DOC = ROOT / "docs" / "PHASE2HD_SAFEPOST_6F_POINTERS.md"
PHASE2HC = ROOT / "docs" / "PHASE2HC_AGENT_READINESS_CONSOLIDATE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0

SAFE_SECTION = """## Agent card pointer — LAND_POST §6f (2hc/2hd)

**Canonical card:** `docs/LAND_POST_READINESS.md` §6f (Phase 2hc).  
**Gate:** CLOSED. `allow_post` False. No recipe execute. Never 5x. Do not ask user to right-click.

### Can feed today (RO IDs)

| ID | Signal |
| --- | --- |
| `LOCATE` / `PATH200` / `INST7088` | CArmy locate · `+0x200` candidates · Instance`+0x70`/`+0x88` |
| `OG50MI` | OG`+0x50` ≡ CArmy`+0xB8` (MI VT `0x29d6fb8`) walkback |
| `ASSIGN51` | Assign units type=51 → CArmy (oi often 0) |
| `FACTORY` / `FN_VT` | factory_idx MATCH + live VT`+0x48`/`+0x50` FN MATCH (2ha/2hb) |
| `CLOCK` | hours/UI/pending/stage/drain/exec |

### HARD_DENY (do not invent)

| ID | Gate |
| --- | --- |
| `MIDFLIGHT` / `NAMED_DEST` | HONEST_EMPTY — stop non-interactive midflight re-poll |
| `ASSIGN_OI` | QUIET until plan-dense oi≠0 |
| `RING` / `POST` / `SPEED5X` | STUBBED / HARD_DENY / NEVER |

### Human-gated (unchanged — still CLOSED)

```
[ ] A  CMove midflight hex OR Strategic-only + human SAFE Post for ring_embed
[ ] B  Ring-embed recreate proof
[ ] C  Human CLAUSEWITZ_ALLOW_POST=1 for ONE experiment
[ ] D  Tool-gate + NEVER_POST
[ ] E  ONE land Post @1x; verify; pause; unset
```

Docs: `docs/PHASE2HC_AGENT_READINESS_CONSOLIDATE.md`, `docs/PHASE2HD_SAFEPOST_6F_POINTERS.md`.

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
    return {"name": name, "factory_match": fac_ok, "fn_match": fn_ok, "both": fac_ok and fn_ok}


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
            else:
                fail += 1
    return {
        "proxy": "OG+0x50[i] == CArmy+0xB8 (VT 0x29d6fb8)",
        "walkback_ok": ok,
        "walkback_fail": fail,
        "ita_members": ita,
        "handle_type_army": HANDLE_TYPE_ARMY,
    }


def patch_docs(meta, result, fam, walk):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hc `AGENT_READINESS_ONE_SUMMARY`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hd `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row = (
        f"| **2hd** | `{result}` | SAFE_POST §6f pointer + PHASE2HC expand; live "
        f"move/assign FN+factory + OG50 "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hd** |" not in t and "| **2hc** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hc** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hd SAFE_POST §6f pointers:** result=`{result}` · move_family={fam['move_family_all']} · "
        f"assign_family={fam['assign_family_all']} · walkback "
        f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hd SAFE_POST §6f pointers:**" not in t:
        # prefer after 2hc live line under §6f
        marker = "**2hc live:**"
        if marker in t:
            idx = t.find(marker)
            eol = t.find("\n", idx)
            if eol != -1:
                t = t[: eol + 1] + note + t[eol + 1 :]
        elif "**2hc readiness consolidate:**" in t:
            idx = t.find("**2hc readiness consolidate:**")
            eol = t.find("\n", idx)
            if eol != -1:
                t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hc · ONE agent-facing readiness consolidate · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hd · SAFE_POST §6f pointers · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    if "## Agent card pointer — LAND_POST §6f (2hc/2hd)" not in t2:
        # Insert before phase polish section
        anchor = "## Phase 2gj … 2hc — checklist polish (CLOSED)"
        if anchor in t2:
            t2 = t2.replace(anchor, SAFE_SECTION + "---\n\n" + anchor)
        else:
            t2 = t2.rstrip() + "\n\n" + SAFE_SECTION
    t2 = t2.replace(
        "## Phase 2gj … 2hc — checklist polish (CLOSED)",
        "## Phase 2gj … 2hd — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hd | SAFE_POST §6f agent-card pointer + PHASE2HC expand | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hd |" not in t2 and "| 2hc |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hc |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hc — ONE agent readiness consolidate. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hd — SAFE_POST §6f pointers. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    # top-of-file catalog pointer polish
    if "§6f agent card" not in t2[:800]:
        t2 = t2.replace(
            "Catalog consolidate: `docs/LAND_POST_READINESS.md` (Phase 2gi).",
            "Catalog consolidate: `docs/LAND_POST_READINESS.md` (Phase 2gi + **§6f agent card** 2hc/2hd).",
        )
    safe.write_text(t2, encoding="utf-8")

    # Expand PHASE2HC with §6f pointer table
    hc = PHASE2HC.read_text(encoding="utf-8") if PHASE2HC.exists() else ""
    pointer_block = "\n".join(
        [
            "",
            "## LAND_POST §6f pointer (2hd)",
            "",
            "Canonical agent card: `docs/LAND_POST_READINESS.md` §6f.",
            "SAFE_POST mirror: `docs/SAFE_POST_ENABLE_CHECKLIST.md` → **Agent card pointer — LAND_POST §6f**.",
            "",
            "| Topic | Where |",
            "| --- | --- |",
            "| Session RO constants | LAND_POST §1 + §6f |",
            "| Factory + VT FN MATCH tables | LAND_POST §2 + §6f (2ha/2hb) |",
            "| Can-feed IDs (`LOCATE`…`CLOCK`) | LAND_POST §6f / SAFE_POST agent card |",
            "| HARD_DENY IDs | LAND_POST §4 + §6f / SAFE_POST |",
            "| Human-gated A–E | LAND_POST §5 + §6f / SAFE_POST Exact next |",
            "| Recipes (DESIGN ONLY) | `reports/phase2fb_ring_embed_recipe.json`, `phase2gk_ring_embed_recipe_v2.json` — never execute |",
            "",
            f"**2hd live reaffirm:** `{result}` · move_family={fam['move_family_all']} · "
            f"assign_family={fam['assign_family_all']} · walkback "
            f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']} · "
            f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.",
            "",
        ]
    )
    if "## LAND_POST §6f pointer (2hd)" not in hc:
        hc = hc.rstrip() + "\n" + pointer_block
        PHASE2HC.write_text(hc + "\n", encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x SAFE_POST §6f pointer polish (no Post, no midflight)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hd",
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
        result = "SAFEPOST_6F_POINTERS_POLISH"
    elif fam["all_families"]:
        result = "SAFEPOST_6F_POINTERS_OG50_PARTIAL"
    else:
        result = "SAFEPOST_6F_POINTERS_PARTIAL"

    report = {
        "phase": "2hd",
        "result": result,
        "allow_post": False,
        "live": meta,
        "families": fam,
        "og50": walk,
        "pointers": {
            "land_post_section": "6f",
            "safepost_agent_card": True,
            "phase2hc_expanded": True,
        },
        "semantics": "SAFE_POST §6f pointer + PHASE2HC expand; live FN/factory+OG50; no midflight; no Post",
        "sha_base": "d879da0",
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
        "phase": "2hd",
        "result": result,
        "allow_post": False,
        "live": meta,
        "move_family_all": fam["move_family_all"],
        "assign_family_all": fam["assign_family_all"],
        "walkback_ok": walk["walkback_ok"],
        "walkback_fail": walk["walkback_fail"],
        "safepost_6f_pointer": True,
        "phase2hc_expanded": True,
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hd SAFE_POST §6f pointers); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": "d879da0",
        "semantics": "SAFE_POST §6f pointers + PHASE2HC; live reaffirm; no midflight",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hd — SAFE_POST §6f pointer polish",
                "",
                f"**Result:** `{result}`",
                "",
                "**Pointers:**",
                "- Canonical card: `docs/LAND_POST_READINESS.md` §6f",
                "- SAFE_POST: **Agent card pointer — LAND_POST §6f (2hc/2hd)**",
                "- Expanded: `docs/PHASE2HC_AGENT_READINESS_CONSOLIDATE.md` § pointer table",
                "",
                f"**Live reaffirm:** move_family={fam['move_family_all']} · "
                f"assign_family={fam['assign_family_all']} · walkback "
                f"{walk['walkback_ok']}/{walk['walkback_ok']+walk['walkback_fail']}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"pending={meta['pending']} stage={meta['stage_count']} · allow_post=False",
                "",
                "**Semantics:** Catalog-only fold of §6f into SAFE_POST + PHASE2HC pointers. "
                "Instant live FN/factory+OG50. No midflight / no Post / never 5x.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hd · 2026-10-31 Asia/Shanghai · sha_base d879da0*",
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
