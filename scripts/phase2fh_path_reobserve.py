#!/usr/bin/env python3
"""Phase 2fh: bounded ETH@1x path-vector re-observe (+ optional Cancel/SupportAttack leaf sight).

No Post. No tool-gate. No 2fb recipe. allow_post stays False. Never 5x.
Window caps: path poll <=90s; leaf sight <=30s if paths stay empty.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import army_subjects
import cmd_layout
import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2fh_path_reobserve.json"
SUMMARY = ROOT / "reports" / "phase2fh_summary.json"
DOC = ROOT / "docs" / "PHASE2FH_PATH_REOBSERVE.md"

CA_VT_RVA = 0x29D6D68
ETH_TAG = 15
PATH_WINDOW_S = 75.0
PATH_INTERVAL_S = 2.0
LEAF_WINDOW_S = 30.0
LEAF_INTERVAL_S = 0.05

LEAF_WATCH = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    cmd_layout.SUPPORT_ATTACK["vt"]: "CSupportAttackCommand",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderUnassignCommand"]["vt"]: "COrderUnassignCommand",
    0x2A2D538: "CCancelRunningAwayCommand",
    0x29F3710: "CHourlyTickCommand",
}
LEAF_FOCUS = {
    "CCancelMovementCommand",
    "CSupportAttackCommand",
    "CMoveCommand",
    "CStrategicRedeploymentCommand",
    "CCancelRunningAwayCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def looks_like_province_id(v: int) -> bool:
    return 1 <= v <= 20000


def read_u32_vector(b, begin, end, cap, max_n=64):
    if not begin or not end or end < begin:
        return None
    nbytes = end - begin
    if nbytes % 4 != 0 or nbytes > max_n * 4:
        return None
    if cap and cap < end:
        return None
    blob = try_read(b, begin, nbytes)
    if not blob or len(blob) != nbytes:
        return None
    return list(struct.unpack("<" + "I" * (nbytes // 4), blob))


def live_meta(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ETH@1x bounded path re-observe (no Post)",
        "country_tag_filter": ETH_TAG,
    }


def carmy_rows(b, base):
    rows = army_subjects.iter_armies_by_index(b, base, 1000, 1400, country_tag=ETH_TAG)
    vt_want = base + CA_VT_RVA
    out = []
    for r in rows:
        vt = try_u64(b, r["army"])
        if vt == vt_want and r.get("handle_ok") and r.get("province_id_ok"):
            out.append(r)
    return out


def scan_army_paths(b, base, rows):
    hits = []
    nonempty = 0
    for r in rows:
        obj = r["army"]
        blob = try_read(b, obj, 0x800) or b""
        cands = []
        for off in range(0x40, min(len(blob) - 24, 0x780), 8):
            begin, end, cap = struct.unpack_from("<QQQ", blob, off)
            if begin < 0x10000 or end < begin:
                continue
            vals = read_u32_vector(b, begin, end, cap, max_n=32)
            if not vals or not all(looks_like_province_id(v) for v in vals):
                continue
            # nonempty path = more than current-province echo alone preferred, but keep multi or non-echo
            cands.append({
                "off": hex(off),
                "n": len(vals),
                "province_ids": vals,
                "matches_current_only": vals == [r["province_id"]],
            })
        useful = [c for c in cands if not c["matches_current_only"] or c["n"] > 1]
        # count nonempty if any candidate (including current-only single) — prefer useful
        status_cands = useful if useful else cands
        if status_cands:
            nonempty += 1
            hits.append({
                "index": r["index"],
                "handle": list(r["handle"]),
                "province_id": r["province_id"],
                "army": hex(obj),
                "vector_cands": status_cands[:6],
                "dest_guess": (status_cands[0]["province_ids"][-1]
                               if status_cands and status_cands[0]["province_ids"] else None),
                "note": "candidate only; not invented",
            })
    return {"nonempty_count": nonempty, "hits": hits, "carmy_rows": len(rows)}


def bounded_path_poll(b, base, seconds=PATH_WINDOW_S, interval=PATH_INTERVAL_S):
    t0 = time.time()
    polls = 0
    best = {"nonempty_count": 0, "hits": [], "carmy_rows": 0}
    first_hit_at = None
    timeline = []
    while True:
        elapsed = time.time() - t0
        if elapsed > seconds:
            break
        rows = carmy_rows(b, base)
        snap = scan_army_paths(b, base, rows)
        polls += 1
        timeline.append({
            "poll": polls,
            "t": round(elapsed, 2),
            "nonempty": snap["nonempty_count"],
            "carmy": snap["carmy_rows"],
        })
        if snap["nonempty_count"] > best["nonempty_count"]:
            best = snap
            if first_hit_at is None:
                first_hit_at = round(elapsed, 2)
            # early stop once we have useful multi-province hits
            useful = [h for h in snap["hits"] if any(
                (not c.get("matches_current_only")) or c.get("n", 0) > 1
                for c in h.get("vector_cands") or []
            )]
            if useful:
                best = {**snap, "hits": useful, "nonempty_count": len(useful)}
                break
        time.sleep(interval)
    return {
        "window_s": seconds,
        "interval_s": interval,
        "polls": polls,
        "elapsed_s": round(min(time.time() - t0, seconds + interval), 2),
        "first_hit_at_s": first_hit_at,
        "best_nonempty_count": best.get("nonempty_count", 0),
        "best_hits": best.get("hits", [])[:12],
        "timeline_tail": timeline[-8:],
        "note": "BOUNDED; stopped early on useful hit or at window end. No invent.",
    }


def sample_stage_pending(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = struct.unpack("<I", b.read(sess + post_abi.CSession_STAGE_COUNT, 4))[0]
    hits = []
    seen = set()
    cur = pending_h
    while cur and cur not in seen and len(hits) < 64:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        rva = vt - base
        name = LEAF_WATCH.get(rva, f"UNK_{rva:#x}")
        hits.append({"source": "pending", "addr": hex(cur), "vt_rva": hex(rva), "name": name})
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
            rva = vt - base
            name = LEAF_WATCH.get(rva, f"UNK_{rva:#x}")
            hits.append({"source": f"stage[{i}]", "addr": hex(ptr), "vt_rva": hex(rva), "name": name})
    return hits


def leaf_sight(b, base, seconds=LEAF_WINDOW_S, interval=LEAF_INTERVAL_S):
    t0 = time.time()
    sight = {}
    samples = []
    polls = 0
    while time.time() - t0 < seconds:
        polls += 1
        for h in sample_stage_pending(b, base):
            name = h["name"]
            sight[name] = sight.get(name, 0) + 1
            if name in LEAF_FOCUS and len(samples) < 16:
                addr = int(h["addr"], 16)
                blob = try_read(b, addr, 0x88)
                samples.append({
                    **h,
                    "poll": polls,
                    "t": round(time.time() - t0, 2),
                    "hex_head": blob.hex() if blob else None,
                    "hex_len": len(blob) if blob else 0,
                })
        time.sleep(interval)
    focus_hits = [s for s in samples if s["name"] in LEAF_FOCUS]
    return {
        "window_s": seconds,
        "interval_s": interval,
        "polls": polls,
        "sight_counts": sight,
        "focus_samples": focus_hits[:12],
        "focus_names_seen": sorted({s["name"] for s in focus_hits}),
        "note": "BOUNDED leaf sight only if path vectors empty. No Post.",
    }


def write_doc(rep: dict) -> None:
    live = rep.get("live") or {}
    path = rep.get("path_poll") or {}
    leaf = rep.get("leaf_sight")
    lines = [
        "# Phase 2fh — bounded ETH path-vector re-observe",
        "",
        f"**Result:** `{rep.get('result')}`  ",
        "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**",
        "",
        "## Path poll (bounded)",
        "",
        f"- window **{path.get('window_s')}s** · polls {path.get('polls')} · elapsed {path.get('elapsed_s')}s",
        f"- nonempty armies: **{path.get('best_nonempty_count')}**",
        f"- first_hit_at: {path.get('first_hit_at_s')}",
        "",
    ]
    hits = path.get("best_hits") or []
    if hits:
        lines += ["### Hits", ""]
        for h in hits[:8]:
            lines.append(
                f"- army idx {h.get('index')} handle {h.get('handle')} "
                f"prov {h.get('province_id')} dest_guess {h.get('dest_guess')} "
                f"cands={len(h.get('vector_cands') or [])}"
            )
        lines.append("")
    else:
        lines += ["Honest empty — no invent.", ""]
    if leaf:
        lines += [
            "## Leaf sight (fallback)",
            "",
            f"- window {leaf.get('window_s')}s · focus seen: {leaf.get('focus_names_seen')}",
            f"- samples: {len(leaf.get('focus_samples') or [])}",
            "",
        ]
    lines += [
        "## Live",
        "",
        "```json",
        json.dumps(live, indent=2),
        "```",
        "",
        f"**Next shortest blocker (NON-Post):** {rep.get('next_shortest_blocker')}",
        "",
        "Script: `scripts/phase2fh_path_reobserve.py`",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    assert allow_post() is False
    pid = find_pid()
    live = {"pid": pid}
    path = {"best_nonempty_count": 0, "best_hits": [], "polls": 0, "note": "no live"}
    leaf = None
    err = None
    if not pid:
        err = "no hoi4 pid"
    else:
        try:
            b = Backend(pid)
            base = int(b.image_base)
            live = live_meta(b, base, pid)
            path = bounded_path_poll(b, base)
            if path.get("best_nonempty_count", 0) == 0:
                leaf = leaf_sight(b, base)
            # refresh date after windows
            live = live_meta(b, base, pid)
        except Exception as e:
            err = str(e)

    nonempty = path.get("best_nonempty_count", 0)
    leaf_focus = (leaf or {}).get("focus_names_seen") or []
    if nonempty > 0:
        result = "PATH_VECTOR_NONEMPTY_BOUNDED"
    elif leaf and leaf_focus:
        result = "PATH_EMPTY_LEAF_HEX_SIGHT"
    elif leaf is not None:
        result = "PATH_EMPTY_LEAF_SIGHT_EMPTY"
    else:
        result = "PATH_REOBSERVE_PARTIAL"

    if nonempty > 0:
        next_blocker = (
            "NON-Post: decode nonempty path-vector offsets into CArmy field map "
            "OR SupportAttack/Cancel leaf hex if sighted — still NO ALLOW_POST"
        )
    elif leaf_focus:
        next_blocker = (
            "NON-Post: decode leaf hex layout for "
            + ",".join(leaf_focus)
            + " (RO only) — still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: RO ceiling on midflight path/leaf this window — next cheapest: "
            "pause+1x war-dense relaunch observe OR catalog-only retreat/attack field polish; "
            "still NO ALLOW_POST"
        )

    works = [
        f"bounded path poll {PATH_WINDOW_S:.0f}s @ {PATH_INTERVAL_S:.0f}s",
        f"nonempty path armies: {nonempty}",
        "allow_post stays False; recipe not executed",
    ]
    if leaf is not None:
        works.append(f"fallback leaf sight {LEAF_WINDOW_S:.0f}s focus={leaf_focus}")

    rep = {
        "phase": "2fh",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "error": err,
        "live": live,
        "path_poll": path,
        "leaf_sight": leaf,
        "works": works,
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live leaf" if "CMoveCommand" not in leaf_focus else "ordinary CMove live leaf (seen in sight — decode deferred)",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
        ],
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "aedb230",
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2fh",
                "result": result,
                "scenario": live.get("scenario", "ETH@1x"),
                "allow_post": False,
                "tool_gate": "CLOSED",
                "pid": live.get("pid"),
                "ui_date": live.get("ui_date"),
                "hours": live.get("hours"),
                "path_nonempty": nonempty,
                "path_polls": path.get("polls"),
                "path_elapsed_s": path.get("elapsed_s"),
                "leaf_focus_seen": leaf_focus,
                "works": works,
                "stubbed": rep["stubbed"],
                "next_shortest_blocker": next_blocker,
                "parent_sha_base": "aedb230",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_doc(rep)
    print(json.dumps(json.loads(SUMMARY.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
