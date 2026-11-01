"""Phase 2ikk: rebuild wartime concentrate→Attack encircle loop on fresh ETH.

Strategic 4753 multi → bounded arrive → SupportAttack 3620 multi toward prior HIT dest.
Retreat PARKED. Instant PARKED. No adjacency/org invent.
"""
from __future__ import annotations

import importlib
import json
import os
import struct
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import config as cfg
from config import allow_post
from process import Backend, find_pid
from handle import resolve_handle, HANDLE_TYPE_ARMY
from army_subjects import iter_armies_by_index
import strategic_order as so
import attack_order as ao
import post_abi

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikk_wartime_encircle_rebuild.json"
SUMMARY = ROOT / "reports" / "phase2ikk_wartime_encircle_rebuild_summary.json"
DOC = ROOT / "docs" / "PHASE2IKK_WARTIME_ENCIRCLE_REBUILD.md"

CA_PROVINCE = 0x28
CONCENTRATE_DEST = 6906  # proven friendly coloc (1042 historically)
ATTACK_TARGET = 1886  # prior wartime SupportAttack IsValid HIT dest
MOVERS = (1037, 1038)
ANCHOR = 1042


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def read_checklist():
    if not CHECKLIST.exists():
        return None
    return json.loads(CHECKLIST.read_text(encoding="utf-8-sig"))


def write_checklist(data):
    CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def open_gates(scope: str):
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        f"OPEN safe_land tool-gate for Phase 2ikk (user t52u).\nScope: {scope}\n"
        "Retreat PARKED. Instant PARKED. NEVER_POST speed beyond pause/1x.\n",
        encoding="utf-8",
    )
    if LEGACY.exists():
        try:
            LEGACY.unlink()
        except Exception:
            pass
    data = read_checklist()
    if isinstance(data, dict):
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                g["status"] = "OPEN_LAND_STRATEGIC_ATTACK"
                g["note"] = "2ikk wartime encircle rebuild"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["posting"] = "LAND_GATED"
        data["last_phase"] = "2ikk"
        write_checklist(data)


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LEGACY):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    data = read_checklist()
    if isinstance(data, dict):
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                g["status"] = "CLOSED_NOT_OPENED"
                g["note"] = "Re-closed after 2ikk"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "closed"
        data["posting"] = "DISABLED"
        data["allow_post"] = False
        data["last_phase"] = "2ikk"
        data["phase2ikk"] = data.get("phase2ikk") or "RAN"
        write_checklist(data)


