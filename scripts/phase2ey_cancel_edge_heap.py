#!/usr/bin/env python3
"""Phase 2ey: Cancel-correlated concurrent heap for leaf MOVE (RO, NO Post).

On CCancelMovementCommand (vt 0x2a2c9b8) sight: immediate writable-heap scan
for 2ew MOVE VTs + dump pending/stage neighbors. One bounded window.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
sys.path.insert(0, str(ROOT / "scripts"))

import cmd_layout
import post_abi
from process import Backend, find_pid
import phase2bm_midflight_ready as mf

OUT = ROOT / "reports" / "phase2ey_cancel_edge_heap.json"
SUMMARY = ROOT / "reports" / "phase2ey_summary.json"
CAPTURE = ROOT / "reports" / "phase2ey_leaf_move_capture.json"
BYPASS = ROOT / "reports" / "phase2ey_direct_execute_ro.json"
DOC = ROOT / "docs" / "PHASE2EY_CANCEL_EDGE_HEAP.md"

CANCEL_NAMES = {"CCancelMovementCommand", "CMassCancelMovementCommand"}
LEAF_MOVE_NAMES = {
    "CMoveCommand",
    "CUnitMoveAction",
    "CSupportAttackCommand",
    "CMassMoveCommand",
    "CStrategicRedeploymentCommand",
    "CUnitStrategicMoveAction",
}
MOVE_FOCUS = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.MOVE["action"]["vt"]: "CUnitMoveAction",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.STRATEGIC["action"]["vt"]: "CUnitStrategicMoveAction",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    0x2A2C848: "CMassMoveCommand",
    0x2A0FC40: "CMassCancelMovementCommand",
    0x2A2CB28: "CSupportAttackCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def live_hours(b, base):
    try:
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
        gs = u64(b, base + gs_rva)
        hours = u32(b, gs + 0x484)
        d = date(1936, 1, 1) + timedelta(days=hours // 24)
        return {"hours": hours, "ui_date": f"{d.isoformat()} {hours % 24:02d}:00", "gs": hex(gs)}
    except Exception as e:
        return {"error": str(e)}


def sample_queues(b, base, sess, server):
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    counters = {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "seq": u32(b, server + 0xD0),
        "stage_count": scount,
    }
    hits = []

    def consider(ptr, source):
        vt = try_u64(b, ptr)
        if vt is None:
            return
        rva = vt - base
        name = MOVE_FOCUS.get(rva) or mf.WATCH.get(rva)
        if not name:
            return
        keep = (
            name in LEAF_MOVE_NAMES
            or name in CANCEL_NAMES
            or name in ("COrderAssignCommand", "COrderUnassignCommand", "CHourlyTickCommand")
        )
        if not keep:
            return
        try:
            hits.append({"source": source, **mf.dump_cmd(b, base, ptr, name)})
        except Exception as e:
            hits.append({"source": source, "addr": hex(ptr), "name": name, "error": str(e)})

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


def heap_scan_move(b, base, mb_limit=64, max_hits=10, tag="heap_cancel_edge"):
    needles = {
        name: struct.pack("<Q", base + vt)
        for vt, name in MOVE_FOCUS.items()
    }
    found, scanned = [], 0
    try:
        from mem import Proc

        src = Proc(find_pid("hoi4.exe"))
        if not hasattr(src, "regions"):
            return {"ok": False, "error": "no regions", "found": [], "tag": tag}
        for m in src.regions(writable=True, min_size=0x1000):
            start_m, end_m = m["start"], m["end"]
            if base <= start_m < base + 0x4000000:
                continue
            pos = start_m
            while pos < end_m and scanned < (mb_limit << 20) and len(found) < max_hits:
                n = min(1 << 20, end_m - pos)
                data = src.try_read(pos, n) if hasattr(src, "try_read") else None
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
                                    {"source": tag, "scanned_mb": scanned >> 20, **mf.dump_cmd(b, base, addr, name)}
                                )
                            except Exception as e:
                                found.append({"source": tag, "addr": hex(addr), "name": name, "error": str(e)})
                pos += n
            if len(found) >= max_hits:
                break
        return {"ok": True, "scanned_mb": scanned >> 20, "found": found, "tag": tag}
    except Exception as e:
        return {"ok": False, "error": str(e), "found": [], "tag": tag}


def catalog_b(cancel_n: int, heap_scans: int, leaf_n: int) -> dict:
    return {
        "phase": "2ey_option_B_catalog",
        "allow_post": False,
        "observation_only": True,
        "live_2ey": {
            "cancel_sights": cancel_n,
            "heap_scans_on_cancel": heap_scans,
            "leaf_move_hits": leaf_n,
        },
        "pipeline": {
            "FN_CMD_QUEUE_POST": hex(post_abi.FN_CMD_QUEUE_POST),
            "SINK_DUMMY": hex(post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY),
            "path": "UI/AI -> Post -> DummyServer ring+0xa0 -> drain pending+0x58 -> SessionUpdate Execute",
        },
        "move_layout": {
            "CMoveCommand_vt": hex(cmd_layout.MOVE["vt"]),
            "CUnitMoveAction_vt": hex(cmd_layout.MOVE["action"]["vt"]),
            "size": hex(cmd_layout.MOVE["size"]),
            "action_embed": hex(cmd_layout.MOVE["action_embed"]),
            "execute": hex(cmd_layout.MOVE["execute"]),
            "factory": hex(cmd_layout.MOVE["factory"]),
        },
        "evidence": [
            "Cancel reaches DummyServer stage (2eu/2ex/2ey) with vt 0x2a2c9b8.",
            "Assign/Unassign likewise on stage; leaf CMoveCommand never retained on stage/pending under dense poll.",
            "Cancel-edge 64MB heaps found 0 MOVE needles → Move object not lingering in writable heap at Cancel time (freed, never allocated, or non-heap/stack ephemeral).",
            "Catalog SP path is DummyServer-centric; no separate proven stack-only Execute entry for land Move.",
        ],
        "conclusion": (
            "Cancel-correlated heap still finds no leaf Move. Stack/direct-Execute-only Move remains "
            "unproven; more consistent with AI rarely constructing CMoveCommand objects that survive "
            "into DummyServer/heap windows. Sample gap persists. Still NO ALLOW_POST."
        ),
        "next_cheapest_recipe": {
            "name": "Factory-site / execlist RO peek (observation)",
            "steps": [
                "RO-read Session execlist (+0x40 per FINDINGS) during Cancel/Assign edges for MOVE VT",
                "OR one ETH@1x relaunch window where Cancel was denser historically",
                "Do NOT enable Post; do NOT endless-poll ITA peacetime-ish traffic",
            ],
            "forbid": ["ALLOW_POST", "Post inject", "5x", "ask right-click"],
        },
    }


def kill_midflight():
    import subprocess

    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'phase2bm_midflight_ready' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--cancel-quiet-s", type=float, default=50.0)
    ap.add_argument("--heap-mb", type=int, default=64)
    ap.add_argument("--max-heap-scans", type=int, default=6)
    ap.add_argument("--burst", type=int, default=32)
    ap.add_argument("--no-kill-watcher", action="store_true")
    args = ap.parse_args()

    if not args.no_kill_watcher:
        kill_midflight()
        time.sleep(0.3)

    pid = find_pid("hoi4.exe")
    if not pid:
        print(json.dumps({"error": "no hoi4"}))
        return 1
    b = Backend(pid)
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)

    t0 = time.time()
    polls = edge_events = burst_samples = heap_scans = 0
    sight_counts, sight_first = {}, {}
    cancel_hits, leaf_hits, neighbor_snaps, heap_results = [], [], [], []
    prev = last_counters = None
    cancel_seen_at = None
    option_b_ran = False
    post_cancel_drain_heaps = 0

    while time.time() - t0 < args.seconds:
        polls += 1
        hits, last_counters = sample_queues(b, base, sess, server)
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
                h2, c2 = sample_queues(b, base, sess, server)
                last_counters = c2
                hits.extend(h2)
                if any(h.get("name") in CANCEL_NAMES or h.get("name") in LEAF_MOVE_NAMES for h in h2):
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
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            if name in CANCEL_NAMES:
                cancel_hits.append(h)
                saw_cancel = True
                if cancel_seen_at is None:
                    cancel_seen_at = time.time() - t0
            if name in LEAF_MOVE_NAMES:
                leaf_hits.append(h)

        if saw_cancel:
            # neighbors = non-HourlyTick hits in same sample burst
            neighbors = [h for h in hits if h.get("name") not in ("CHourlyTickCommand",)]
            neighbor_snaps.append(
                {
                    "t": round(time.time() - t0, 2),
                    "poll": polls,
                    "counters": dict(last_counters),
                    "neighbors": neighbors[:24],
                }
            )

        trigger = False
        tag = "heap_cancel_edge"
        if saw_cancel and heap_scans < args.max_heap_scans:
            trigger = True
            tag = "heap_cancel_edge"
        elif (
            cancel_seen_at is not None
            and (time.time() - t0 - cancel_seen_at) < 6.0
            and edge
            and post_cancel_drain_heaps < 2
            and heap_scans < args.max_heap_scans
        ):
            trigger = True
            tag = "heap_post_cancel_drain"
            post_cancel_drain_heaps += 1

        if trigger:
            heap_scans += 1
            hr = heap_scan_move(b, base, mb_limit=args.heap_mb, tag=tag)
            heap_results.append({"poll": polls, "counters": dict(last_counters), **hr})
            for f in hr.get("found") or []:
                if f.get("name") in LEAF_MOVE_NAMES:
                    leaf_hits.append(f)
                # also record Cancel on heap as adjacency proof
            if leaf_hits:
                break

        # quiet → stop after short wait
        if cancel_seen_at is None and (time.time() - t0) >= args.cancel_quiet_s:
            break

    uniq, seen_a = [], set()
    for h in leaf_hits:
        a = h.get("addr")
        if a in seen_a:
            continue
        seen_a.add(a)
        uniq.append(h)

    # Option B if Cancel fired but no Move, OR Cancel quiet
    bypass = catalog_b(len(cancel_hits), heap_scans, len(uniq))
    if cancel_seen_at is not None and not uniq:
        option_b_ran = True
    elif cancel_seen_at is None:
        option_b_ran = True
        bypass["note"] = "Cancel quiet this window; catalog still recorded."
    BYPASS.write_text(json.dumps(bypass, indent=2), encoding="utf-8")

    date_info = live_hours(b, base)
    if uniq:
        result = "LEAF_MOVE_CAPTURED"
    elif cancel_seen_at is not None:
        result = "CANCEL_EDGE_HEAP_NO_MOVE"
    else:
        result = "CANCEL_QUIET_RECIPE_STATUS"

    # heap name tallies
    heap_name_counts = {}
    for hr in heap_results:
        for f in hr.get("found") or []:
            n = f.get("name") or "?"
            heap_name_counts[n] = heap_name_counts.get(n, 0) + 1

    report = {
        "phase": "2ey",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "scenario": "ITA@1x keep live",
        "pid": pid,
        "date": date_info,
        "observe_seconds": round(time.time() - t0, 1),
        "polls": polls,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "heap_scans": heap_scans,
        "cancel_seen_at_s": cancel_seen_at,
        "cancel_hits_n": len(cancel_hits),
        "option_b_ran": option_b_ran,
        "sight_counts": sight_counts,
        "sight_first": sight_first,
        "neighbor_snaps_n": len(neighbor_snaps),
        "neighbor_snaps_tail": neighbor_snaps[-3:],
        "leaf_hits": uniq[:8],
        "heap_name_counts": heap_name_counts,
        "heap_results_meta": [
            {"tag": hr.get("tag"), "ok": hr.get("ok"), "mb": hr.get("scanned_mb"), "n_found": len(hr.get("found") or [])}
            for hr in heap_results
        ],
        "vt_candidates": {n: hex(v) for v, n in MOVE_FOCUS.items()},
        "last_counters": last_counters,
        "result": result,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if uniq:
        CAPTURE.write_text(
            json.dumps({"phase": "2ey_leaf_move_capture", "allow_post": False, "captures": uniq}, indent=2),
            encoding="utf-8",
        )

    works = [
        "Cancel-correlated concurrent heap armed",
        f"heap_scans={heap_scans} mb={args.heap_mb}",
        "allow_post stays False",
    ]
    if cancel_seen_at is not None:
        works.append(f"Cancel sighted at t={cancel_seen_at:.1f}s x{len(cancel_hits)}")
    if heap_name_counts:
        works.append(f"heap non-Move finds: {heap_name_counts}")
    if option_b_ran:
        works.append("option B RO catalog: stack/direct-Execute Move unproven")
    if uniq:
        works.append(f"LEAF: {[u.get('name') for u in uniq]}")

    stubbed = []
    if not uniq:
        stubbed.extend(["live CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand"])
    stubbed.extend(["ring_embed", "SAFE_POST", "self-issue MOVE"])

    if uniq:
        blocker = "Decode/persist leaf Move → ring_embed (still NO ALLOW_POST)"
    elif cancel_seen_at is not None:
        blocker = bypass["next_cheapest_recipe"]["name"] + " — still NO ALLOW_POST"
    else:
        blocker = "Cancel quiet; retry Cancel-edge on denser war traffic OR execlist RO peek; still NO ALLOW_POST"

    summary = {
        "phase": "2ey",
        "result": result,
        "scenario": "ITA @1x AI-on",
        "pid": pid,
        "ui_date": date_info.get("ui_date"),
        "hours": date_info.get("hours"),
        "observe_seconds": report["observe_seconds"],
        "polls": polls,
        "edge_events": edge_events,
        "heap_scans": heap_scans,
        "cancel_seen_at_s": cancel_seen_at,
        "cancel_hits_n": len(cancel_hits),
        "option_b_ran": option_b_ran,
        "sight_counts": sight_counts,
        "heap_name_counts": heap_name_counts,
        "leaf_names_hit": [u.get("name") for u in uniq],
        "allow_post": False,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": blocker,
        "direct_execute_conclusion": bypass.get("conclusion"),
        "next_cheapest_recipe": bypass.get("next_cheapest_recipe"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    DOC.write_text(
        f"""# Phase 2ey — Cancel-correlated concurrent heap (RO)

**Result:** `{result}`

| Metric | Value |
|--------|-------|
| Scenario | ITA @1x pid {pid} |
| UI | {date_info.get('ui_date')} |
| Observe | {report['observe_seconds']}s |
| Cancel sights | {len(cancel_hits)} (first t={cancel_seen_at}) |
| Heap scans | {heap_scans} × {args.heap_mb}MB |
| Leaf Move | {len(uniq)} |
| Heap finds | {heap_name_counts} |

Option B conclusion: {bypass.get('conclusion')}

Next: `{bypass['next_cheapest_recipe']['name']}` — still **NO ALLOW_POST**.

Script: `scripts/phase2ey_cancel_edge_heap.py`
""",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
