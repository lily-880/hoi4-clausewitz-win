"""Phase 2ikm: re-issue multi-Strategic concentrate → arrive → Attack.

Paths died after 2ikk/2ikl. Rebuild encircle loop with proven ABIs only.
Retreat PARKED. Instant PARKED.
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

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikm_reissue_concentrate_attack.json"
SUMMARY = ROOT / "reports" / "phase2ikm_reissue_concentrate_attack_summary.json"
DOC = ROOT / "docs" / "PHASE2IKM_REISSUE_CONCENTRATE_ATTACK.md"

CA_PROVINCE = 0x28
CONCENTRATE_DEST = 6906
ATTACK_TARGET = 1886
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
        f"OPEN safe_land for Phase 2ikm (t52u).\nScope: {scope}\n"
        "Retreat PARKED. Instant PARKED.\n",
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
                g["note"] = "2ikm reissue concentrate→Attack"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["posting"] = "LAND_GATED"
        data["last_phase"] = "2ikm"
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
                g["note"] = "Re-closed after 2ikm"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "closed"
        data["posting"] = "DISABLED"
        data["allow_post"] = False
        data["last_phase"] = "2ikm"
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
    return {
        "pid": pid,
        "ui_date": ui,
        "day_index": day,
        "player_tag": i32(b, gs + 0x518),
        "allow_post": allow_post(),
        "war_basis": "1936 ETH day-1 historical war vs ITA (continuation)",
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


def observe_stable(pid: int, seconds: float = 25.0) -> dict:
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


def bounded_arrive(pid, base, seconds=60.0):
    samples = []
    t0 = time.time()
    early = False
    while time.time() - t0 < seconds:
        if find_pid() != pid:
            samples.append({"t": round(time.time() - t0, 2), "dead": True})
            break
        b = Backend(pid)
        row = {
            "t": round(time.time() - t0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "armies": {str(ix): snap(b, base, ix) for ix in (*MOVERS, ANCHOR)},
        }
        at_conc = [ix for ix in (*MOVERS, ANCHOR) if row["armies"][str(ix)].get("at_concentrate")]
        enroute = [ix for ix in MOVERS if row["armies"][str(ix)].get("dest_in_path")]
        row["stack_at_concentrate"] = at_conc
        row["stack_depth"] = len(at_conc)
        row["enroute"] = enroute
        samples.append(row)
        if len(at_conc) >= 2:
            early = True
            break
        time.sleep(4.0)
    last = samples[-1] if samples else {}
    return {
        "seconds_budget": seconds,
        "early_stop_stack": early,
        "samples_n": len(samples),
        "compact": [
            {
                "t": s.get("t"),
                "ui": s.get("ui"),
                "provs": {
                    k: (v.get("province"), v.get("path_len"), v.get("dest_in_path"))
                    for k, v in (s.get("armies") or {}).items()
                },
                "stack_depth": s.get("stack_depth"),
                "enroute": s.get("enroute"),
            }
            for s in samples
        ],
        "last": last,
        "movers_arrived": all(
            (last.get("armies") or {}).get(str(i), {}).get("at_concentrate") for i in MOVERS
        )
        if last.get("armies")
        else False,
        "movers_enroute": any(
            (last.get("armies") or {}).get(str(i), {}).get("dest_in_path") for i in MOVERS
        )
        if last.get("armies")
        else False,
        "anchor_at_dest": bool((last.get("armies") or {}).get(str(ANCHOR), {}).get("at_concentrate")),
        "stack_depth": last.get("stack_depth") or 0,
        "gate_open": (last.get("stack_depth") or 0) >= 1
        or any((last.get("armies") or {}).get(str(i), {}).get("dest_in_path") for i in MOVERS),
    }


def post_attack_observe(pid, base, seconds=30.0):
    samples = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        if find_pid() != pid:
            break
        b = Backend(pid)
        samples.append(
            {
                "t": round(time.time() - t0, 2),
                "ui": continuum(b, base, pid).get("ui_date"),
                "armies": {str(ix): snap(b, base, ix) for ix in (*MOVERS, ANCHOR)},
            }
        )
        time.sleep(5.0)
    last = samples[-1]["armies"] if samples else {}
    return {
        "samples_n": len(samples),
        "compact": [
            {
                "t": s["t"],
                "ui": s.get("ui"),
                "provs": {k: (v.get("province"), v.get("path_len")) for k, v in s["armies"].items()},
            }
            for s in samples
        ],
        "synthesis": {
            "provinces": {k: v.get("province") for k, v in last.items()},
            "any_at_1886": any(v.get("at_attack_target") for v in last.values()),
            "stack_at_6906": [int(k) for k, v in last.items() if v.get("at_concentrate")],
            "any_path": any((v.get("path_len") or 0) > 0 for v in last.values()),
            "combat_densify": "HONEST_EMPTY",
            "adjacency": "HONEST_EMPTY",
        },
    }


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
        "decision": "PARKED — reissue concentrate→Attack",
    }

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)
    tag = live0["player_tag"]
    rows = []
    for lo in range(1000, 2000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    by = {int(r["index"]): r for r in rows}
    for need in (*MOVERS, ANCHOR):
        if need not in by:
            raise SystemExit(f"MISSING_ARMY_{need}")

    before = {str(ix): snap(b, base, ix) for ix in (*MOVERS, ANCHOR)}
    plan = {
        "bias": "REISSUE_MULTI_STRATEGIC_CONCENTRATE_THEN_MULTI_ATTACK",
        "movers": list(MOVERS),
        "anchor": ANCHOR,
        "concentrate_dest": CONCENTRATE_DEST,
        "attack_target": ATTACK_TARGET,
        "attack_target_source": "PRIOR_WARTIME_HIT_DEST",
        "before": before,
        "eth_army_n": len(rows),
        "occupancy_dest": Counter(int(r["province_id"]) for r in rows)[CONCENTRATE_DEST],
        "adjacency": "HONEST_EMPTY",
    }

    open_gates("multi Strategic 4753 + multi SupportAttack 3620 reissue")
    importlib.reload(cfg)
    from config import allow_post as apo

    if not apo():
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
        entry = {
            "army": idx,
            "src": src,
            "dest": CONCENTRATE_DEST,
            "dry": {k: dry.get(k) for k in ("ok", "result")},
            "post": None,
        }
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = so.strategic_redeploy(idx, CONCENTRATE_DEST, dry_run=False)
            entry["post"] = posted
            time.sleep(0.8)
        else:
            entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
        strat_posts.append(entry)

    arrive = bounded_arrive(pid, base, seconds=60.0)

    # Attack if gate: stack>=2 OR (anchor at dest + enroute/arrived) — match 2ikk pattern
    last = arrive["last"].get("armies") or {}
    stack_depth = arrive["stack_depth"]
    attackers = []
    if stack_depth >= 2:
        for ix in (*MOVERS, ANCHOR):
            if (last.get(str(ix)) or {}).get("at_concentrate"):
                attackers.append(ix)
            if len(attackers) >= 2:
                break
    else:
        # still allow Attack from anchor + mover if anchor at dest and strategic enroute/HIT (2ikk style)
        if arrive["anchor_at_dest"] and (arrive["movers_enroute"] or arrive["movers_arrived"] or stack_depth >= 1):
            attackers = [ANCHOR]
            for ix in MOVERS:
                if ix not in attackers:
                    attackers.append(ix)
                if len(attackers) >= 2:
                    break

    atk_posts = []
    if len(attackers) >= 2:
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
    else:
        # no attack — document
        pass

    close_gates()

    post_obs = post_attack_observe(pid, base, seconds=30.0)
    stab = observe_stable(pid, 25.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    importlib.reload(cfg)
    from config import allow_post as apf

    # ensure closed
    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    strat_hits = []
    for e in strat_posts:
        p = e.get("post") or {}
        if e.get("skipped"):
            strat_hits.append("SKIP")
        elif p.get("result") == "PATH_CONTAINS_DEST" or (
            p.get("ok") and CONCENTRATE_DEST in (p.get("path_after") or [])
        ):
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

    n_strat = strat_hits.count("HIT") + strat_hits.count("WEAK")
    n_atk = atk_hits.count("HIT")
    if n_strat >= 1 and n_atk >= 2:
        result = "G6_REISSUE_CONCENTRATE_ATTACK_HIT"
        estimate = "~98-99%"
        note = "+~1pp reissue concentrate→Attack after paths died"
        hit = True
    elif n_strat >= 1 and n_atk >= 1:
        result = "G6_REISSUE_CONCENTRATE_ATTACK_PARTIAL"
        estimate = "~97-99%"
        note = "+~0-1pp partial reissue"
        hit = False
    elif n_strat >= 1:
        result = "G6_REISSUE_CONCENTRATE_STRATEGIC_ONLY"
        estimate = "~97-99%"
        note = "Strategic reissued; Attack gate not met or fail"
        hit = False
    else:
        result = "G6_REISSUE_CONCENTRATE_ATTACK_FAIL"
        estimate = "~97-99%"
        note = "no Path-C bump"
        hit = False

    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikm"] = result
        data["last_phase"] = "2ikm"
        data["allow_post"] = False
        data["posting"] = "DISABLED"
        write_checklist(data)

    report = {
        "phase": "2ikm",
        "result": result,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "retreat": retreat,
        "plan": plan,
        "strategic_posts": [
            {
                "army": e.get("army"),
                "skipped": e.get("skipped"),
                "dry": e.get("dry"),
                "post_result": (e.get("post") or {}).get("result"),
                "post_rax": (e.get("post") or {}).get("post_rax"),
                "path_after_has_dest": CONCENTRATE_DEST in ((e.get("post") or {}).get("path_after") or []),
            }
            for e in strat_posts
        ],
        "strategic_hits": strat_hits,
        "arrive": {
            "seconds_budget": arrive["seconds_budget"],
            "early_stop_stack": arrive["early_stop_stack"],
            "samples_n": arrive["samples_n"],
            "movers_arrived": arrive["movers_arrived"],
            "movers_enroute": arrive["movers_enroute"],
            "anchor_at_dest": arrive["anchor_at_dest"],
            "stack_depth": arrive["stack_depth"],
            "gate_open": arrive["gate_open"],
            "compact": arrive["compact"],
        },
        "attackers": attackers[:2] if attackers else [],
        "attack_posts": atk_posts,
        "attack_hits": atk_hits,
        "post_attack_observe": post_obs,
        "stability": stab,
        "live0": live0,
        "live_after": live1,
        "instant": "PARKED",
        "final_allow_post": apf(),
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
            "prior_2ikl": "~97-99%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": note,
        },
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikm",
                "result": result,
                "HIT": hit,
                "strategic_hits": strat_hits,
                "attack_hits": atk_hits,
                "attackers": attackers[:2] if attackers else [],
                "arrive": {
                    "movers_arrived": arrive["movers_arrived"],
                    "movers_enroute": arrive["movers_enroute"],
                    "anchor_at_dest": arrive["anchor_at_dest"],
                    "stack_depth": arrive["stack_depth"],
                    "early_stop_stack": arrive["early_stop_stack"],
                },
                "post_obs_syn": post_obs.get("synthesis"),
                "stability": stab,
                "final_allow_post": apf(),
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
        f"""# Phase 2ikm — Reissue concentrate→Attack after paths died

**Result:** `{result}` HIT={hit}
**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x

## Strategic 4753 → {CONCENTRATE_DEST}
hits={strat_hits}

## Arrive (~60s max)
movers_arrived={arrive['movers_arrived']} enroute={arrive['movers_enroute']} stack={arrive['stack_depth']} early={arrive['early_stop_stack']}

## Attack 3620 → {ATTACK_TARGET}
attackers={attackers[:2] if attackers else []} hits={atk_hits}

## Post-observe
{post_obs.get('synthesis')}

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
                "attackers": attackers[:2] if attackers else [],
                "arrive": {
                    "movers_arrived": arrive["movers_arrived"],
                    "movers_enroute": arrive["movers_enroute"],
                    "anchor_at_dest": arrive["anchor_at_dest"],
                    "stack_depth": arrive["stack_depth"],
                    "early_stop_stack": arrive["early_stop_stack"],
                },
                "post_obs_syn": post_obs.get("synthesis"),
                "stability": stab,
                "allow_post": apf(),
                "estimate": estimate,
                "note": note,
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
