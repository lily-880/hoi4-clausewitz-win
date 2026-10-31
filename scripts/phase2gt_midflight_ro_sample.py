#!/usr/bin/env python3
"""Phase 2gt: Non-interactive midflight RO sample (no user right-click).

ONE RO slice. No Post / no ALLOW_POST / never 5x / no recipe execute.
A) ≤90s pending/stage + bounded heap-edge for CMove / SupportAttack / Cancel /
   Assign(oi≠0). Document hits or honest empty.
B) Agent-facing LAND_POST summary of what perception can/can't feed today.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gt_midflight_ro_sample.json"
SUMMARY = ROOT / "reports" / "phase2gt_summary.json"
DOC = ROOT / "docs" / "PHASE2GT_MIDFLIGHT_RO_SAMPLE.md"

OBSERVE_S = 90.0
POLL_SLEEP = 0.04
HEAP_MB = 24
HEAP_MAX_HITS = 8
HEAP_SCANS_CAP = 4
HEAP_EVERY_S = 15.0
GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35

FOCUS = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    cmd_layout.SUPPORT_ATTACK["vt"]: "CSupportAttackCommand",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderUnassignCommand"]["vt"]: "COrderUnassignCommand",
}
LEAF_MOVE = {"CMoveCommand", "CSupportAttackCommand", "CStrategicRedeploymentCommand"}
CANCEL = {"CCancelMovementCommand"}
ASSIGN = {"COrderAssignCommand", "COrderUnassignCommand"}


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


def decode_assign(b, base, addr, name):
    units_data = try_u64(b, addr + 0x28)
    units_size = try_u32(b, addr + 0x34) or 0
    units = []
    if units_data and 0 < units_size <= 64:
        blob = try_read(b, units_data, units_size * 8)
        if blob:
            for j in range(units_size):
                typ, ix = struct.unpack_from("<II", blob, j * 8)
                units.append({"type": typ, "index": ix})
    oi = try_u32(b, addr + 0x48)
    return {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex((try_u64(b, addr) or 0) - base),
        "order_index": oi,
        "units_size": units_size,
        "units": units[:8],
    }


def decode_moveish(b, base, addr, name):
    """Minimal leaf dump — hex head for midflight proof, no Post."""
    head = try_read(b, addr, 0x88)
    action = try_u64(b, addr + 0x28)
    return {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex((try_u64(b, addr) or 0) - base),
        "action_embed": hex(action) if action else None,
        "hex_head_88": head.hex() if head else None,
        "size_hint": "0x88" if name == "CMoveCommand" else ("0x50" if name == "CStrategicRedeploymentCommand" else None),
    }


def decode_cmd(b, base, addr, name):
    if name in ASSIGN:
        return decode_assign(b, base, addr, name)
    return decode_moveish(b, base, addr, name)


def walk_pending_stage(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    counters = {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "stage_count": scount,
        "pending_nonzero": 1 if pending_h else 0,
    }
    hits = []
    seen = set()
    cur = pending_h
    while cur and cur not in seen and len(hits) < 80:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = FOCUS.get(vt - base)
        if name:
            hits.append({"source": "pending", **decode_cmd(b, base, cur, name)})
        nxt = try_u64(b, cur + 8)
        if not nxt or nxt == cur:
            break
        cur = nxt
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            name = FOCUS.get(vt - base)
            if name:
                hits.append({"source": f"stage[{i}]", **decode_cmd(b, base, ptr, name)})
    return hits, counters


def heap_edge(b, base, mb_limit=HEAP_MB, max_hits=HEAP_MAX_HITS):
    needles = {name: struct.pack("<Q", base + vt) for vt, name in FOCUS.items()}
    found, scanned = [], 0
    try:
        from mem import Proc

        src = Proc(find_pid("hoi4.exe") or find_pid())
        if not hasattr(src, "regions"):
            return {"ok": False, "error": "no regions", "found": [], "scanned_mb": 0}
        for m in src.regions(writable=True, min_size=0x1000):
            start_m, end_m = m["start"], m["end"]
            if base <= start_m < base + 0x4000000:
                continue
            pos = start_m
            while pos < end_m and scanned < (mb_limit << 20) and len(found) < max_hits:
                n = min(1 << 20, end_m - pos)
                data = None
                if hasattr(src, "try_read"):
                    data = src.try_read(pos, n)
                if data is None:
                    try:
                        data = src.read(pos, n)
                    except Exception:
                        data = None
                scanned += n
                if data:
                    for name, needle in needles.items():
                        j = 0
                        while j < len(data) and len(found) < max_hits:
                            k = data.find(needle, j)
                            if k < 0:
                                break
                            addr = pos + k
                            try:
                                found.append(
                                    {"source": "heap_edge", **decode_cmd(b, base, addr, name)}
                                )
                            except Exception as e:
                                found.append(
                                    {
                                        "source": "heap_edge",
                                        "addr": hex(addr),
                                        "name": name,
                                        "error": str(e),
                                    }
                                )
                            j = k + 8
                pos += n
            if len(found) >= max_hits:
                break
        return {"ok": True, "found": found, "scanned_mb": round(scanned / (1 << 20), 2)}
    except Exception as e:
        return {"ok": False, "error": str(e), "found": [], "scanned_mb": 0}


def classify_captures(captures):
    by = Counter(c.get("name") for c in captures)
    move_hex = [
        c
        for c in captures
        if c.get("name") in LEAF_MOVE and c.get("hex_head_88") and not c.get("error")
    ]
    cancel_hex = [
        c for c in captures if c.get("name") in CANCEL and c.get("hex_head_88") and not c.get("error")
    ]
    assign_nz = [
        c
        for c in captures
        if c.get("name") == "COrderAssignCommand" and (c.get("order_index") or 0) != 0
    ]
    assign_z = [
        c
        for c in captures
        if c.get("name") == "COrderAssignCommand" and (c.get("order_index") or 0) == 0
    ]
    return {
        "by_name": dict(by),
        "move_hex_n": len(move_hex),
        "cancel_hex_n": len(cancel_hex),
        "assign_oi_nonzero_n": len(assign_nz),
        "assign_oi_zero_n": len(assign_z),
        "move_hex_sample": move_hex[:3],
        "cancel_hex_sample": cancel_hex[:2],
        "assign_nz_sample": assign_nz[:3],
    }


def agent_facing_summary(cls, path_note="(see 2gs §6b)"):
    return {
        "can_feed_today": [
            "CArmy locate via handle type=51 + country_tag",
            "CArmy+0x200 multi-prov path *candidates* (tag-FP filtered; not demangled dest)",
            "Instance+0x70/+0x88 order/front province maps (≠ midflight dest)",
            "OG+0x50 ≡ CArmy+0xB8 membership proxy (VT 0x29d6fb8)",
            "Assign units type=51 → CArmy resolve (when Assign sighted; oi often 0)",
            "Live hours/UI date, pending/stage/drain/exec counters (RO)",
        ],
        "cannot_feed_today": [
            "Ordinary CMove midflight hex (bit_identical rebuild) — still empty without human/AI leave",
            "Named movement_dest demangle",
            "Assign units↔OI when order_index≠0 (quiet through 2gq/2gr/2gt)",
            "ring_embed / Dummy recreate in-process (needs SAFE Post)",
            "Any Post / tool-gate / recipe execute",
        ],
        "this_window": cls,
        "path_note": path_note,
    }


def patch_docs(live, result, cls, agent):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    summary_blk = f"""
## 6c. Agent-facing perception summary (2gt)