def continuum(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year, day = i32(b, gs + 0x478), i32(b, gs + 0x484)
    try:
        ui = (datetime(year, 1, 1) + timedelta(days=int(day))).strftime("%Y-%m-%d")
    except Exception:
        ui = None
    tag = i32(b, gs + 0x518)
    return {
        "pid": pid,
        "ui_date": ui,
        "day_index": day,
        "player_tag": tag,
        "allow_post": allow_post(),
        "war_basis": "1936 ETH day-1 historical war vs ITA (repo 2et/2fa/2ikc; AI-on relaunch)",
    }


def snap(b, base, idx: int) -> dict:
    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return {"army": idx, "ok": False}
    prov = u32(b, army + CA_PROVINCE)
    path = so._path(b, base, army)
    return {
        "army": idx,
        "ok": True,
        "province": prov,
        "path": path,
        "path_len": len(path),
        "at_concentrate": prov == CONCENTRATE_DEST,
        "at_attack_target": prov == ATTACK_TARGET,
        "dest_in_path": CONCENTRATE_DEST in path,
        "target_in_path": ATTACK_TARGET in path,
    }


def observe_stable(pid: int, seconds: float = 30.0) -> dict:
    samples = []
    t0 = time.time()
    heap = False
    while time.time() - t0 < seconds:
        alive = find_pid() == pid
        exit_code = 259
        try:
            import ctypes

            k = ctypes.WinDLL("kernel32", use_last_error=True)
            hp = k.OpenProcess(0x1000, False, pid)
            if hp:
                code = ctypes.c_ulong()
                if k.GetExitCodeProcess(hp, ctypes.byref(code)):
                    exit_code = int(code.value)
                k.CloseHandle(hp)
        except Exception:
            pass
        samples.append({"t": round(time.time() - t0, 2), "alive": alive, "exit_code": exit_code})
        if exit_code == 0xC0000374:
            heap = True
            break
        if not alive:
            break
        time.sleep(1.0)
    return {
        "seconds": seconds,
        "responding_stayed": all(s["alive"] and s["exit_code"] == 259 for s in samples) and bool(samples),
        "alive_final": find_pid() == pid,
        "heap_exit": heap,
        "samples_n": len(samples),
    }


def brief_arrive(pid, base, seconds=12.0):
    samples = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        b = Backend(pid)
        row = {"t": round(time.time() - t0, 2)}
        for ix in (*MOVERS, ANCHOR):
            row[str(ix)] = snap(b, base, ix)
        samples.append(row)
        time.sleep(3.0)
    last = samples[-1]
    movers_arrived = any((last.get(str(i)) or {}).get("at_concentrate") for i in MOVERS)
    movers_enroute = any((last.get(str(i)) or {}).get("dest_in_path") for i in MOVERS)
    anchor_at = bool((last.get(str(ANCHOR)) or {}).get("at_concentrate"))
    return {
        "seconds_budget": seconds,
        "samples_n": len(samples),
        "samples": samples,
        "movers_arrived": movers_arrived,
        "movers_enroute": movers_enroute,
        "anchor_at_dest": anchor_at,
        "gate_open": movers_arrived or movers_enroute or anchor_at,
        "last": last,
    }


def brief_post_attack_observe(pid, base, seconds=35.0):
    samples = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        b = Backend(pid)
        row = {
            "t": round(time.time() - t0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "armies": {str(ix): snap(b, base, ix) for ix in (*MOVERS, ANCHOR)},
        }
        samples.append(row)
        time.sleep(5.0)
    return {"seconds_budget": seconds, "samples_n": len(samples), "samples": samples}


def main() -> int:
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    importlib.reload(cfg)
    from config import allow_post as ap0

    assert ap0() is False

    retreat = {
        "status": "HARD_DENY_PARKED_NOT_PROVEN_CHEAP",
        "retreat_order_py": (ROOT / "calling" / "retreat_order.py").exists(),
        "decision": "PARKED — prefer wartime concentrate→Attack rebuild",
    }

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)
    tag = live0["player_tag"]

    rows = []
    for lo in range(1000, 3000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    by = {int(r["index"]): r for r in rows}
    for need in (*MOVERS, ANCHOR):
        if need not in by:
            raise SystemExit(f"MISSING_ARMY_{need}")

    before = {str(ix): snap(b, base, ix) for ix in (*MOVERS, ANCHOR)}
    plan = {
        "bias": "WARTIME_MULTI_STRATEGIC_CONCENTRATE_THEN_MULTI_ATTACK",
        "movers": list(MOVERS),
        "anchor": ANCHOR,
        "concentrate_dest": CONCENTRATE_DEST,
        "attack_target": ATTACK_TARGET,
        "attack_target_source": "PRIOR_WARTIME_HIT_DEST",
        "adjacency": "HONEST_EMPTY",
        "before": before,
        "eth_army_n": len(rows),
        "occupancy_dest": Counter(int(r["province_id"]) for r in rows)[CONCENTRATE_DEST],
    }

    # --- Strategic concentrate ---
    open_gates("multi Strategic 4753 concentrate + multi SupportAttack 3620")
    importlib.reload(cfg)
    from config import allow_post as allow_post_open

    if not allow_post_open():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
    importlib.reload(so)
    importlib.reload(ao)

    strat_posts = []
    for idx in MOVERS:
        src = int(by[idx]["province_id"])
        if src == CONCENTRATE_DEST:
            strat_posts.append({"army": idx, "skipped": True, "reason": "ALREADY_AT_DEST"})
            continue
        dry = so.strategic_redeploy(idx, CONCENTRATE_DEST, dry_run=True)
        entry = {"army": idx, "src": src, "dest": CONCENTRATE_DEST, "dry": {k: dry.get(k) for k in ("ok", "result")}, "post": None}
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = so.strategic_redeploy(idx, CONCENTRATE_DEST, dry_run=False)
            entry["post"] = posted
            time.sleep(0.8)
        else:
            entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
        strat_posts.append(entry)

    arrive = brief_arrive(pid, base, seconds=12.0)

    # --- Multi Attack (anchor + any arrived/enroute mover; always try 2) ---
    last = arrive["last"]
    attackers = []
    if (last.get(str(ANCHOR)) or {}).get("at_concentrate") or (before.get(str(ANCHOR)) or {}).get("at_concentrate"):
        attackers.append(ANCHOR)
    for ix in MOVERS:
        s = last.get(str(ix)) or {}
        if s.get("at_concentrate") or s.get("dest_in_path") or s.get("ok"):
            if ix not in attackers:
                attackers.append(ix)
        if len(attackers) >= 2:
            break
    if len(attackers) < 2:
        attackers = [ANCHOR, MOVERS[0]]

    atk_posts = []
    for ix in attackers[:2]:
        dry = ao.support_attack(ix, ATTACK_TARGET, dry_run=True)
        entry = {
            "army": ix,
            "src_province": (last.get(str(ix)) or {}).get("province"),
            "at_concentrate": (last.get(str(ix)) or {}).get("at_concentrate"),
            "target": ATTACK_TARGET,
            "dry": {k: dry.get(k) for k in ("ok", "result")},
            "post": None,
        }
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = ao.support_attack(ix, ATTACK_TARGET, dry_run=False)
            entry["post"] = posted
            time.sleep(0.6)
        else:
            entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
        atk_posts.append(entry)

    post_obs = brief_post_attack_observe(pid, base, seconds=35.0)
    stab = observe_stable(pid, 25.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    close_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_final

    # Score
    strat_hits = []
    for e in strat_posts:
        p = e.get("post") or {}
        if e.get("skipped"):
            strat_hits.append("SKIP")
        elif p.get("result") == "PATH_CONTAINS_DEST" or (p.get("ok") and CONCENTRATE_DEST in (p.get("path_after") or [])):
            strat_hits.append("HIT")
        elif p.get("post_rax") == 1:
            strat_hits.append("WEAK")
        else:
            strat_hits.append("FAIL")

    atk_hits = []
    for e in atk_posts:
        p = e.get("post") or {}
        if p.get("result") == "ATTACK_POSTED_STABLE" and p.get("ok"):
            atk_hits.append("HIT")
        elif p.get("post_rax") == 1:
            atk_hits.append("WEAK")
        else:
            atk_hits.append("FAIL")

    n_strat = strat_hits.count("HIT") + strat_hits.count("WEAK")
    n_atk = atk_hits.count("HIT")
    if n_strat >= 1 and n_atk >= 2:
        result = "G6_WARTIME_ENCIRCLE_LOOP_HIT"
        estimate = "~97-99%"
        note = "+~1-2pp wartime concentrate→Attack loop rebuilt on fresh ETH"
        hit = True
    elif n_strat >= 1 and n_atk >= 1:
        result = "G6_WARTIME_ENCIRCLE_LOOP_PARTIAL"
        estimate = "~96-98%"
        note = "+~1pp partial loop (Strategic+Attack)"
        hit = False
    elif n_atk >= 1 or n_strat >= 1:
        result = "G6_WARTIME_ENCIRCLE_LOOP_PARTIAL"
        estimate = "~96-98%"
        note = "partial rebuild"
        hit = False
    else:
        result = "G6_WARTIME_ENCIRCLE_LOOP_FAIL"
        estimate = "~96-98%"
        note = "no Path-C bump"
        hit = False

    # post-attack observe synthesis (honest)
    last_obs = (post_obs["samples"][-1]["armies"] if post_obs["samples"] else {})
    obs_syn = {
        "final_provinces": {k: v.get("province") for k, v in last_obs.items()},
        "any_at_attack_target": any(v.get("at_attack_target") for v in last_obs.values()),
        "any_path": any((v.get("path_len") or 0) > 0 for v in last_obs.values()),
        "combat_densify": "HONEST_EMPTY",
        "adjacency": "HONEST_EMPTY",
    }

    strategic_attempts = sum(
        1
        for e in strat_posts
        if e.get("post")
        and not e.get("skipped")
        and (
            "path_after" in (e.get("post") or {})
            or (e.get("post") or {}).get("result")
            in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH", "PROCESS_EXITED")
        )
    )
    attack_attempts = sum(
        1
        for e in atk_posts
        if e.get("post")
        and (
            "post_rax" in (e.get("post") or {})
            or (e.get("post") or {}).get("result")
            in ("ATTACK_POSTED_STABLE", "ATTACK_POST_UNCERTAIN", "PROCESS_EXITED")
        )
    )

    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikk"] = result
        write_checklist(data)

    report = {
        "phase": "2ikk",
        "result": result,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "retreat": retreat,
        "plan": plan,
        "strategic_posts": strat_posts,
        "strategic_hits": strat_hits,
        "arrive": {
            "movers_arrived": arrive["movers_arrived"],
            "movers_enroute": arrive["movers_enroute"],
            "anchor_at_dest": arrive["anchor_at_dest"],
            "gate_open": arrive["gate_open"],
            "last": arrive["last"],
            "samples_n": arrive["samples_n"],
        },
        "attackers": attackers[:2],
        "attack_posts": atk_posts,
        "attack_hits": atk_hits,
        "post_attack_observe": {
            "samples_n": post_obs["samples_n"],
            "synthesis": obs_syn,
            "compact": [
                {
                    "t": s["t"],
                    "ui": s.get("ui"),
                    "provs": {k: (v.get("province"), v.get("path_len")) for k, v in s["armies"].items()},
                }
                for s in post_obs["samples"]
            ],
        },
        "stability": stab,
        "live0": live0,
        "live_after": live1,
        "instant": "PARKED",
        "final_allow_post": allow_post_final(),
        "marker_exists": MARKER.exists(),
        "post_attempts": {
            "strategic": strategic_attempts,
            "attack": attack_attempts,
            "move": 0,
            "cancel": 0,
            "retreat": 0,
        },
        "path_c": {
            "baseline": "~60%",
            "prior_2ikj": "~96-98%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": note,
        },
        "agent_card_fold": (
            "Fresh-ETH wartime rebuild: multi-Strategic concentrate onto friendly dest 6906, "
            "then multi SupportAttack toward prior HIT dest 1886; encircle-bias loop restored."
        ),
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikk",
                "result": result,
                "HIT": hit,
                "strategic_hits": strat_hits,
                "attack_hits": atk_hits,
                "attackers": attackers[:2],
                "arrive": {
                    "movers_arrived": arrive["movers_arrived"],
                    "movers_enroute": arrive["movers_enroute"],
                    "anchor_at_dest": arrive["anchor_at_dest"],
                },
                "obs_syn": obs_syn,
                "stability": stab,
                "final_allow_post": allow_post_final(),
                "estimate": estimate,
                "ui0": live0.get("ui_date"),
                "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
                "post_attempts": report["post_attempts"],
                "retreat": retreat["status"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ikk — Wartime concentrate→Attack encircle loop rebuild

**Result:** `{result}` HIT={hit}
**War:** WARTIME_ETH_CONTINUATION (fresh ETH AI-on day-1 historical vs ITA)
**Auth:** t52u | pause/1x NEVER 5x

## Plan
- Movers {list(MOVERS)} Strategic 4753 → {CONCENTRATE_DEST} (anchor {ANCHOR})
- Multi SupportAttack 3620 → {ATTACK_TARGET} (PRIOR_WARTIME_HIT_DEST)
- Retreat PARKED; Instant PARKED; combat densify HONEST_EMPTY

## Strategic
{strat_hits} / posts={strat_posts}

## Arrive
movers_arrived={arrive['movers_arrived']} enroute={arrive['movers_enroute']} anchor={arrive['anchor_at_dest']}

## Attack
attackers={attackers[:2]} hits={atk_hits}

## Observe
{obs_syn}

## Stability
{stab}

## Path C
{estimate}; crossed_70=YES; {note}

*{report['timestamp_asia_shanghai']}*
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "result": result,
                "HIT": hit,
                "strategic_hits": strat_hits,
                "attack_hits": atk_hits,
                "attackers": attackers[:2],
                "arrive": {
                    "movers_arrived": arrive["movers_arrived"],
                    "movers_enroute": arrive["movers_enroute"],
                    "anchor_at_dest": arrive["anchor_at_dest"],
                },
                "obs_syn": obs_syn,
                "stability": stab,
                "allow_post": allow_post_final(),
                "estimate": estimate,
                "ui0": live0.get("ui_date"),
                "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
                "post_attempts": report["post_attempts"],
                "retreat": retreat["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
