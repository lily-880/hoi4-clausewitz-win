#!/usr/bin/env python3
"""Phase 2fa: ETH@1x relaunch + denser execlist-only RO window (NO Post).

One bounded observe (default 100s). Never 5x. Never ALLOW_POST.
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
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

OUT = ROOT / "reports" / "phase2fa_eth_execlist.json"
SUMMARY = ROOT / "reports" / "phase2fa_summary.json"
CAPTURE = ROOT / "reports" / "phase2fa_leaf_move_capture.json"
DOC = ROOT / "docs" / "PHASE2FA_ETH_EXECLIST.md"

LEAF_MOVE = {
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
WATCH_OK = set(MOVE_FOCUS.values()) | {
    "COrderAssignCommand",
    "COrderUnassignCommand",
    "CHourlyTickCommand",
}

HAITI_RETURN = {
    "recipe": "python scripts/launch_into_map.py --speed 1 --allow-ai",
    "equiv_cli": "-gdpr-compliant -start_tag=HAI -start_speed=1",
}
ITA_RETURN = {
    "recipe": "python scripts/launch_into_map.py --start-tag ITA --speed 1 --allow-ai",
    "equiv_cli": "-gdpr-compliant -start_tag=ITA -start_speed=1",
}


def py():
    return sys.executable


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
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'phase2bm_midflight_ready|phase2fa_eth' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    # do not kill self: exclude phase2fa when matching — only midflight
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'phase2bm_midflight_ready' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)


def relaunch(tag: str, speed: int) -> dict:
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
    return {"cmd": cmd, "rc": r.returncode, "stdout": (r.stdout or "")[-600:], "stderr": (r.stderr or "")[-300:]}


def wait_map(timeout: float = 240.0) -> dict:
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
            last = {"snippet": txt[-400:]}
            if "CInGameIdler" in txt:
                info = {"ok": True, "elapsed_s": round(time.time() - t0, 1)}
                try:
                    j = json.loads(txt)
                    info["pid"] = j.get("pid")
                    info["player_tag"] = (j.get("armies") or {}).get("player_tag")
                    info["armies"] = (j.get("armies") or {}).get("armies_count")
                    info["date_full"] = j.get("date_full")
                except Exception:
                    pass
                return info
        except Exception as e:
            last = {"error": str(e)}
        time.sleep(4)
    return {"ok": False, "elapsed_s": round(time.time() - t0, 1), "last": last}


def live_hours(b, base):
    try:
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
        gs = u64(b, base + gs_rva)
        hours = u32(b, gs + 0x484)
        d = date(1936, 1, 1) + timedelta(days=hours // 24)
        return {"hours": hours, "ui_date": f"{d.isoformat()} {hours % 24:02d}:00"}
    except Exception as e:
        return {"error": str(e)}


def walk_list(b, base, head, list_name, limit=48):
    hits, seen, cur = [], set(), head
    while cur and cur not in seen and len(hits) < limit:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        rva = vt - base
        name = MOVE_FOCUS.get(rva) or mf.WATCH.get(rva)
        if name and name in WATCH_OK:
            try:
                hits.append({"list": list_name, **mf.dump_cmd(b, base, cur, name)})
            except Exception as e:
                hits.append({"list": list_name, "addr": hex(cur), "name": name, "error": str(e)})
        nxt = try_u64(b, cur + 8)
        if not nxt or nxt == cur:
            break
        cur = nxt
    return hits


def sample(b, base, sess, server):
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    execlist_h = try_u64(b, server + post_abi.CDummyServer_EXECLIST) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    counters = {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "seq": u32(b, server + 0xD0),
        "stage_count": scount,
        "execlist_head": hex(execlist_h) if execlist_h else "0x0",
        "pending_head": hex(pending_h) if pending_h else "0x0",
    }
    hits = []
    hits.extend(walk_list(b, base, execlist_h, "execlist"))
    hits.extend(walk_list(b, base, pending_h, "pending"))
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            rva = vt - base
            name = MOVE_FOCUS.get(rva) or mf.WATCH.get(rva)
            if not name or name not in WATCH_OK:
                continue
            try:
                hits.append({"list": f"stage[{i}]", **mf.dump_cmd(b, base, ptr, name)})
            except Exception as e:
                hits.append({"list": f"stage[{i}]", "addr": hex(ptr), "name": name, "error": str(e)})
    return hits, counters


def observe(seconds: float, burst: int) -> dict:
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    t0 = time.time()
    polls = edge_events = burst_samples = 0
    execlist_nonzero = 0
    sight = {}
    sight_first = {}
    leaf_hits = []
    cancel_n = assign_n = 0
    snapshots = []
    prev = None
    last = None

    while time.time() - t0 < seconds:
        polls += 1
        hits, last = sample(b, base, sess, server)
        if last.get("execlist_head") not in (None, "0x0", "0x0"):
            if last["execlist_head"] != "0x0":
                execlist_nonzero += 1
        edge = False
        if prev is not None:
            edge = (
                last["drain"] != prev["drain"]
                or last["exec"] != prev["exec"]
                or last["seq"] != prev["seq"]
            )
        if edge:
            edge_events += 1
            for _ in range(burst):
                burst_samples += 1
                h2, c2 = sample(b, base, sess, server)
                last = c2
                hits.extend(h2)
                if any(h.get("name") in LEAF_MOVE for h in h2):
                    break
        prev = dict(last)

        interesting = [h for h in hits if h.get("name") != "CHourlyTickCommand"]
        if interesting and len(snapshots) < 16:
            snapshots.append({"t": round(time.time() - t0, 2), "counters": dict(last), "hits": interesting[:20]})

        for h in hits:
            name = h.get("name") or "?"
            key = f"{h.get('list')}:{name}"
            sight[key] = sight.get(key, 0) + 1
            if name not in sight_first:
                sight_first[name] = {
                    "list": h.get("list"),
                    "addr": h.get("addr"),
                    "vt_rva": h.get("vt_rva"),
                    "poll": polls,
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            if name in LEAF_MOVE:
                leaf_hits.append(h)
            if name == "CCancelMovementCommand":
                cancel_n += 1
            if name in ("COrderAssignCommand", "COrderUnassignCommand"):
                assign_n += 1
        if leaf_hits:
            break

    uniq, seen = [], set()
    for h in leaf_hits:
        a = h.get("addr")
        if a in seen:
            continue
        seen.add(a)
        uniq.append(h)

    return {
        "pid": pid,
        "date": live_hours(b, base),
        "observe_seconds": round(time.time() - t0, 1),
        "polls": polls,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "execlist_nonzero_polls": execlist_nonzero,
        "sight_counts": sight,
        "sight_first": sight_first,
        "cancel_sightings": cancel_n,
        "assign_family_sightings": assign_n,
        "snapshots_tail": snapshots[-5:],
        "leaf_hits": uniq[:8],
        "last_counters": last,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="ETH")
    ap.add_argument("--speed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=100.0)
    ap.add_argument("--burst", type=int, default=24)
    ap.add_argument("--skip-relaunch", action="store_true")
    ap.add_argument("--map-timeout", type=float, default=240.0)
    args = ap.parse_args()

    if args.speed >= 5:
        print(json.dumps({"error": "never 5x"}))
        return 2

    launch_info = {"skipped": True}
    map_info = {"ok": True, "skipped": True}
    if not args.skip_relaunch:
        launch_info = relaunch(args.tag, args.speed)
        map_info = wait_map(args.map_timeout)
        if not map_info.get("ok"):
            # fallback note — still try observe if hoi4 up
            if not find_pid("hoi4.exe"):
                summary = {
                    "phase": "2fa",
                    "result": "ETH_RELAUNCH_MAP_FAIL",
                    "launch": launch_info,
                    "map": map_info,
                    "allow_post": False,
                }
                SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print(json.dumps(summary, indent=2))
                return 1

    obs = observe(args.seconds, args.burst)
    uniq = obs["leaf_hits"]
    if uniq:
        result = "LEAF_MOVE_CAPTURED_ETH"
        CAPTURE.write_text(
            json.dumps({"phase": "2fa", "allow_post": False, "captures": uniq, "tag": args.tag}, indent=2),
            encoding="utf-8",
        )
    elif obs["cancel_sightings"] or obs["assign_family_sightings"]:
        result = "ETH_EXECLIST_ORDER_TRAFFIC_NO_LEAF_MOVE"
    else:
        result = "ETH_EXECLIST_QUIET_NO_LEAF_MOVE"

    next_recipe = {
        "name": "Accept Move sample gap for SAFE_POST / layout-only ring_embed design",
        "steps": [
            "Do NOT endless-poll or Capstone/121 re-churn",
            "Document midflight leaf Move as STUBBED; Cancel/Assign path remains strongest adjacent proof",
            "Optional later: layout-only ring_embed design still gated by allow_post False",
        ],
        "forbid": ["ALLOW_POST", "Post inject", "5x", "ask right-click"],
    }

    report = {
        "phase": "2fa",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "tag": args.tag,
        "speed": args.speed,
        "launch": launch_info,
        "map": map_info,
        "observe": obs,
        "haiti_return": HAITI_RETURN,
        "ita_return": ITA_RETURN,
        "result": result,
        "next_cheapest_recipe": next_recipe,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    works = [
        f"relaunch {args.tag}@1x AI-on" if not args.skip_relaunch else f"kept {args.tag}@1x",
        f"execlist-only denser observe {obs['observe_seconds']}s polls={obs['polls']} edges={obs['edge_events']}",
        "no heap / no Post / never 5x",
        "allow_post stays False",
    ]
    if obs["cancel_sightings"]:
        works.append(f"Cancel sightings={obs['cancel_sightings']}")
    if uniq:
        works.append(f"LEAF: {[u.get('name') for u in uniq]}")

    stubbed = []
    if not uniq:
        stubbed.extend(["live CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand"])
    stubbed.extend(["ring_embed", "SAFE_POST", "self-issue MOVE"])

    summary = {
        "phase": "2fa",
        "result": result,
        "scenario": f"{args.tag} @1x AI-on",
        "pid": obs["pid"],
        "ui_date": (obs.get("date") or {}).get("ui_date"),
        "hours": (obs.get("date") or {}).get("hours"),
        "observe_seconds": obs["observe_seconds"],
        "polls": obs["polls"],
        "edge_events": obs["edge_events"],
        "execlist_nonzero_polls": obs["execlist_nonzero_polls"],
        "sight_counts": obs["sight_counts"],
        "cancel_sightings": obs["cancel_sightings"],
        "assign_family_sightings": obs["assign_family_sightings"],
        "leaf_names_hit": [u.get("name") for u in uniq],
        "map_player_tag": map_info.get("player_tag"),
        "allow_post": False,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": (
            "Decode leaf Move → ring_embed (still NO ALLOW_POST)"
            if uniq
            else next_recipe["name"] + " — still NO ALLOW_POST"
        ),
        "next_cheapest_recipe": next_recipe,
        "haiti_return": HAITI_RETURN,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    DOC.write_text(
        f"""# Phase 2fa — ETH denser execlist-only RO

**Result:** `{result}`  
**Scenario:** `{args.tag} @1x AI-on` pid {obs['pid']}  
**UI:** {(obs.get('date') or {}).get('ui_date')}  
**Observe:** {obs['observe_seconds']}s · polls {obs['polls']} · edges {obs['edge_events']}  
**execlist nonzero polls:** {obs['execlist_nonzero_polls']}  
**Cancel / Assign-family:** {obs['cancel_sightings']} / {obs['assign_family_sightings']}  
**Leaf Move:** {len(uniq)}

Sight: `{obs['sight_counts']}`

Return Haiti: `{HAITI_RETURN['recipe']}`  
Still **NO ALLOW_POST**. Never 5x.

Script: `scripts/phase2fa_eth_execlist.py`
""",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