**What land agent can read RO today (no Post):**
{chr(10).join('- ' + x for x in agent['can_feed_today'])}

**What is still blocked / honest-empty:**
{chr(10).join('- ' + x for x in agent['cannot_feed_today'])}

**2gt midflight sample:** result=`{result}` · move_hex={cls['move_hex_n']} · cancel_hex={cls['cancel_hex_n']} · assign_oi≠0={cls['assign_oi_nonzero_n']} · live hours={live.get('hours')} UI={live.get('ui_date')} · allow_post=False.

"""
    if "## 6c. Agent-facing" in t:
        import re

        t = re.sub(
            r"\n## 6c\. Agent-facing.*?(?=\n## |\Z)",
            "\n" + summary_blk.lstrip("\n"),
            t,
            count=1,
            flags=re.S,
        )
    else:
        marker = "## 7. Live RO snapshot"
        if marker not in t:
            raise SystemExit("LAND_POST missing §7")
        t = t.replace(marker, summary_blk + marker, 1)

    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later plan-dense Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed (2gt non-interactive still empty) OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    old = "| **2gs** | `PERCEPTION_READINESS_CATALOG_POLISH` | §6b perception map; ≤60s path snapshot; OG50 walkback reaffirm; SAFE_POST 2gp–2gr deltas | Post/ring HARD_DENY; oi≠0 still open |\n"
    new = old + f"| **2gt** | `{result}` | ≤90s non-interactive midflight RO (CMove/SA/Cancel/Assign); §6c agent-facing summary | midflight hex / oi≠0 still open; Post HARD_DENY |\n"
    if old in t and "| **2gt** |" not in t:
        t = t.replace(old, new)
    t = t.replace(
        "*Phase 2gs · perception+readiness catalog polish · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gt · midflight RO sample + agent-facing summary · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2gs — checklist polish (CLOSED)",
        "## Phase 2gj … 2gt — checklist polish (CLOSED)",
    )
    old2 = "| 2gs | perception §6b + readiness catalog; ≤60s path snapshot | **DOCS/RO polish** (Post still CLOSED) |\n"
    new2 = old2 + f"| 2gt | ≤90s non-interactive midflight RO + §6c agent summary | **{result}** (Post still CLOSED) |\n"
    if old2 in t2 and "| 2gt |" not in t2:
        t2 = t2.replace(old2, new2)
    t2 = t2.replace(
        "*Phase 2gs — perception+readiness catalog polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gt — midflight RO sample + agent summary. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x non-interactive midflight RO ≤90s (no Post, no right-click)"
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2gt",
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

    t0 = time.time()
    polls = 0
    sight = Counter()
    captures = []
    seen = set()
    last_counters = None
    heap_scans = 0
    heap_meta = []
    last_heap_t = 0.0
    last_exec = meta0.get("exec")

    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = walk_pending_stage(b, base)
        for h in hits:
            name = h.get("name") or "?"
            sight[name] += 1
            key = (name, h.get("addr"), h.get("source"))
            if key in seen:
                continue
            seen.add(key)
            captures.append(h)

        now = time.time()
        exec_now = (last_counters or {}).get("exec")
        exec_moved = exec_now is not None and last_exec is not None and exec_now != last_exec
        if exec_now is not None:
            last_exec = exec_now
        due = (now - last_heap_t) >= HEAP_EVERY_S
        if heap_scans < HEAP_SCANS_CAP and (heap_scans == 0 or exec_moved or due):
            hr = heap_edge(b, base)
            heap_scans += 1
            last_heap_t = now
            heap_meta.append(
                {
                    "poll": polls,
                    "t": round(now - t0, 2),
                    "ok": hr.get("ok"),
                    "scanned_mb": hr.get("scanned_mb"),
                    "n_found": len(hr.get("found") or []),
                    "error": hr.get("error"),
                }
            )
            for h in hr.get("found") or []:
                if not h.get("name"):
                    continue
                sight[h["name"] + ":heap"] += 1
                key = (h["name"], h.get("addr"), "heap_edge")
                if key in seen:
                    continue
                seen.add(key)
                captures.append(h)

        # early stop on valuable midflight
        cls_tmp = classify_captures(captures)
        if cls_tmp["move_hex_n"] >= 1 or cls_tmp["assign_oi_nonzero_n"] >= 1:
            if cls_tmp["move_hex_n"] >= 1 and cls_tmp["assign_oi_nonzero_n"] >= 1:
                break
            if cls_tmp["move_hex_n"] >= 2 or cls_tmp["assign_oi_nonzero_n"] >= 2:
                break
        time.sleep(POLL_SLEEP)

    observe_s = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, pid, tag, scenario)
    cls = classify_captures(captures)

    if cls["move_hex_n"] and cls["assign_oi_nonzero_n"]:
        result = "MIDFLIGHT_MOVE_AND_ASSIGN_OI_NONZERO_HIT"
    elif cls["move_hex_n"]:
        result = "MIDFLIGHT_MOVE_HEX_HIT"
    elif cls["cancel_hex_n"] and not cls["move_hex_n"]:
        result = "MIDFLIGHT_CANCEL_ONLY"
    elif cls["assign_oi_nonzero_n"]:
        result = "MIDFLIGHT_ASSIGN_OI_NONZERO_HIT"
    elif any(c.get("name") in ASSIGN for c in captures):
        result = "MIDFLIGHT_ASSIGN_OI_ZERO_OR_PARTIAL"
    elif captures:
        result = "MIDFLIGHT_SIGHT_PARTIAL"
    else:
        result = "MIDFLIGHT_HONEST_EMPTY"

    agent = agent_facing_summary(cls)
    next_b = (
        "NON-Post: human midflight CMove hex / SAFE Post for ring_embed "
        "(2gt non-interactive empty) OR later plan-dense Assign oi≠0; push when "
        "GitHub reachable; still NO ALLOW_POST"
        if result == "MIDFLIGHT_HONEST_EMPTY"
        else (
            "NON-Post: midflight HIT this window — catalog hex / oi≠0 into rebuild path "
            "OR SAFE Post for ring_embed; push when GitHub reachable; still NO ALLOW_POST"
        )
    )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk; no ask right-click",
        f"≤{observe_s}s pending/stage+heap midflight polls={polls} heap_scans={heap_scans}",
        f"captures={len(captures)} by={dict(cls['by_name'])}",
        f"move_hex={cls['move_hex_n']} cancel_hex={cls['cancel_hex_n']} assign_oi≠0={cls['assign_oi_nonzero_n']}",
        "LAND_POST §6c agent-facing summary",
    ]
    stubbed = [
        "demangled OG+0x50 / MI field name",
        "named movement_dest",
        "ring_embed execute",
        "2fb/2gk recipe execute",
        "ALLOW_POST / CLAUSEWITZ_ALLOW_POST",
        "tool-gate open",
        "Post inject",
        "ask-user right-click",
        "Capstone/121 re-churn",
    ]
    if not cls["move_hex_n"]:
        stubbed.append("ordinary CMove midflight hex this window")
    if not cls["assign_oi_nonzero_n"]:
        stubbed.append("Assign oi≠0 units↔OI this window")

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gt",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "asked_user_right_click": False,
        "result": result,
        "live_start": meta0,
        "live_end": meta1,
        "observe_s": observe_s,
        "polls": polls,
        "sight_counts": dict(sight),
        "captures_n": len(captures),
        "captures_sample": captures[:12],
        "classified": cls,
        "heap_scans": heap_scans,
        "heap_meta": heap_meta,
        "last_counters": last_counters,
        "agent_facing": agent,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "caa6ed0",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "phase": "2gt",
        "result": result,
        "allow_post": False,
        "live": meta1,
        "observe_s": observe_s,
        "polls": polls,
        "captures_n": len(captures),
        "move_hex": cls["move_hex_n"],
        "cancel_hex": cls["cancel_hex_n"],
        "assign_oi_nonzero": cls["assign_oi_nonzero_n"],
        "heap_scans": heap_scans,
        "next_shortest_blocker": next_b,
        "sha_base": "caa6ed0",
        "semantics": (
            f"midflight move_hex={cls['move_hex_n']} cancel={cls['cancel_hex_n']} "
            f"assign_oi≠0={cls['assign_oi_nonzero_n']}; §6c agent summary"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gt — Non-interactive midflight RO sample",
                "",
                f"**Result:** `{result}`",
                f"**Live:** pid {meta1['pid']} · {meta1['ui_date']} · hours={meta1['hours']} · tag={tag} · @1x",
                f"**Observe:** {observe_s}s · polls={polls} · heap_scans={heap_scans} · captures={len(captures)}",
                f"**Hits:** move_hex={cls['move_hex_n']} · cancel_hex={cls['cancel_hex_n']} · assign_oi≠0={cls['assign_oi_nonzero_n']}",
                "",
                "**allow_post:** **False** · no ask right-click · never 5x · recipes **NOT executed**",
                "",
                "## Method",
                "",
                "Pending/stage + bounded heap-edge for CMove / SupportAttack / Cancel / Assign.",
                "No user interaction; no Post.",
                "",
                "## Agent-facing (LAND_POST §6c)",
                "",
                "Can feed: army locate, +0x200 candidates, Instance+0x70/+0x88, OG+0x50 MI proxy, Assign type=51 resolve when sighted.",
                "Cannot: CMove bit_identical hex (if empty), named dest, Assign oi≠0, ring_embed, Post.",
                "",
                f"**Next:** {next_b}",
                "",
                "Script: `scripts/phase2gt_midflight_ro_sample.py`",
                f"*Phase 2gt · {sh} Asia/Shanghai*",
                "",
            ]
        ),
        encoding="utf-8",
    )
    patch_docs(meta1, result, cls, agent)
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
                "observe_s": observe_s,
                "move_hex": cls["move_hex_n"],
                "cancel_hex": cls["cancel_hex_n"],
                "assign_oi_nonzero": cls["assign_oi_nonzero_n"],
                "captures": len(captures),
                "heap_scans": heap_scans,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
