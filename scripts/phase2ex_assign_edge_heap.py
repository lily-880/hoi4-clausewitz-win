#!/usr/bin/env python3
"""Phase 2ex: Assign-edge heap scan for leaf MOVE VTs (RO, NO Post).

When COrderAssignCommand / COrderUnassignCommand appears on pending/stage,
immediately scan writable heap for 2ew MOVE-VT candidates.
If Assign stays quiet: emit RO catalog note on DummyServer vs direct-Execute.

Usage:
  python scripts/phase2ex_assign_edge_heap.py --seconds 90
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

OUT = ROOT / "reports" / "phase2ex_assign_edge_heap.json"
SUMMARY = ROOT / "reports" / "phase2ex_summary.json"
CAPTURE = ROOT / "reports" / "phase2ex_leaf_move_capture.json"
BYPASS = ROOT / "reports" / "phase2ex_direct_execute_ro.json"

ASSIGN_NAMES = {"COrderAssignCommand", "COrderUnassignCommand"}
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
        if name not in LEAF_MOVE_NAMES and name not in ASSIGN_NAMES and name not in (
            "CCancelMovementCommand",
            "CMassCancelMovementCommand",
            "CHourlyTickCommand",
        ):
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


def heap_scan_move(b, base, mb_limit=64, max_hits=8, tag="heap_assign_edge"):
    needles = {
        name: struct.pack("<Q", base + vt)
        for vt, name in MOVE_FOCUS.items()
        if name in LEAF_MOVE_NAMES or name.startswith("CCancel") or name.startswith("CMassCancel")
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


def catalog_direct_execute_ro() -> dict:
    """Option B: observation-only from existing RO catalogs — no live writes."""
    return {
        "phase": "2ex_option_B_catalog",
        "allow_post": False,
        "observation_only": True,
        "pipeline_catalog": {
            "FN_CMD_QUEUE_POST": hex(post_abi.FN_CMD_QUEUE_POST),
            "FN_CMD_QUEUE_POST_SINK_DUMMY": hex(post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY),
            "path_doc": getattr(post_abi, "PATH", None)
            or "UI/AI -> FN_CMD_QUEUE_POST(session, cmd) -> DummyServer sink -> drain pending -> SessionUpdate Execute",
            "pending_off": hex(post_abi.CDummyServer_PENDING),
            "stage_array_off": hex(post_abi.CSession_STAGE_ARRAY),
            "stage_count_off": hex(post_abi.CSession_STAGE_COUNT),
        },
        "move_layout": {
            "CMoveCommand_vt": hex(cmd_layout.MOVE["vt"]),
            "CUnitMoveAction_vt": hex(cmd_layout.MOVE["action"]["vt"]),
            "size": hex(cmd_layout.MOVE["size"]),
            "action_embed": hex(cmd_layout.MOVE["action_embed"]),
            "execute_rva": hex(cmd_layout.MOVE["execute"]),
            "factory_rva": hex(cmd_layout.MOVE["factory"]),
        },
        "evidence": [
            "Other land cmds (HourlyTick, Assign, Unassign, Cancel) DO appear on DummyServer stage — Post→Dummy path is live for those classes.",
            "2ew tight burst (634k polls / 2110 edges) never saw leaf Move on stage/pending → either AI rarely Posts Move, or Move lifetime ≪ poll, or Move uses a different queue that still drains via same counters.",
            "Catalog does NOT prove a separate non-Dummy Execute-only path for CMoveCommand; SP land Post ABI is DummyServer-centric (FINDINGS / post_abi).",
            "Strongest adjacent proof remains ETH CCancelMovementCommand on stage (2eu) — Cancel reaches Dummy; leaf Move still absent.",
        ],
        "conclusion": (
            "RO catalogs do not establish a Move bypass of DummyServer. "
            "Absence on stage under dense polling is better explained by rare/short-lived AI Move Posts "
            "than by a proven direct-Execute-only path. Next cheapest: longer Assign-edge heap when "
            "Assign traffic returns (ETH war / order churn), still NO ALLOW_POST."
        ),
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
    ap.add_argument("--assign-quiet-s", type=float, default=45.0, help="if no Assign by then, run option B")
    ap.add_argument("--heap-mb", type=int, default=64)
    ap.add_argument("--max-heap-scans", type=int, default=6)
    ap.add_argument("--burst", type=int, default=24)
    ap.add_argument("--no-kill-watcher", action="store_true")
    args = ap.parse_args()

    if not args.no_kill_watcher:
        kill_midflight()
        time.sleep(0.4)

    pid = find_pid("hoi4.exe")
    if not pid:
        print(json.dumps({"error": "no hoi4"}))
        return 1
    b = Backend(pid)
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)

    t0 = time.time()
    polls = 0
    edge_events = 0
    burst_samples = 0
    heap_scans = 0
    sight_counts = {}
    sight_first = {}
    assign_hits = []
    leaf_hits = []
    heap_results = []
    prev = None
    last_counters = None
    assign_seen_at = None
    option_b_ran = False
    post_assign_drain_heaps = 0

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
                if any(h.get("name") in ASSIGN_NAMES or h.get("name") in LEAF_MOVE_NAMES for h in h2):
                    break
        prev = dict(last_counters)

        saw_assign = False
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
            if name in ASSIGN_NAMES:
                assign_hits.append(h)
                saw_assign = True
                if assign_seen_at is None:
                    assign_seen_at = time.time() - t0
            if name in LEAF_MOVE_NAMES:
                leaf_hits.append(h)

        trigger_heap = False
        tag = "heap_assign_edge"
        if saw_assign and heap_scans < args.max_heap_scans:
            trigger_heap = True
            tag = "heap_assign_edge"
        # shortly after Assign, also heap on next drain edges (Move may follow Assign)
        elif (
            assign_seen_at is not None
            and (time.time() - t0 - assign_seen_at) < 8.0
            and edge
            and post_assign_drain_heaps < 2
            and heap_scans < args.max_heap_scans
        ):
            trigger_heap = True
            tag = "heap_post_assign_drain"
            post_assign_drain_heaps += 1

        if trigger_heap:
            heap_scans += 1
            hr = heap_scan_move(b, base, mb_limit=args.heap_mb, tag=tag)
            heap_results.append({"poll": polls, "counters": dict(last_counters), **hr})
            for f in hr.get("found") or []:
                if f.get("name") in LEAF_MOVE_NAMES:
                    leaf_hits.append(f)

        if leaf_hits:
            break

        # Option B if Assign quiet
        if (
            not option_b_ran
            and assign_seen_at is None
            and (time.time() - t0) >= args.assign_quiet_s
        ):
            option_b_ran = True
            bypass = catalog_direct_execute_ro()
            BYPASS.write_text(json.dumps(bypass, indent=2), encoding="utf-8")
            # one opportunistic heap anyway (cheap) tagged quiet-window
            if heap_scans < args.max_heap_scans:
                heap_scans += 1
                hr = heap_scan_move(b, base, mb_limit=min(48, args.heap_mb), tag="heap_assign_quiet_opportunistic")
                heap_results.append({"poll": polls, "counters": dict(last_counters), **hr})
                for f in hr.get("found") or []:
                    if f.get("name") in LEAF_MOVE_NAMES:
                        leaf_hits.append(f)
            # continue remaining window briefly then stop early if still no assign
            # (don't burn full quota after B)
            if (time.time() - t0) > args.assign_quiet_s + 15:
                break

    if not option_b_ran and assign_seen_at is None:
        option_b_ran = True
        bypass = catalog_direct_execute_ro()
        BYPASS.write_text(json.dumps(bypass, indent=2), encoding="utf-8")
    elif option_b_ran and not BYPASS.exists():
        BYPASS.write_text(json.dumps(catalog_direct_execute_ro(), indent=2), encoding="utf-8")

    date_info = live_hours(b, base)
    seen_a, uniq = set(), []
    for h in leaf_hits:
        a = h.get("addr")
        if a in seen_a:
            continue
        seen_a.add(a)
        uniq.append(h)

    result = "LEAF_MOVE_CAPTURED" if uniq else (
        "ASSIGN_EDGE_HEAP_NO_MOVE" if assign_seen_at is not None else "ASSIGN_QUIET_OPTION_B_CATALOG"
    )

    report = {
        "phase": "2ex",
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
        "assign_seen_at_s": assign_seen_at,
        "assign_hits_n": len(assign_hits),
        "option_b_ran": option_b_ran,
        "sight_counts": sight_counts,
        "sight_first": sight_first,
        "leaf_hits": uniq[:8],
        "heap_results": heap_results,
        "last_counters": last_counters,
        "vt_candidates": {n: hex(v) for v, n in MOVE_FOCUS.items()},
        "result": result,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if uniq:
        CAPTURE.write_text(
            json.dumps(
                {
                    "phase": "2ex_leaf_move_capture",
                    "allow_post": False,
                    "captures": uniq,
                    "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    works = [
        "Assign-edge heap scan armed (Assign/Unassign → MOVE-VT heap)",
        f"heap_scans={heap_scans} mb={args.heap_mb}",
        "allow_post stays False",
    ]
    if assign_seen_at is not None:
        works.append(f"Assign sighted at t={assign_seen_at:.1f}s")
    if option_b_ran:
        works.append("option B RO catalog: Move DummyServer-bypass NOT proven")
    if uniq:
        works.append(f"LEAF move: {[u.get('name') for u in uniq]}")

    stubbed = []
    if not uniq:
        stubbed.extend(["live CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand"])
    stubbed.extend(["ring_embed", "SAFE_POST", "self-issue MOVE"])

    if uniq:
        blocker = "Decode/persist leaf Move → ring_embed design (still NO ALLOW_POST)"
    elif assign_seen_at is not None:
        blocker = (
            "Assign-edge heap ran but no leaf Move on heap — Move may free before scan or never allocated; "
            "next: ETH Cancel-correlated heap or accept sample gap; still NO ALLOW_POST"
        )
    else:
        blocker = (
            "Assign quiet on ITA@1x this window; RO catalog rejects proven DummyServer-bypass; "
            "next cheapest: wait Assign/Cancel churn (ETH/ITA war traffic) then one heap; still NO ALLOW_POST"
        )

    summary = {
        "phase": "2ex",
        "result": result,
        "scenario": "ITA @1x AI-on",
        "pid": pid,
        "ui_date": date_info.get("ui_date"),
        "hours": date_info.get("hours"),
        "observe_seconds": report["observe_seconds"],
        "polls": polls,
        "edge_events": edge_events,
        "heap_scans": heap_scans,
        "assign_seen_at_s": assign_seen_at,
        "option_b_ran": option_b_ran,
        "sight_counts": sight_counts,
        "leaf_names_hit": [u.get("name") for u in uniq],
        "allow_post": False,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": blocker,
        "direct_execute_conclusion": (
            json.loads(BYPASS.read_text(encoding="utf-8")).get("conclusion") if BYPASS.exists() else None
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
