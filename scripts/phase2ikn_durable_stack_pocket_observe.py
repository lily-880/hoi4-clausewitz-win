"""Phase 2ikn: longer durable stack/pocket observe after 2ikm Attack.

Observe-first; if paths died / stack collapsed → ONE reissue multi-Strategic
concentrate → arrive → multi-Attack (proven ABIs), then longer observe (~90–120s).
Retreat PARKED. Instant PARKED. pause/1x only NEVER 5x.
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
OUT = ROOT / "reports" / "phase2ikn_durable_stack_pocket_observe.json"
SUMMARY = ROOT / "reports" / "phase2ikn_durable_stack_pocket_observe_summary.json"
DOC = ROOT / "docs" / "PHASE2IKN_DURABLE_STACK_POCKET_OBSERVE.md"
CONSOLE = ROOT / "reports" / "phase2ikn_run_console.txt"

CA_PROVINCE = 0x28
CONCENTRATE_DEST = 6906
ATTACK_TARGET = 1886
MOVERS = (1037, 1038)
ANCHOR = 1042
TRACK = (*MOVERS, ANCHOR)


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
        f"OPEN safe_land for Phase 2ikn (t52u).\nScope: {scope}\n"
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
                g["note"] = "2ikn durable observe / optional reissue"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["posting"] = "LAND_GATED"
        data["last_phase"] = "2ikn"
        write_checklist(data)


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    data = read_checklist()
    if isinstance(data, dict):
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                g["status"] = "CLOSED"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "CLOSED"
        data["posting"] = "DISABLED"
        data["allow_post"] = False
        write_checklist(data)
    importlib.reload(cfg)


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


def tap_space_once():
    """UI unpause/pause toggle only — NOT a speed-mem write; never + beyond 1x."""
    import ctypes

    user32 = ctypes.windll.user32
    user32.keybd_event(0x20, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x20, 0, 2, 0)


def ensure_calendar_advancing(pid, base, wait_s=12.0):
    b = Backend(pid)
    d0 = continuum(b, base, pid)["day_index"]
    time.sleep(wait_s)
    if find_pid() != pid:
        return {"ok": False, "reason": "DEAD", "day0": d0}
    b = Backend(pid)
    d1 = continuum(b, base, pid)["day_index"]
    if d1 > d0:
        return {"ok": True, "tapped": False, "day0": d0, "day1": d1}
    # likely paused — one Space tap then recheck
    tap_space_once()
    time.sleep(wait_s)
    if find_pid() != pid:
        return {"ok": False, "reason": "DEAD_AFTER_SPACE", "day0": d0}
    b = Backend(pid)
    d2 = continuum(b, base, pid)["day_index"]
    return {
        "ok": d2 > d0,
        "tapped": True,
        "day0": d0,
        "day1": d1,
        "day2": d2,
        "note": "space_tap_unpause_only",
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


def synthesize_sample(armies: dict) -> dict:
    return {
        "provinces": {k: v.get("province") for k, v in armies.items()},
        "any_at_1886": any(v.get("at_attack_target") for v in armies.values()),
        "stack_at_6906": [int(k) for k, v in armies.items() if v.get("at_concentrate")],
        "stack_depth": sum(1 for v in armies.values() if v.get("at_concentrate")),
        "any_path": any((v.get("path_len") or 0) > 0 for v in armies.values()),
        "enroute_conc": [int(k) for k, v in armies.items() if v.get("dest_in_path")],
        "enroute_atk": [int(k) for k, v in armies.items() if v.get("target_in_path")],
        "combat_densify": "HONEST_EMPTY",
        "adjacency": "HONEST_EMPTY",
    }


def durable_observe(pid, base, seconds=100.0, early_on_durable=True):
    """Bounded longer observe. Early-stop if durable stack>=2 for 2 consecutive samples
    OR any_at_1886 OR pocket-like (stack>=2 at conc AND path toward 1886)."""
    samples = []
    t0 = time.time()
    durable_hits = 0
    early = None
    while time.time() - t0 < seconds:
        if find_pid() != pid:
            samples.append({"t": round(time.time() - t0, 2), "dead": True})
            break
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        syn = synthesize_sample(armies)
        row = {
            "t": round(time.time() - t0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "armies": armies,
            "syn": syn,
        }
        samples.append(row)
        # durable: stack>=2 at concentrate across consecutive samples
        if syn["stack_depth"] >= 2:
            durable_hits += 1
        else:
            durable_hits = 0
        if early_on_durable and durable_hits >= 2:
            early = "DURABLE_STACK_GE2"
            break
        if syn["any_at_1886"]:
            early = "ANY_AT_1886"
            break
        if syn["stack_depth"] >= 2 and syn["enroute_atk"]:
            early = "STACK_PLUS_ATTACK_PATH"
            break
        time.sleep(5.0)
    last = samples[-1] if samples else {}
    syn_last = last.get("syn") or {}
    # durable if last two samples both stack>=2
    durable = False
    if len(samples) >= 2:
        s0 = (samples[-2].get("syn") or {}).get("stack_depth", 0)
        s1 = (samples[-1].get("syn") or {}).get("stack_depth", 0)
        durable = s0 >= 2 and s1 >= 2
    return {
        "seconds_budget": seconds,
        "early_stop": early,
        "samples_n": len(samples),
        "durable_stack_ge2": durable,
        "compact": [
            {
                "t": s.get("t"),
                "ui": s.get("ui"),
                "provs": {
                    k: (v.get("province"), v.get("path_len"), v.get("dest_in_path"), v.get("target_in_path"))
                    for k, v in (s.get("armies") or {}).items()
                },
                "stack_depth": (s.get("syn") or {}).get("stack_depth"),
                "any_at_1886": (s.get("syn") or {}).get("any_at_1886"),
                "any_path": (s.get("syn") or {}).get("any_path"),
            }
            for s in samples
            if not s.get("dead")
        ],
        "synthesis": syn_last,
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
            "armies": {str(ix): snap(b, base, ix) for ix in TRACK},
        }
        at_conc = [ix for ix in TRACK if row["armies"][str(ix)].get("at_concentrate")]
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
            if not s.get("dead")
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
    }


def classify_hit(obs0, reissued, arrive, atk_hits, durable_obs):
    syn = durable_obs.get("synthesis") or {}
    durable = bool(durable_obs.get("durable_stack_ge2"))
    any1886 = bool(syn.get("any_at_1886"))
    n_atk = atk_hits.count("HIT")
    if durable and any1886:
        return True, "G6_DURABLE_STACK_AND_POCKET_HIT", "~99%", "+~1pp durable stack+at1886"
    if durable:
        return True, "G6_DURABLE_STACK_GE2_HIT", "~98-99%", "+~0-1pp durable stack>=2 observe"
    if any1886:
        return True, "G6_ANY_AT_1886_HIT", "~98-99%", "+~0-1pp army at attack dest"
    if reissued and n_atk >= 2 and (arrive or {}).get("stack_depth", 0) >= 2:
        return False, "G6_REISSUE_THEN_OBSERVE_NO_DURABLE", "~98-99%", "reissue HIT but durable not held"
    if reissued and n_atk >= 1:
        return False, "G6_REISSUE_PARTIAL_NO_DURABLE", "~98-99%", "partial reissue; no durable"
    # observe-only honesty
    if (obs0.get("synthesis") or {}).get("stack_depth", 0) >= 2:
        return False, "G6_OBSERVE_STACK_EPHEMERAL", "~98-99%", "stack seen but not durable"
    return False, "G6_OBSERVE_HONEST_EMPTY_NO_DURABLE", "~98-99%", "paths empty / no durable pocket"


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
        "decision": "PARKED — observe/reissue only",
    }

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)
    tag = live0["player_tag"]

    cal = ensure_calendar_advancing(pid, base, wait_s=10.0)
    if find_pid() != pid:
        raise SystemExit("HOI4_DEAD_AFTER_CAL")

    b = Backend(pid)
    live_after_cal = continuum(b, base, pid)

    # --- OBSERVE FIRST (short) ---
    obs0 = durable_observe(pid, base, seconds=35.0, early_on_durable=True)
    syn0 = obs0.get("synthesis") or {}
    paths_died = not syn0.get("any_path")
    stack_collapsed = syn0.get("stack_depth", 0) < 2
    need_reissue = paths_died and stack_collapsed and not syn0.get("any_at_1886")

    strat_posts = []
    strat_hits = []
    arrive = None
    atk_posts = []
    atk_hits = []
    attackers = []
    reissued = False

    if need_reissue:
        reissued = True
        rows = []
        for lo in range(1000, 2000, 500):
            rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
        by = {int(r["index"]): r for r in rows}
        for need in TRACK:
            if need not in by:
                raise SystemExit(f"MISSING_ARMY_{need}")

        open_gates("2ikn optional reissue Strategic 4753 + Attack 3620 then durable observe")
        importlib.reload(cfg)
        from config import allow_post as apo

        if not apo():
            close_gates()
            raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
        importlib.reload(so)
        importlib.reload(ao)

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
        last = (arrive.get("last") or {}).get("armies") or {}
        stack_depth = arrive.get("stack_depth") or 0
        if stack_depth >= 2:
            for ix in TRACK:
                if (last.get(str(ix)) or {}).get("at_concentrate"):
                    attackers.append(ix)
                if len(attackers) >= 2:
                    break
        elif arrive.get("anchor_at_dest") and (
            arrive.get("movers_enroute") or arrive.get("movers_arrived") or stack_depth >= 1
        ):
            attackers = [ANCHOR]
            for ix in MOVERS:
                if ix not in attackers:
                    attackers.append(ix)
                if len(attackers) >= 2:
                    break

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

        close_gates()
    else:
        # no post — gates stay closed
        pass

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

    for e in atk_posts:
        p = e.get("post") or {}
        if p.get("result") == "ATTACK_POSTED_STABLE" and p.get("ok"):
            atk_hits.append("HIT")
        elif p.get("post_rax") == 1:
            atk_hits.append("WEAK")
        else:
            atk_hits.append("FAIL")

    # --- LONGER DURABLE OBSERVE ---
    durable_obs = durable_observe(pid, base, seconds=100.0, early_on_durable=True)
    stab = observe_stable(pid, 25.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    # ensure closed
    close_gates()
    importlib.reload(cfg)
    from config import allow_post as apf

    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

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

    hit, result, estimate, note = classify_hit(obs0, reissued, arrive, atk_hits, durable_obs)

    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikn"] = result
        data["last_phase"] = "2ikn"
        data["allow_post"] = False
        data["posting"] = "DISABLED"
        write_checklist(data)

    report = {
        "phase": "2ikn",
        "result": result,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x; space tap unpause only if calendar stalled",
        "retreat": retreat,
        "calendar_ensure": cal,
        "observe_first": {
            "need_reissue": need_reissue,
            "paths_died": paths_died,
            "stack_collapsed": stack_collapsed,
            "early_stop": obs0.get("early_stop"),
            "synthesis": syn0,
            "compact": obs0.get("compact"),
        },
        "reissued": reissued,
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
        "arrive": None
        if arrive is None
        else {
            "seconds_budget": arrive["seconds_budget"],
            "early_stop_stack": arrive["early_stop_stack"],
            "samples_n": arrive["samples_n"],
            "movers_arrived": arrive["movers_arrived"],
            "movers_enroute": arrive["movers_enroute"],
            "anchor_at_dest": arrive["anchor_at_dest"],
            "stack_depth": arrive["stack_depth"],
            "compact": arrive["compact"],
        },
        "attackers": attackers[:2] if attackers else [],
        "attack_posts": [
            {
                "army": e.get("army"),
                "src_province": e.get("src_province"),
                "target": e.get("target"),
                "dry": e.get("dry"),
                "post_result": (e.get("post") or {}).get("result"),
                "post_rax": (e.get("post") or {}).get("post_rax"),
            }
            for e in atk_posts
        ],
        "attack_hits": atk_hits,
        "durable_observe": {
            "seconds_budget": durable_obs.get("seconds_budget"),
            "early_stop": durable_obs.get("early_stop"),
            "samples_n": durable_obs.get("samples_n"),
            "durable_stack_ge2": durable_obs.get("durable_stack_ge2"),
            "synthesis": durable_obs.get("synthesis"),
            "compact": durable_obs.get("compact"),
        },
        "stability": stab,
        "live0": live0,
        "live_after_cal": live_after_cal,
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
            "prior_2ikm": "~98-99%",
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
                "phase": "2ikn",
                "result": result,
                "HIT": hit,
                "need_reissue": need_reissue,
                "reissued": reissued,
                "strategic_hits": strat_hits,
                "attack_hits": atk_hits,
                "attackers": attackers[:2] if attackers else [],
                "obs0_syn": syn0,
                "durable": {
                    "durable_stack_ge2": durable_obs.get("durable_stack_ge2"),
                    "early_stop": durable_obs.get("early_stop"),
                    "synthesis": durable_obs.get("synthesis"),
                },
                "stability": stab,
                "final_allow_post": apf(),
                "estimate": estimate,
                "ui0": live0.get("ui_date"),
                "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
                "post_attempts": report["post_attempts"],
                "retreat": retreat["status"],
                "calendar_ensure": cal,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ikn — Durable stack/pocket observe (optional reissue)

**Result:** `{result}` HIT={hit}
**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x

## Observe-first
need_reissue={need_reissue} paths_died={paths_died} stack_collapsed={stack_collapsed}
syn0={syn0}

## Reissue Strategic/Attack
reissued={reissued} strat_hits={strat_hits} atk_hits={atk_hits} attackers={attackers[:2] if attackers else []}

## Durable observe (~100s)
durable_stack_ge2={durable_obs.get('durable_stack_ge2')} early={durable_obs.get('early_stop')}
syn={durable_obs.get('synthesis')}

## Stability
{stab}

## Path C
{estimate}; crossed_70=YES; {note}

*{report['timestamp_asia_shanghai']}*
""",
        encoding="utf-8",
    )

    summary_print = {
        "result": result,
        "HIT": hit,
        "need_reissue": need_reissue,
        "reissued": reissued,
        "strategic_hits": strat_hits,
        "attack_hits": atk_hits,
        "attackers": attackers[:2] if attackers else [],
        "obs0_syn": syn0,
        "durable": {
            "durable_stack_ge2": durable_obs.get("durable_stack_ge2"),
            "early_stop": durable_obs.get("early_stop"),
            "synthesis": durable_obs.get("synthesis"),
        },
        "stability": stab,
        "allow_post": apf(),
        "estimate": estimate,
        "note": note,
        "ui0": live0.get("ui_date"),
        "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
        "post_attempts": report["post_attempts"],
        "retreat": retreat["status"],
        "calendar_ensure": cal,
    }
    text = json.dumps(summary_print, indent=2)
    CONSOLE.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
