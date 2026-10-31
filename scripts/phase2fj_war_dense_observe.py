#!/usr/bin/env python3
"""Phase 2fj: war-dense ETH relaunch @1x + bounded path/leaf RO observe.

Relaunch -start_tag=ETH -start_speed=1 AI-on (no -noai). NEVER 5x.
No Post. No tool-gate. No 2fb recipe. allow_post stays False.
Path window <=75s; leaf <=30s if paths empty. No endless poll.
"""
from __future__ import annotations

import json
import struct
import subprocess
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

OUT = ROOT / "reports" / "phase2fj_war_dense_observe.json"
SUMMARY = ROOT / "reports" / "phase2fj_summary.json"
DOC = ROOT / "docs" / "PHASE2FJ_WAR_DENSE_OBSERVE.md"

CA_VT_RVA = 0x29D6D68
ETH_TAG = 15
PATH_WINDOW_S = 75.0
PATH_INTERVAL_S = 2.0
LEAF_WINDOW_S = 30.0
LEAF_INTERVAL_S = 0.05
MAP_WAIT_S = 180.0

LEAF_WATCH = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    cmd_layout.SUPPORT_ATTACK["vt"]: "CSupportAttackCommand",
    cmd_layout.CANCEL_RUNNING_AWAY["vt"]: "CCancelRunningAwayCommand",
    cmd_layout.WITHDRAW_ARMY_HQ["vt"]: "CWithdrawArmyHqCommand",
    cmd_layout.MASS_CANCEL["vt"]: "CMassCancelMovementCommand",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderUnassignCommand"]["vt"]: "COrderUnassignCommand",
    cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]: "COrderExecuteCommand",
    cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]: "COrderNewFallbackCommand",
    0x29F3710: "CHourlyTickCommand",
}
LEAF_FOCUS = {
    "CCancelMovementCommand",
    "CSupportAttackCommand",
    "CMoveCommand",
    "CStrategicRedeploymentCommand",
    "CCancelRunningAwayCommand",
    "CWithdrawArmyHqCommand",
    "CMassCancelMovementCommand",
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


def live_meta(b, base, pid, scenario: str):
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
        "scenario": scenario,
        "country_tag_filter": ETH_TAG,
        "cmdline_expect": "-gdpr-compliant -start_tag=ETH -start_speed=1",
    }


def relaunch_eth() -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "launch_into_map.py"),
        "--start-tag",
        "ETH",
        "--speed",
        "1",
        "--allow-ai",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "cmd": cmd,
        "rc": r.returncode,
        "stdout": (r.stdout or "")[-600:],
        "stderr": (r.stderr or "")[-300:],
    }


def wait_map(timeout: float = MAP_WAIT_S) -> dict:
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout:
        pid = find_pid()
        if not pid:
            time.sleep(2)
            continue
        try:
            b = Backend(pid)
            base = int(b.image_base)
            # idler name via status helper if present; else hours readable + armies
            ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
            gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
            try:
                gs = u64(b, base + gs_rva)
                hours = i32(b, gs + 0x484)
            except Exception as e:
                last = {"pid": pid, "gs_err": str(e)}
                time.sleep(3)
                continue
            rows = army_subjects.iter_armies_by_index(b, base, 1000, 1400, country_tag=ETH_TAG)
            carmy = 0
            vt_want = base + CA_VT_RVA
            for r in rows:
                vt = try_u64(b, r["army"])
                if vt == vt_want and r.get("handle_ok"):
                    carmy += 1
            last = {"pid": pid, "hours": hours, "eth_rows": len(rows), "carmy": carmy}
            # map ready when hours finite and at least a few ETH armies exist
            if hours is not None and hours >= 0 and carmy >= 3:
                d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
                return {
                    "ok": True,
                    "elapsed_s": round(time.time() - t0, 1),
                    "pid": pid,
                    "hours": hours,
                    "ui_date": d.strftime("%Y-%m-%d %H:00"),
                    "carmy": carmy,
                }
        except Exception as e:
            last = {"error": str(e), "pid": pid}
        time.sleep(3)
    return {"ok": False, "elapsed_s": round(time.time() - t0, 1), "last": last}


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
            cands.append({
                "off": hex(off),
                "n": len(vals),
                "province_ids": vals,
                "matches_current_only": vals == [r["province_id"]],
            })
        useful = [c for c in cands if not c["matches_current_only"] or c["n"] > 1]
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
        "note": "BOUNDED; stop early on useful hit or window end. No invent.",
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
        "note": "BOUNDED leaf sight after empty paths. No Post.",
    }


