#!/usr/bin/env python3
"""Phase 2et: cheap war-start RO midflight capture (NO Post / NO ALLOW_POST).

Relaunch 1936 Ethiopia (ETH) — already at war with Italy on Jan 1 1936 —
at -start_speed=1 WITHOUT -noai. Arm midflight watcher; poll for real land cmds.
Never 5x. Never Posts. Document Haiti return recipe.

Usage:
  python scripts/phase2et_war_midflight.py
  python scripts/phase2et_war_midflight.py --tag ITA --observe-seconds 180
  python scripts/phase2et_war_midflight.py --skip-relaunch   # already on war tag
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "calling"))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "reports" / "phase2et_war_midflight.json"
SUMMARY = ROOT / "reports" / "phase2et_summary.json"
WATCHER_LOG = ROOT / "reports" / "phase2et_watcher.log"
WATCHER_ERR = ROOT / "reports" / "phase2et_watcher.err"
CAPTURE = ROOT / "reports" / "midflight_cmove_capture.json"
SIGHTLINE = ROOT / "reports" / "midflight_watcher_sightline.json"
HEARTBEAT = ROOT / "reports" / "midflight_watcher_heartbeat.json"

HAITI_RETURN = {
    "recipe": "python scripts/launch_into_map.py --speed 1 --allow-ai",
    "equiv_cli": "-gdpr-compliant -start_tag=HAI -start_speed=1",
    "paused_cool": "python scripts/launch_into_map.py  # HAI speed 0 -noai",
    "note": "Reversible: kill hoi4 then relaunch with HAI; no save required for RO RE.",
}

# Land VTs we care about (names match phase2bm WATCH)
LAND_NAMES = {
    "CMoveCommand",
    "CUnitMoveAction",
    "CStrategicRedeploymentCommand",
    "CUnitStrategicMoveAction",
    "CCancelMovementCommand",
    "CSupportAttackCommand",
    "COrderExecuteCommand",
    "COrderAssignCommand",
    "COrderUnassignCommand",
    "COrderDeleteCommand",
    "COrderNewFrontCommand",
    "COrderNewRootCommand",
    "COrderNewFallbackCommand",
    "COrderGroupCommand",
    "CMassMoveCommand",
    "CCancelRunningAwayCommand",
    "CWithdrawArmyHqCommand",
    "CToggleStrategicDeploymentCommand",
    "CMassCancelMovementCommand",
    "CMoveArmiesInTheaterCommand",
    "COrderInsertFrontCommand",
    "COrderSetPathCommand",
    "COrderReshapeCommand",
}


def py() -> str:
    return sys.executable


def kill_hoi4() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "hoi4.exe"], capture_output=True, text=True)
    time.sleep(3)


def kill_watchers() -> None:
    # Best-effort: stop prior midflight python arms (Windows)
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return
    # use wmic/powershell simpler
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'midflight_ready' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )


def launch_war(tag: str, speed: int) -> dict:
    """Relaunch via launch_into_map with --allow-ai and war tag."""
    kill_watchers()
    cmd = [
        py(),
        str(ROOT / "scripts" / "launch_into_map.py"),
        "--start-tag",
        tag,
        "--speed",
        str(speed),
        "--allow-ai",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "cmd": cmd,
        "rc": r.returncode,
        "stdout": (r.stdout or "")[-800:],
        "stderr": (r.stderr or "")[-400:],
    }


def wait_map(timeout: float = 240.0) -> dict:
    """Poll clausewitz_win status until CInGameIdler / armies visible."""
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout:
        try:
            r = subprocess.run(
                [py(), str(ROOT / "clausewitz_win.py"), "status"],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                timeout=45,
            )
            txt = r.stdout or ""
            last = {"rc": r.returncode, "snippet": txt[-600:]}
            if '"CInGameIdler"' in txt or "CInGameIdler" in txt:
                # parse date hours if present
                info = {"ok": True, "elapsed_s": round(time.time() - t0, 1)}
                try:
                    j = json.loads(txt)
                    gs = j.get("gamestate") or j.get("G_GAMESTATE") or {}
                    info["date_full"] = j.get("date_full") or gs.get("date_full")
                    info["pid"] = j.get("pid")
                    info["armies"] = (j.get("armies") or {}).get("armies_count")
                    info["player_tag"] = (j.get("armies") or {}).get("player_tag")
                except Exception:
                    pass
                if "date_hours_since_1936_01_01" in txt or "hours_value" in txt:
                    info["raw_has_hours"] = True
                return info
        except Exception as e:
            last = {"error": str(e)}
        time.sleep(5)
    return {"ok": False, "elapsed_s": round(time.time() - t0, 1), "last": last}


def arm_watcher(seconds: int = 600) -> dict:
    kill_watchers()
    time.sleep(1)
    WATCHER_LOG.write_text("", encoding="utf-8")
    WATCHER_ERR.write_text("", encoding="utf-8")
    log_f = open(WATCHER_LOG, "w", encoding="utf-8")
    err_f = open(WATCHER_ERR, "w", encoding="utf-8")
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
        stdout=log_f,
        stderr=err_f,
    )
    return {"pid": proc.pid, "seconds": seconds}


def read_json(path: Path):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}
    return None


def summarize_sightline(sl) -> dict:
    if not sl:
        return {"present": False}
    # tolerate several shapes
    names = {}
    hits = sl.get("hits") or sl.get("sightings") or sl.get("by_name") or []
    if isinstance(hits, dict):
        for k, v in hits.items():
            names[k] = v
    elif isinstance(hits, list):
        for h in hits:
            if isinstance(h, dict):
                n = h.get("name") or h.get("type") or h.get("vt_name")
                if n:
                    names[n] = names.get(n, 0) + int(h.get("count", 1))
            elif isinstance(h, str):
                names[h] = names.get(h, 0) + 1
    # also scan top-level counters
    for k, v in (sl.items() if isinstance(sl, dict) else []):
        if k in LAND_NAMES or k == "CHourlyTickCommand":
            names[k] = v
    land = {k: v for k, v in names.items() if k in LAND_NAMES}
    return {
        "present": True,
        "name_counts": names,
        "land_counts": land,
        "land_any": bool(land),
        "hourly_only": bool(names) and not land and ("CHourlyTickCommand" in names or not names),
    }


def path_vector_scan() -> dict:
    """RO deepen: scan CArmy path-ish pointers; do not invent nonempty."""
    try:
        from process import Backend, find_pid
        import struct

        pid = find_pid()
        if not pid:
            return {"ok": False, "error": "no hoi4"}
        b = Backend(pid)
        # reuse status armies if possible via light read of country armies
        # Minimal: call a tiny inline using existing army_subjects if available
        try:
            import army_subjects as asub

            snap = asub.snapshot_armies(b) if hasattr(asub, "snapshot_armies") else None
            if snap is None and hasattr(asub, "list_player_armies"):
                snap = asub.list_player_armies(b)
        except Exception as e:
            snap = None
            err = str(e)
        else:
            err = None
        nonempty = 0
        sampled = 0
        samples = []
        if isinstance(snap, dict):
            armies = snap.get("armies") or snap.get("items") or []
            if isinstance(armies, list):
                for a in armies[:24]:
                    sampled += 1
                    # look for path/movement fields without inventing
                    path = None
                    if isinstance(a, dict):
                        for key in ("path", "path_vector", "movement_path", "dest", "movement_dest"):
                            if key in a and a[key]:
                                path = a[key]
                                break
                    if path:
                        nonempty += 1
                        samples.append({"army": a.get("ptr") or a.get("address"), "path_keys": list(path)[:8] if isinstance(path, dict) else str(path)[:80]})
        return {
            "ok": True,
            "sampled": sampled,
            "path_nonempty": nonempty,
            "samples": samples[:5],
            "snap_err": err,
            "note": "RO only; empty means unobserved under this scenario, not a fabricated dest",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def live_date() -> dict:
    try:
        r = subprocess.run(
            [py(), str(ROOT / "clausewitz_win.py"), "status"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=45,
        )
        j = json.loads(r.stdout)
        df = j.get("date_full") or {}
        hours = df.get("hours_value")
        ui = None
        if isinstance(hours, int):
            from datetime import date, timedelta

            d = date(1936, 1, 1) + timedelta(days=hours // 24)
            ui = f"{d.isoformat()} {hours % 24:02d}:00"
        return {
            "pid": j.get("pid"),
            "hours": hours,
            "ui_date": ui,
            "armies_count": (j.get("armies") or {}).get("armies_count"),
            "theatres": (j.get("armies") or {}).get("theatres_count"),
            "fronts": (j.get("armies") or {}).get("fronts_count"),
            "allow_post": False,
        }
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="ETH", help="war-likely 1936 tag (default ETH vs ITA)")
    ap.add_argument("--speed", type=int, default=1, choices=[0, 1], help="0=pause 1=1x only")
    ap.add_argument("--observe-seconds", type=int, default=150)
    ap.add_argument("--skip-relaunch", action="store_true")
    ap.add_argument("--map-timeout", type=float, default=300)
    args = ap.parse_args()

    report = {
        "phase": "2et",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "haiti_return": HAITI_RETURN,
        "scenario": {
            "tag": args.tag,
            "why": "1936 ETH already at war with Italy on day 1 — cheapest land-combat traffic without Post",
            "speed": args.speed,
            "ai": "on (--allow-ai, no -noai)",
        },
    }

    if not args.skip_relaunch:
        report["relaunch"] = launch_war(args.tag, args.speed)
        report["map_wait"] = wait_map(args.map_timeout)
        if not report["map_wait"].get("ok"):
            report["result"] = "MAP_WAIT_FAILED"
            OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
            SUMMARY.write_text(json.dumps({"phase": "2et", "ok": False, "error": "map_wait"}, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2)[-2000:])
            return 1
    else:
        report["relaunch"] = {"skipped": True}

    report["live_before_observe"] = live_date()
    report["watcher"] = arm_watcher(seconds=max(600, args.observe_seconds + 60))
    t0 = time.time()
    # observe window
    time.sleep(args.observe_seconds)
    report["observe_elapsed_s"] = round(time.time() - t0, 1)
    report["live_after_observe"] = live_date()

    sl = read_json(SIGHTLINE)
    cap = read_json(CAPTURE)
    hb = read_json(HEARTBEAT)
    report["sightline"] = summarize_sightline(sl)
    report["capture_present"] = bool(cap) and not (isinstance(cap, dict) and cap.get("_error"))
    report["capture_summary"] = None
    if isinstance(cap, dict) and not cap.get("_error"):
        report["capture_summary"] = {
            "keys": list(cap.keys())[:20],
            "name": cap.get("name") or cap.get("type") or cap.get("vt_name"),
            "caught_army_move": cap.get("caught_army_move"),
        }
    report["heartbeat_tail"] = None
    if isinstance(hb, dict):
        report["heartbeat_tail"] = {k: hb.get(k) for k in ("ticks", "edges", "last_sight", "pid", "ts") if k in hb}

    report["path_vector_scan"] = path_vector_scan()

    land_any = (report["sightline"] or {}).get("land_any") or report.get("capture_present")
    report["works"] = {
        "war_relaunch": not args.skip_relaunch,
        "map_ok": True,
        "watcher_armed": True,
        "land_midflight_seen": bool(land_any),
        "allow_post_stays_false": True,
        "speed_le_1": args.speed <= 1,
    }
    report["stubbed"] = {
        "live_CMoveCommand": not bool(land_any),
        "ring_embed": True,
        "SAFE_POST_enable": True,
        "self_issue_MOVE": True,
    }
    if land_any:
        report["result"] = "LAND_MIDFLIGHT_SIGHTED"
        report["next_shortest_blocker"] = "Decode/persist capture → ring_embed rebuild (still no ALLOW_POST)"
    else:
        report["result"] = "NO_LAND_MIDFLIGHT_YET"
        report["next_shortest_blocker"] = (
            "ETH@1x AI-on produced no land cmd in observe window — try longer observe, "
            "ITA tag (attacker), or speed=1 longer; still NO Post / no user click"
        )

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2et",
                "result": report["result"],
                "tag": args.tag,
                "speed": args.speed,
                "ui_before": (report.get("live_before_observe") or {}).get("ui_date"),
                "ui_after": (report.get("live_after_observe") or {}).get("ui_date"),
                "land_any": bool(land_any),
                "sightline": report.get("sightline"),
                "haiti_return": HAITI_RETURN,
                "allow_post": False,
                "next_shortest_blocker": report["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(json.loads(SUMMARY.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
