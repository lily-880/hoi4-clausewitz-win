#!/usr/bin/env python3
"""Phase 2eu: longer ETH@1x RO midflight for CMove/CSupportAttack (NO Post).

Assumes ETH already live @1x AI-on. Re-arms watcher, observes N seconds,
snapshots sight_counts / captures. Optional cheap RO note on Cancel/Assign.
Never 5x. Never Posts. Documents ITA next recipe if Move still missing.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "calling"))

OUT = ROOT / "reports" / "phase2eu_eth_longer.json"
SUMMARY = ROOT / "reports" / "phase2eu_summary.json"
SIGHTLINE = ROOT / "reports" / "midflight_watcher_sightline.json"
HEARTBEAT = ROOT / "reports" / "midflight_watcher_heartbeat.json"
CAPTURE = ROOT / "reports" / "midflight_cmove_capture.json"
WLOG = ROOT / "reports" / "phase2eu_watcher.log"
WERR = ROOT / "reports" / "phase2eu_watcher.err"

LAND_FOCUS = {
    "CMoveCommand",
    "CUnitMoveAction",
    "CSupportAttackCommand",
    "CStrategicRedeploymentCommand",
    "CUnitStrategicMoveAction",
    "CCancelMovementCommand",
    "CMassMoveCommand",
    "CMassCancelMovementCommand",
    "COrderAssignCommand",
    "COrderUnassignCommand",
    "COrderExecuteCommand",
    "COrderNewFrontCommand",
    "COrderNewFallbackCommand",
}

ITA_NEXT = {
    "recipe": "python scripts/phase2et_war_midflight.py --tag ITA --speed 1 --observe-seconds 240",
    "equiv_cli": "-gdpr-compliant -start_tag=ITA -start_speed=1",
    "why": "ITA is the attacker in the 1936 Ethiopia war — more offensive Move/Attack traffic than ETH defender",
    "haiti_return": "python scripts/launch_into_map.py --speed 1 --allow-ai",
}


def py() -> str:
    return sys.executable


def kill_watchers() -> None:
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'midflight_ready' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)


def arm_watcher(seconds: int) -> dict:
    kill_watchers()
    time.sleep(1)
    WLOG.write_text("", encoding="utf-8")
    WERR.write_text("", encoding="utf-8")
    lf = open(WLOG, "w", encoding="utf-8")
    ef = open(WERR, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            py(),
            str(ROOT / "scripts" / "phase2bm_midflight_ready.py"),
            "--seconds",
            str(seconds),
            "--interval",
            "0.02",
            "--heap-every",
            "0",
            "--burst-on-edge",
            "12",
        ],
        cwd=str(ROOT),
        stdout=lf,
        stderr=ef,
    )
    return {"pid": proc.pid, "seconds": seconds}


def read_json(path: Path):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}
    return None


def live_hours() -> dict:
    try:
        r = subprocess.run(
            [py(), str(ROOT / "clausewitz_win.py"), "status"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=60,
        )
        j = json.loads(r.stdout)
        df = j.get("date_full") or {}
        hours = df.get("hours_value")
        # nested fallbacks
        if hours is None:
            for blob in (j, j.get("gamestate") or {}, (j.get("session") or {})):
                if isinstance(blob, dict):
                    d2 = blob.get("date_full") or {}
                    if isinstance(d2, dict) and "hours_value" in d2:
                        hours = d2["hours_value"]
                        break
                    if "date_hours_since_1936_01_01" in blob:
                        hours = blob["date_hours_since_1936_01_01"]
                        break
        ui = None
        if isinstance(hours, int):
            d = date(1936, 1, 1) + timedelta(days=hours // 24)
            ui = f"{d.isoformat()} {hours % 24:02d}:00"
        return {
            "pid": j.get("pid"),
            "hours": hours,
            "ui_date": ui,
            "armies_count": (j.get("armies") or {}).get("armies_count"),
            "allow_post": False,
        }
    except Exception as e:
        return {"error": str(e), "allow_post": False}


def hoi4_cmdline() -> str | None:
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='hoi4.exe'\" | "
        "Select-Object -ExpandProperty CommandLine"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return (r.stdout or "").strip() or None


def ro_follow_order_pipeline(sl: dict) -> dict:
    """Observation-only: summarize land order sightings + Cancel as Move-adjacent."""
    sc = (sl or {}).get("sight_counts") or {}
    first = (sl or {}).get("sight_first") or {}
    land = {k: v for k, v in sc.items() if k in LAND_FOCUS}
    pipeline = {
        "assign": sc.get("COrderAssignCommand", 0),
        "unassign": sc.get("COrderUnassignCommand", 0),
        "execute": sc.get("COrderExecuteCommand", 0),
        "cancel_movement": sc.get("CCancelMovementCommand", 0),
        "move": sc.get("CMoveCommand", 0),
        "unit_move_action": sc.get("CUnitMoveAction", 0),
        "support_attack": sc.get("CSupportAttackCommand", 0),
    }
    note = []
    if pipeline["cancel_movement"] and not pipeline["move"]:
        note.append(
            "CCancelMovementCommand sighted without CMoveCommand in stage window — "
            "Move may be too short-lived / drained before poll; Cancel proves movement existed"
        )
    if pipeline["assign"] and not pipeline["move"]:
        note.append("COrderAssignCommand present — battle-planner order traffic without leaf Move capture")
    return {
        "land_sight_counts": land,
        "pipeline_counters": pipeline,
        "sight_first_land": {k: first[k] for k in first if k in LAND_FOCUS},
        "notes": note,
        "predict_move": (
            "Move most likely when cancel_movement rises or during active front combat; "
            "attacker ITA may emit longer-lived CMoveCommand than ETH defender cancels"
        ),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--observe-seconds", type=int, default=360)
    ap.add_argument("--keep-prior-sightline", action="store_true",
                    help="merge prior sight_counts into baseline (default: snapshot baseline then re-arm fresh)")
    args = ap.parse_args()

    baseline_sl = read_json(SIGHTLINE) or {}
    baseline_counts = dict(baseline_sl.get("sight_counts") or {})

    report = {
        "phase": "2eu",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "scenario": "ETH @1x AI-on (no relaunch)",
        "cmdline": hoi4_cmdline(),
        "baseline_sight_counts": baseline_counts,
        "live_before": live_hours(),
        "ita_next_if_quiet": ITA_NEXT,
    }

    # Re-arm for observe window (+60s slack)
    report["watcher"] = arm_watcher(seconds=max(600, args.observe_seconds + 60))
    t0 = time.time()
    time.sleep(args.observe_seconds)
    report["observe_elapsed_s"] = round(time.time() - t0, 1)
    report["live_after"] = live_hours()

    sl = read_json(SIGHTLINE) or {}
    hb = read_json(HEARTBEAT) or {}
    cap = read_json(CAPTURE)

    after_counts = dict(sl.get("sight_counts") or {})
    # delta vs baseline (cumulative file may reset on re-arm — handle both)
    delta = {}
    for k, v in after_counts.items():
        b = baseline_counts.get(k, 0)
        # if watcher reset, after may be smaller; treat after as window-local
        if v >= b and baseline_counts:
            delta[k] = v - b
        else:
            delta[k] = v

    report["sight_counts_after"] = after_counts
    report["sight_delta_vs_baseline"] = delta
    report["pipeline"] = ro_follow_order_pipeline(sl)
    report["heartbeat"] = {
        k: hb.get(k)
        for k in ("polls", "elapsed_s", "captures", "caught_army_move", "sight_counts", "ts_asia_shanghai")
    }
    report["capture_present"] = bool(cap) and not (isinstance(cap, dict) and cap.get("_error"))
    if isinstance(cap, dict) and not cap.get("_error"):
        report["capture_summary"] = {
            "name": cap.get("name") or cap.get("type") or cap.get("vt_name"),
            "caught_army_move": cap.get("caught_army_move"),
            "keys": list(cap.keys())[:24],
        }

    # Do NOT treat midflight_cmove_capture.json alone as Move — watcher also
    # dumps CCancelMovementCommand under caught_army_move.
    cap_names = set()
    if isinstance(cap, dict):
        for c in cap.get("captures") or []:
            if isinstance(c, dict) and c.get("name"):
                cap_names.add(c["name"])
        n = cap.get("name") or cap.get("type") or cap.get("vt_name")
        if n:
            cap_names.add(n)
    move_names = {"CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand", "CMassMoveCommand"}
    move_hit = (
        after_counts.get("CMoveCommand", 0) > 0
        or after_counts.get("CUnitMoveAction", 0) > 0
        or after_counts.get("CSupportAttackCommand", 0) > 0
        or after_counts.get("CMassMoveCommand", 0) > 0
        or bool(cap_names & move_names)
    )
    cancel_hit = after_counts.get("CCancelMovementCommand", 0) > 0
    assign_hit = after_counts.get("COrderAssignCommand", 0) > 0

    works = [
        "ETH@1x kept (no 5x)",
        "watcher re-armed longer observe",
        "RO pipeline counters (Assign/Unassign/Cancel/Move)",
        "allow_post stays False",
    ]
    if assign_hit:
        works.append("COrderAssignCommand midflight confirmed")
    if cancel_hit:
        works.append("CCancelMovementCommand midflight (Move-adjacent proof)")
    if move_hit:
        works.append("true CMove/SupportAttack/UnitMoveAction midflight captured")

    stubbed = []
    if not move_hit:
        stubbed.extend(["live CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand", "midflight_cmove_capture.json"])
    stubbed.extend(["ring_embed", "SAFE_POST enable", "self-issue MOVE"])

    if move_hit:
        result = "LAND_MOVE_OR_ATTACK_SIGHTED"
        blocker = "Persist/decode Move capture → ring_embed (still no ALLOW_POST)"
    elif cancel_hit:
        result = "CANCEL_MOVEMENT_WITHOUT_MOVE_SAMPLE"
        blocker = (
            "CancelMovement proves moves happen but CMoveCommand not retained in stage — "
            "try ITA@1x attacker OR tighten watcher burst on Cancel edge; still NO ALLOW_POST"
        )
    else:
        result = "NO_MOVE_YET"
        blocker = "ETH quiet for Move — use ITA next recipe; still NO ALLOW_POST"

    summary = {
        "phase": "2eu",
        "result": result,
        "scenario": "ETH @1x AI-on",
        "observe_seconds": args.observe_seconds,
        "ui_before": (report.get("live_before") or {}).get("ui_date"),
        "ui_after": (report.get("live_after") or {}).get("ui_date"),
        "sight_counts": after_counts,
        "sight_delta": delta,
        "pipeline": report["pipeline"]["pipeline_counters"],
        "move_hit": move_hit,
        "cancel_hit": cancel_hit,
        "assign_hit": assign_hit,
        "captures": hb.get("captures", 0),
        "caught_army_move": hb.get("caught_army_move", False),
        "ita_next": ITA_NEXT,
        "allow_post": False,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": blocker,
    }
    report["result"] = result
    report["works"] = works
    report["stubbed"] = stubbed
    report["next_shortest_blocker"] = blocker

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