def main():
    assert allow_post() is False, "allow_post must stay False"
    scenario = "ETH war-dense relaunch @1x AI-on bounded path/leaf (no Post)"

    relaunch = relaunch_eth()
    assert relaunch["rc"] == 0, relaunch

    map_wait = wait_map(MAP_WAIT_S)
    if not map_wait.get("ok"):
        report = {
            "phase": "2fj",
            "result": "RELAUNCH_MAP_WAIT_FAIL",
            "allow_post": False,
            "relaunch": relaunch,
            "map_wait": map_wait,
            "parent_sha_base": "7920ce9",
        }
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        SUMMARY.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return

    # re-attach after relaunch
    time.sleep(1)
    pid = find_pid()
    b = Backend(pid)
    base = int(b.image_base)
    live = live_meta(b, base, pid, scenario)

    path = bounded_path_poll(b, base)
    leaf = None
    if path.get("best_nonempty_count", 0) == 0:
        # refresh backend in case pid same
        pid = find_pid() or pid
        b = Backend(pid)
        base = int(b.image_base)
        leaf = leaf_sight(b, base)
        live = live_meta(b, base, pid, scenario)

    if path.get("best_nonempty_count", 0) > 0:
        result = "PATH_NONEMPTY_WAR_DENSE"
    elif leaf and leaf.get("focus_names_seen"):
        result = "PATH_EMPTY_LEAF_SIGHT_HIT"
    else:
        result = "PATH_EMPTY_LEAF_SIGHT_EMPTY"

    works = [
        "relaunch ETH -start_tag=ETH -start_speed=1 --allow-ai (no -noai)",
        f"map_wait ok={map_wait.get('ok')} elapsed={map_wait.get('elapsed_s')}s carmy={map_wait.get('carmy')}",
        f"bounded path poll {path.get('elapsed_s')}s nonempty={path.get('best_nonempty_count')}",
        "allow_post stays False; recipe not executed; never 5x",
    ]
    if leaf is not None:
        works.append(f"fallback leaf sight {leaf.get('window_s')}s focus={leaf.get('focus_names_seen')}")

    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
    ]
    if path.get("best_nonempty_count", 0) == 0:
        stubbed.append("path-vector nonempty (this war-dense window)")

    if result == "PATH_NONEMPTY_WAR_DENSE":
        next_blocker = (
            "NON-Post: deepen movement_dest field off from nonempty hits OR "
            "SupportAttack/Cancel leaf hex on next midflight; still NO ALLOW_POST"
        )
    elif result == "PATH_EMPTY_LEAF_SIGHT_HIT":
        next_blocker = (
            "NON-Post: deepen leaf hex fields from focus samples OR longer war-dense path "
            "window on fresh ETH/ITA; still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: RO ceiling even on fresh ETH war-start window — next cheapest: "
            "ITA@1x war-dense relaunch OR catalog NewFallback subject beyond +0x54; "
            "still NO ALLOW_POST"
        )

    report = {
        "phase": "2fj",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "result": result,
        "relaunch": relaunch,
        "map_wait": map_wait,
        "live": live,
        "path_poll": path,
        "leaf_sight": leaf,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "7920ce9",
        "haiti_return": {
            "recipe": "python scripts/launch_into_map.py --speed 1 --allow-ai",
            "equiv_cli": "-gdpr-compliant -start_tag=HAI -start_speed=1",
            "paused_cool": "python scripts/launch_into_map.py  # HAI speed 0 -noai",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2fj",
                "result": result,
                "scenario": scenario,
                "allow_post": False,
                "tool_gate": "CLOSED",
                "pid": live["pid"],
                "ui_date": live["ui_date"],
                "hours": live["hours"],
                "path_nonempty": path.get("best_nonempty_count"),
                "path_polls": path.get("polls"),
                "path_elapsed_s": path.get("elapsed_s"),
                "leaf_focus_seen": (leaf or {}).get("focus_names_seen"),
                "map_wait_s": map_wait.get("elapsed_s"),
                "works": works,
                "stubbed": stubbed,
                "next_shortest_blocker": next_blocker,
                "parent_sha_base": "7920ce9",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Phase 2fj — war-dense ETH relaunch observe",
        "",
        f"**Result:** `{result}`  ",
        f"**Base:** `7920ce9` (2fi) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb recipe **NOT executed**",
        "",
        "## Relaunch",
        "",
        "- CLI: `-gdpr-compliant -start_tag=ETH -start_speed=1` (AI on, no `-noai`)",
        f"- map_wait: ok={map_wait.get('ok')} · {map_wait.get('elapsed_s')}s · carmy={map_wait.get('carmy')}",
        "",
        "## Path poll (bounded)",
        "",
        f"- window **{path.get('window_s')}s** · polls {path.get('polls')} · elapsed {path.get('elapsed_s')}s",
        f"- nonempty armies: **{path.get('best_nonempty_count')}**",
        f"- first_hit_at: {path.get('first_hit_at_s')}",
        "",
    ]
    if path.get("best_hits"):
        lines.append("### Hits (honest)")
        lines.append("")
        for h in path["best_hits"][:8]:
            lines.append(
                f"- army idx={h.get('index')} prov={h.get('province_id')} "
                f"handle={h.get('handle')} dest_guess={h.get('dest_guess')} "
                f"cands={len(h.get('vector_cands') or [])}"
            )
        lines.append("")
    else:
        lines.append("Honest empty — no invent.")
        lines.append("")
    if leaf is not None:
        lines += [
            "## Leaf sight (fallback)",
            "",
            f"- window {leaf.get('window_s')}s · focus seen: {leaf.get('focus_names_seen')}",
            f"- sight_counts: `{json.dumps(leaf.get('sight_counts') or {})}`",
            "",
        ]
    lines += [
        "## Live",
        "",
        "```json",
        json.dumps(live, indent=2),
        "```",
        "",
        f"**Next shortest blocker (NON-Post):** {next_blocker}",
        "",
        "Script: `scripts/phase2fj_war_dense_observe.py`",
    ]
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "phase": "2fj",
        "result": result,
        "allow_post": False,
        "pid": live["pid"],
        "ui_date": live["ui_date"],
        "hours": live["hours"],
        "path_nonempty": path.get("best_nonempty_count"),
        "path_polls": path.get("polls"),
        "path_elapsed_s": path.get("elapsed_s"),
        "leaf_focus_seen": (leaf or {}).get("focus_names_seen"),
        "map_wait_s": map_wait.get("elapsed_s"),
        "next_shortest_blocker": next_blocker,
    }, indent=2))


if __name__ == "__main__":
    main()
