#!/usr/bin/env python3
"""Phase 2ew: tighten MOVE-VT edge-burst + Cancel-edge heap scan (RO, NO Post).

One focused attempt on live ITA@1x (or whatever hoi4 is running).
- High-frequency stage/pending poll for leaf MOVE VTs
- On drain/exec/seq edge: large burst (no sleep)
- On CCancelMovementCommand sight: immediate small writable-heap scan for MOVE needles
Never Posts. Never 5x. Bounded observe then stop.

Usage:
  python scripts/phase2ew_move_burst.py --seconds 150
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
sys.path.insert(0, str(ROOT / "scripts"))

import cmd_layout
import post_abi
from process import Backend, find_pid

# reuse dump helpers from midflight watcher
import phase2bm_midflight_ready as mf

OUT = ROOT / "reports" / "phase2ew_move_burst.json"
SUMMARY = ROOT / "reports" / "phase2ew_summary.json"
CAPTURE = ROOT / "reports" / "phase2ew_leaf_move_capture.json"

# Leaf MOVE focus (short-lived)
MOVE_FOCUS = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.MOVE["action"]["vt"]: "CUnitMoveAction",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.STRATEGIC["action"]["vt"]: "CUnitStrategicMoveAction",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    0x2A2C848: "CMassMoveCommand",
    0x2A0FC40: "CMassCancelMovementCommand",
}
_sa = getattr(cmd_layout, "SUPPORT_ATTACK", None)
if isinstance(_sa, dict) and _sa.get("vt"):
    MOVE_FOCUS[_sa["vt"]] = "CSupportAttackCommand"

LEAF_MOVE_NAMES = {
    "CMoveCommand",
    "CUnitMoveAction",
    "CSupportAttackCommand",
    "CMassMoveCommand",
    "CStrategicRedeploymentCommand",
    "CUnitStrategicMoveAction",
}
CANCEL_NAMES = {"CCancelMovementCommand", "CMassCancelMovementCommand"}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def kill_watchers():
    import subprocess

    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'phase2bm_midflight_ready' -and $_.CommandLine -notmatch 'phase2ew_move' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)


def sample_move_focus(b, base, sess, server):
    """RO pass: pending + stage for MOVE_FOCUS VTs only (+ record all WATCH via mf for cancel)."""
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    seq = u32(b, server + 0xD0)
    counters = {"drain": drain, "exec": exec_c, "seq": seq, "stage_count": scount}
    hits = []

    def consider(ptr, source):
        vt = try_u64(b, ptr)
        if vt is None:
            return
        rva = vt - base
        name = MOVE_FOCUS.get(rva) or mf.WATCH.get(rva)
        if not name:
            return
        # Only keep move-focus + cancel + assign family for edge triggers
        keep = name in LEAF_MOVE_NAMES or name in CANCEL_NAMES or name in (
            "COrderAssignCommand",
            "COrderUnassignCommand",
            "CHourlyTickCommand",
        )
        if not keep and name not in MOVE_FOCUS.values():
            return
        try:
            hits.append({"source": source, **mf.dump_cmd(b, base, ptr, name)})
        except Exception as e:
            hits.append({"source": source, "addr": hex(ptr), "name": name, "error": str(e)})

    # pending list
    cur, seen = pending_h, set()
    while cur and cur not in seen and len(seen) < 64:
        seen.add(cur)
        consider(cur, "pending")
        nxt = try_u64(b, cur + 8)
        if not nxt or nxt == cur:
            break
        cur = nxt

    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if ptr:
                consider(ptr, f"stage[{i}]")

    return hits, counters


def heap_scan_move(b, base, mb_limit=64, max_hits=6):
    """Small RO writable-heap scan for leaf MOVE needles only."""
    needles = {
        name: struct.pack("<Q", base + vt)
        for vt, name in MOVE_FOCUS.items()
        if name in LEAF_MOVE_NAMES or name in CANCEL_NAMES
    }
    found, scanned = [], 0
    try:
        from mem import Proc

        src = Proc(find_pid("hoi4.exe"))
        if not hasattr(src, "regions"):
            return {"ok": False, "error": "no regions", "found": []}
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
                        j = data.find(needle)
                        if j >= 0:
                            addr = pos + j
                            try:
                                found.append(
                                    {
                                        "source": "heap_cancel_edge",
                                        "scanned_mb": scanned >> 20,
                                        **mf.dump_cmd(b, base, addr, name),
                                    }
                                )
                            except Exception as e:
                                found.append(
                                    {
                                        "source": "heap_cancel_edge",
                                        "addr": hex(addr),
                                        "name": name,
                                        "error": str(e),
                                    }
                                )
                pos += n
            if len(found) >= max_hits:
                break
        return {"ok": True, "scanned_mb": scanned >> 20, "found": found}
    except Exception as e:
        return {"ok": False, "error": str(e), "found": []}


def live_hours(b, base):
    try:
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        # top-level G_GAMESTATE is RVA; pointer then +0x484 hours
        gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
        gs = u64(b, base + gs_rva)
        hours = u32(b, gs + 0x484)
        from datetime import date, timedelta

        d = date(1936, 1, 1) + timedelta(days=hours // 24)
        return {"hours": hours, "ui_date": f"{d.isoformat()} {hours % 24:02d}:00", "gs": hex(gs)}
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--burst", type=int, default=48, help="extra samples per edge")
    ap.add_argument("--heap-mb", type=int, default=48, help="Cancel-edge heap scan budget MB")
    ap.add_argument("--no-kill-watcher", action="store_true")
    args = ap.parse_args()

    if not args.no_kill_watcher:
        kill_watchers()
        time.sleep(0.5)

    pid = find_pid("hoi4.exe")
    if not pid:
        print(json.dumps({"error": "no hoi4"}))
        return 1
    b = Backend(pid)
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)

    vt_candidates = {
        name: hex(vt)
        for vt, name in sorted(MOVE_FOCUS.items(), key=lambda kv: kv[1])
    }
    recipe = {
        "poll": "pending+stage every ~0ms busy loop with counter edge detect",
        "burst_on_edge": args.burst,
        "cancel_edge_heap": f"on Cancel sight: scan up to {args.heap_mb}MB writable heap for MOVE needles",
        "vt_candidates": vt_candidates,
        "leaf_names": sorted(LEAF_MOVE_NAMES),
        "note": "RO only; allow_post False; never 5x",
    }

    t0 = time.time()
    polls = 0
    edge_events = 0
    burst_samples = 0
    heap_scans = 0
    sight_counts = {}
    sight_first = {}
    leaf_hits = []
    cancel_hits = []
    heap_results = []
    prev = None
    last_counters = None

    while time.time() - t0 < args.seconds:
        polls += 1
        hits, last_counters = sample_move_focus(b, base, sess, server)
        edge = False
        if prev is not None:
            edge = (
                last_counters["drain"] != prev["drain"]
                or last_counters["exec"] != prev["exec"]
                or last_counters["seq"] != prev["seq"]
            )
        if edge:
            edge_events += 1
            for _ in range(args.burst):
                burst_samples += 1
                h2, c2 = sample_move_focus(b, base, sess, server)
                last_counters = c2
                hits.extend(h2)
                if any(h.get("name") in LEAF_MOVE_NAMES for h in h2):
                    break
        prev = dict(last_counters)

        saw_cancel = False
        for h in hits:
            name = h.get("name") or "?"
            sight_counts[name] = sight_counts.get(name, 0) + 1
            if name not in sight_first:
                sight_first[name] = {
                    "source": h.get("source"),
                    "addr": h.get("addr"),
                    "vt_rva": h.get("vt_rva"),
                    "poll": polls,
                    "counters": dict(last_counters),
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            if name in LEAF_MOVE_NAMES:
                leaf_hits.append(h)
            if name in CANCEL_NAMES:
                cancel_hits.append(h)
                saw_cancel = True

        if saw_cancel and heap_scans < 8:
            heap_scans += 1
            hr = heap_scan_move(b, base, mb_limit=args.heap_mb)
            heap_results.append({"poll": polls, "counters": dict(last_counters), **hr})
            for f in hr.get("found") or []:
                if f.get("name") in LEAF_MOVE_NAMES:
                    leaf_hits.append(f)

        if leaf_hits:
            break  # stop early on first leaf Move

    date_info = live_hours(b, base)
    true_leaf = [h for h in leaf_hits if h.get("name") in LEAF_MOVE_NAMES]
    # de-dupe by addr
    seen_a, uniq = set(), []
    for h in true_leaf:
        a = h.get("addr")
        if a in seen_a:
            continue
        seen_a.add(a)
        uniq.append(h)

    result = "LEAF_MOVE_CAPTURED" if uniq else "NO_LEAF_MOVE_AFTER_TIGHT_BURST"
    report = {
        "phase": "2ew",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "scenario": "ITA@1x (keep live process)",
        "pid": pid,
        "date": date_info,
        "observe_seconds": round(time.time() - t0, 1),
        "polls": polls,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "heap_scans_on_cancel": heap_scans,
        "sight_counts": sight_counts,
        "sight_first": sight_first,
        "cancel_hits_n": len(cancel_hits),
        "leaf_hits": uniq[:8],
        "heap_results_tail": heap_results[-3:],
        "recipe": recipe,
        "last_counters": last_counters,
        "result": result,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if uniq:
        CAPTURE.write_text(
            json.dumps(
                {
                    "phase": "2ew_leaf_move_capture",
                    "allow_post": False,
                    "captures": uniq,
                    "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    works = [
        "tight MOVE-VT edge-burst on live ITA@1x",
        f"burst={args.burst} busy-poll; edge_events={edge_events}",
        "Cancel-edge heap scan recipe armed",
        "VT candidates documented",
        "allow_post stays False",
    ]
    if uniq:
        works.append(f"LEAF move captured: {[u.get('name') for u in uniq]}")
    if cancel_hits:
        works.append(f"Cancel sighted during window x{len(cancel_hits)}")

    stubbed = []
    if not uniq:
        stubbed.extend(["live CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand"])
    stubbed.extend(["ring_embed", "SAFE_POST", "self-issue MOVE"])

    if uniq:
        blocker = "Decode/persist leaf Move → ring_embed (still no ALLOW_POST)"
    else:
        blocker = (
            "Tight burst+Cancel-edge heap still no leaf Move on ITA@1x — "
            "Move may never sit in DummyServer stage (direct Execute?) or AI quiet; "
            "next: optional deeper heap on Assign edge OR accept order-pipeline interim; still NO ALLOW_POST"
        )

    summary = {
        "phase": "2ew",
        "result": result,
        "scenario": "ITA @1x AI-on",
        "pid": pid,
        "ui_date": date_info.get("ui_date"),
        "hours": date_info.get("hours"),
        "observe_seconds": report["observe_seconds"],
        "polls": polls,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "heap_scans_on_cancel": heap_scans,
        "sight_counts": sight_counts,
        "leaf_names_hit": [u.get("name") for u in uniq],
        "vt_candidates": vt_candidates,
        "scan_recipe": recipe,
        "allow_post": False,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": blocker,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
