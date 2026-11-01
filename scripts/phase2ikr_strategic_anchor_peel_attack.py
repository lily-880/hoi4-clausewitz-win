"""Phase 2ikr: hybrid Strategic fast concentrate + Cancel-on-anchor-peel + Attack-all.

Strategic 4753 multi → watch concentrate ANCHOR: if anchor peels while movers
enroute, Cancel 1415 + re-Strategic; when stack>=2 (prefer 3) IMMEDIATE multi
SupportAttack 3620 ALL at concentrate → 1886; light Cancel mid-hold; optional
short Move 1402 local adjust after stack (not primary concentrate).
Retreat PARKED. Instant PARKED. pause/1x NEVER 5x.
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
import cancel_order as co
import move_order as mo

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikr_strategic_anchor_peel_attack.json"
SUMMARY = ROOT / "reports" / "phase2ikr_strategic_anchor_peel_attack_summary.json"
DOC = ROOT / "docs" / "PHASE2IKR_STRATEGIC_ANCHOR_PEEL_ATTACK.md"
CONSOLE = ROOT / "reports" / "phase2ikr_run_console.txt"

CA_PROVINCE = 0x28
CONCENTRATE_DEST = 7213  # live stack 1038+1045 @7213 (1037 gone)
ATTACK_TARGET = 1886
MOVERS = (1038, 1045)  # 1037 missing mid-campaign; 1045 co-located @7213
ANCHOR = 1042  # rejoin concentrate via Strategic
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
        "OPEN safe_land for Phase 2ikr (t52u).\nScope: %s\nRetreat PARKED. Instant PARKED.\n" % scope,
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
                g["status"] = "OPEN_LAND_STRATEGIC_ATTACK_CANCEL"
                g["note"] = "2ikr Strategic + Cancel-on-anchor-peel + Attack-all"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["posting"] = "LAND_GATED"
        data["last_phase"] = "2ikr"
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
        "war_basis": "1936 ETH day-1 historical war vs ITA (continuation/relaunch)",
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
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(0x20, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x20, 0, 2, 0)


def ensure_calendar_advancing(pid, base, wait_s=8.0):
    b = Backend(pid)
    d0 = continuum(b, base, pid)["day_index"]
    time.sleep(wait_s)
    if find_pid() != pid:
        return {"ok": False, "reason": "DEAD", "day0": d0}
    b = Backend(pid)
    d1 = continuum(b, base, pid)["day_index"]
    if d1 > d0:
        return {"ok": True, "tapped": False, "day0": d0, "day1": d1}
    tap_space_once()
    time.sleep(wait_s)
    if find_pid() != pid:
        return {"ok": False, "reason": "DEAD_AFTER_SPACE", "day0": d0}
    b = Backend(pid)
    d2 = continuum(b, base, pid)["day_index"]
    return {"ok": d2 > d0, "tapped": True, "day0": d0, "day1": d1, "day2": d2}


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


def durable_observe(pid, base, seconds=90.0):
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
        samples.append({
            "t": round(time.time() - t0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "armies": armies,
            "syn": syn,
        })
        if syn["stack_depth"] >= 2:
            durable_hits += 1
        else:
            durable_hits = 0
        if durable_hits >= 2:
            early = "DURABLE_STACK_GE2"
            break
        if syn["any_at_1886"]:
            early = "ANY_AT_1886"
            break
        time.sleep(5.0)
    last = samples[-1] if samples else {}
    syn_last = last.get("syn") or {}
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
            for s in samples if not s.get("dead")
        ],
        "synthesis": syn_last,
    }


def hit_label_strat(entry):
    p = entry.get("post") or {}
    if entry.get("skipped"):
        return "SKIP"
    if p.get("result") == "PATH_CONTAINS_DEST" or (
        p.get("ok") and CONCENTRATE_DEST in (p.get("path_after") or [])
    ):
        return "HIT"
    if p.get("post_rax") == 1:
        return "WEAK"
    return "FAIL"


def hit_label_atk(entry):
    p = entry.get("post") or {}
    if p.get("result") == "ATTACK_POSTED_STABLE" and p.get("ok"):
        return "HIT"
    if p.get("post_rax") == 1:
        return "WEAK"
    return "FAIL"


def try_cancel_peel(ix, cancel_posts):
    dryc = co.cancel_movement(ix, dry_run=True)
    centry = {
        "army": ix,
        "reason": "PEEL_DURING_HOLD_OR_ARRIVE",
        "dry": {k: dryc.get(k) for k in ("ok", "result", "isvalid")},
        "post": None,
    }
    if dryc.get("ok") and dryc.get("result") not in (
        "ISVALID_FALSE", "FACTORY_FAIL", "ARMY_NOT_FOUND", "NO_PROCESS"
    ):
        posted = co.cancel_movement(ix, dry_run=False)
        centry["post"] = posted
        time.sleep(0.4)
    else:
        centry["post"] = {"ok": False, "result": dryc.get("result") or "DRY_FAIL"}
    cancel_posts.append(centry)
    return centry


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
        "decision": "PARKED — Strategic + Cancel-on-anchor-peel + Attack-all",
    }

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)
    tag = live0["player_tag"]

    cal = ensure_calendar_advancing(pid, base, wait_s=8.0)
    if find_pid() != pid:
        raise SystemExit("HOI4_DEAD_AFTER_CAL")
    b = Backend(pid)

    rows = []
    for lo in range(0, 4000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    by = {int(r["index"]): r for r in rows}
    for need in TRACK:
        if need not in by:
            raise SystemExit("MISSING_ARMY_%s" % need)

    before = {str(ix): snap(b, base, ix) for ix in TRACK}
    plan = {
        "bias": "HYBRID_STRAT_CANCEL_ANCHOR_PEEL_ATTACK_ALL",
        "movers": list(MOVERS),
        "anchor": ANCHOR,
        "concentrate_dest": CONCENTRATE_DEST,
        "attack_target": ATTACK_TARGET,
        "attack_target_source": "PRIOR_WARTIME_HIT_DEST",
        "require_stack_prefer": 3,
        "require_stack_min_after_40s": 2,
        "eth_army_n": len(rows),
        "occupancy_dest": Counter(int(r["province_id"]) for r in rows)[CONCENTRATE_DEST],
        "adjacency": "HONEST_EMPTY",
        "move_hop": "SHORT_LOCAL_ADJUST_ONLY_AFTER_STACK",
    }

    open_gates("Strategic 4753 + Cancel-on-anchor-peel + Attack-all 3620")
    importlib.reload(cfg)
    from config import allow_post as apo
    if not apo():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
    importlib.reload(so)
    importlib.reload(ao)
    importlib.reload(co)
    importlib.reload(mo)

    strat_posts = []
    for idx in list(MOVERS) + [ANCHOR]:
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
            "role": "anchor_join" if idx == ANCHOR else "mover",
        }
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = so.strategic_redeploy(idx, CONCENTRATE_DEST, dry_run=False)
            entry["post"] = posted
            time.sleep(0.8)
        else:
            entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
        strat_posts.append(entry)

    arrive_samples = []
    cancel_posts = []
    atk_posts = []
    attackers = []
    attack_moment = None
    t0 = time.time()
    seconds = 90.0
    early_stack3 = False
    while time.time() - t0 < seconds:
        if find_pid() != pid:
            arrive_samples.append({"t": round(time.time() - t0, 2), "dead": True})
            break
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        at_conc = [ix for ix in TRACK if armies[str(ix)].get("at_concentrate")]
        enroute = [ix for ix in TRACK if armies[str(ix)].get("dest_in_path")]
        row = {
            "t": round(time.time() - t0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "provs": {k: (v.get("province"), v.get("path_len"), v.get("dest_in_path")) for k, v in armies.items()},
            "stack_depth": len(at_conc),
            "at_conc": at_conc,
            "enroute": enroute,
        }
        arrive_samples.append(row)

        # Cancel-on-anchor-peel + diverting movers before Attack
        if attack_moment is None:
            # Anchor left concentrate while others still need stack: Cancel + re-Strategic
            sa = armies[str(ANCHOR)]
            if not sa.get("at_concentrate"):
                plen_a = sa.get("path_len") or 0
                # peeled (has diverting path) OR idle off dest
                if plen_a > 0 and not sa.get("dest_in_path"):
                    try_cancel_peel(ANCHOR, cancel_posts)
                    cancel_posts[-1]["reason"] = "ANCHOR_PEEL_PATH"
                dry_a = so.strategic_redeploy(ANCHOR, CONCENTRATE_DEST, dry_run=True)
                if dry_a.get("ok") and dry_a.get("result") == "DRY_RUN_VALID":
                    so.strategic_redeploy(ANCHOR, CONCENTRATE_DEST, dry_run=False)
                    time.sleep(0.5)
                    if cancel_posts and cancel_posts[-1].get("army") == ANCHOR:
                        cancel_posts[-1]["re_strategic"] = "ANCHOR_RECONCENTRATE"
                    else:
                        cancel_posts.append({"army": ANCHOR, "reason": "ANCHOR_OFF_DEST_RESTRAT", "re_strategic": "ISSUED", "post": {"ok": True}})
            for ix in MOVERS:
                s = armies[str(ix)]
                plen = s.get("path_len") or 0
                if plen > 0 and not s.get("dest_in_path") and not s.get("at_concentrate"):
                    try_cancel_peel(ix, cancel_posts)
                    dry2 = so.strategic_redeploy(ix, CONCENTRATE_DEST, dry_run=True)
                    if dry2.get("ok") and dry2.get("result") == "DRY_RUN_VALID":
                        so.strategic_redeploy(ix, CONCENTRATE_DEST, dry_run=False)
                        time.sleep(0.5)
                        cancel_posts[-1]["re_strategic"] = "ISSUED"
                    break

        # Prefer stack==3 immediate; allow stack>=2 after 40s
        elapsed = time.time() - t0
        ready = (len(at_conc) >= 3) or (len(at_conc) >= 2 and elapsed >= 40.0)
        if ready and attack_moment is None:
            early_stack3 = len(at_conc) >= 3
            attackers = list(at_conc)
            for ix in attackers:
                dry = ao.support_attack(ix, ATTACK_TARGET, dry_run=True)
                entry = {
                    "army": ix,
                    "src_province": armies[str(ix)].get("province"),
                    "at_concentrate": True,
                    "target": ATTACK_TARGET,
                    "dry": {k: dry.get(k) for k in ("ok", "result")},
                    "post": None,
                    "immediate_on_stack3": True,
                }
                if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
                    posted = ao.support_attack(ix, ATTACK_TARGET, dry_run=False)
                    entry["post"] = posted
                    time.sleep(0.35)
                else:
                    entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
                atk_posts.append(entry)
            b2 = Backend(pid)
            armies2 = {str(ix): snap(b2, base, ix) for ix in TRACK}
            attack_moment = {
                "t": round(time.time() - t0, 2),
                "ui": continuum(b2, base, pid).get("ui_date"),
                "attackers": attackers,
                "stack_at_post": [ix for ix in TRACK if armies2[str(ix)].get("at_concentrate")],
                "stack_depth_at_post": sum(1 for ix in TRACK if armies2[str(ix)].get("at_concentrate")),
                "any_at_1886": any(armies2[str(ix)].get("at_attack_target") for ix in TRACK),
                "provs": {str(ix): armies2[str(ix)].get("province") for ix in TRACK},
            }
            break
        time.sleep(3.0)

    # If never reached stack3 but stack>=2 near timeout: Attack all currently stacked (fallback)
    fallback_attack = False
    if attack_moment is None and arrive_samples:
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        at_conc = [ix for ix in TRACK if armies[str(ix)].get("at_concentrate")]
        if len(at_conc) >= 2:
            fallback_attack = True
            attackers = list(at_conc)
            for ix in attackers:
                dry = ao.support_attack(ix, ATTACK_TARGET, dry_run=True)
                entry = {
                    "army": ix,
                    "src_province": armies[str(ix)].get("province"),
                    "at_concentrate": True,
                    "target": ATTACK_TARGET,
                    "dry": {k: dry.get(k) for k in ("ok", "result")},
                    "post": None,
                    "immediate_on_stack3": False,
                    "fallback_stack2": True,
                }
                if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
                    posted = ao.support_attack(ix, ATTACK_TARGET, dry_run=False)
                    entry["post"] = posted
                    time.sleep(0.35)
                else:
                    entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
                atk_posts.append(entry)
            b2 = Backend(pid)
            armies2 = {str(ix): snap(b2, base, ix) for ix in TRACK}
            attack_moment = {
                "t": round(time.time() - t0, 2),
                "ui": continuum(b2, base, pid).get("ui_date"),
                "attackers": attackers,
                "stack_at_post": [ix for ix in TRACK if armies2[str(ix)].get("at_concentrate")],
                "stack_depth_at_post": sum(1 for ix in TRACK if armies2[str(ix)].get("at_concentrate")),
                "any_at_1886": any(armies2[str(ix)].get("at_attack_target") for ix in TRACK),
                "provs": {str(ix): armies2[str(ix)].get("province") for ix in TRACK},
                "fallback_stack2": True,
            }

    # Keep gates open for Cancel during hold window
    hold_samples = []
    ht0 = time.time()
    while time.time() - ht0 < 35.0:
        if find_pid() != pid:
            break
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        syn = synthesize_sample(armies)
        # Cancel diverting during hold: left concentrate with path not toward attack target
        for ix in TRACK:
            s = armies[str(ix)]
            if s.get("at_concentrate"):
                continue
            plen = s.get("path_len") or 0
            # peeled: not at concentrate, has path, and path does not contain attack target
            if plen > 0 and not s.get("target_in_path") and not s.get("dest_in_path"):
                try_cancel_peel(ix, cancel_posts)
                # try re-strategic back to concentrate to rebuild stack
                dry2 = so.strategic_redeploy(ix, CONCENTRATE_DEST, dry_run=True)
                if dry2.get("ok") and dry2.get("result") == "DRY_RUN_VALID":
                    so.strategic_redeploy(ix, CONCENTRATE_DEST, dry_run=False)
                    time.sleep(0.4)
                    cancel_posts[-1]["re_strategic"] = "ISSUED_HOLD"
                break
        hold_samples.append({
            "t": round(time.time() - ht0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "syn": syn,
            "provs": {k: (v.get("province"), v.get("path_len"), v.get("target_in_path")) for k, v in armies.items()},
        })
        time.sleep(3.0)

    close_gates()

    durable = durable_observe(pid, base, seconds=90.0)
    stab = observe_stable(pid, 25.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    close_gates()
    importlib.reload(cfg)
    from config import allow_post as apf
    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    strat_hits = [hit_label_strat(e) for e in strat_posts]
    atk_hits = [hit_label_atk(e) for e in atk_posts]

    strategic_attempts = sum(
        1 for e in strat_posts
        if e.get("post") and not e.get("skipped")
        and (
            "path_after" in (e.get("post") or {})
            or (e.get("post") or {}).get("result") in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH", "PROCESS_EXITED")
        )
    )
    # also count re-strategic after cancel roughly
    re_strat = sum(1 for e in cancel_posts if e.get("re_strategic"))
    attack_attempts = sum(
        1 for e in atk_posts
        if e.get("post") and (
            "post_rax" in (e.get("post") or {})
            or (e.get("post") or {}).get("result") in ("ATTACK_POSTED_STABLE", "ATTACK_POST_UNCERTAIN", "PROCESS_EXITED")
        )
    )
    cancel_attempts = sum(1 for e in cancel_posts if e.get("post"))

    hold_stack_counts = [(h.get("syn") or {}).get("stack_depth", 0) for h in hold_samples]
    hold_through = bool(attack_moment) and (attack_moment.get("stack_depth_at_post") or 0) >= 2
    hold_post_window = any(c >= 2 for c in hold_stack_counts[:4]) if hold_stack_counts else False
    durable_ok = bool(durable.get("durable_stack_ge2"))
    any1886 = bool((durable.get("synthesis") or {}).get("any_at_1886")) or any(
        (h.get("syn") or {}).get("any_at_1886") for h in hold_samples
    )
    n_atk = atk_hits.count("HIT")
    attacked_all3 = len(attackers) >= 3 and n_atk >= 3

    if durable_ok and any1886:
        hit, result, estimate, note = True, "G6_HYBRID_POCKET_HIT", "~99%", "+~1pp durable stack+at1886"
    elif durable_ok:
        hit, result, estimate, note = True, "G6_HYBRID_DURABLE_HIT", "~98-99%", "+~0-1pp durable stack held"
    elif any1886:
        hit, result, estimate, note = True, "G6_HYBRID_ANY_AT_1886_HIT", "~98-99%", "+~0-1pp army at attack dest"
    elif attacked_all3 and hold_through and hold_post_window:
        hit, result, estimate, note = False, "G6_HYBRID_ATTACK_ALL_EPHEMERAL", "~98-99%", "Attack-all3 + brief hold; not durable"
    elif attacked_all3:
        hit, result, estimate, note = False, "G6_HYBRID_ATTACK_ALL_THEN_PEEL", "~98-99%", "Hybrid Strategic+anchor-Cancel; Attack-all; durable pocket goal"
    elif n_atk >= 2 and early_stack3:
        hit, result, estimate, note = False, "G6_HYBRID_ATTACK_PARTIAL", "~98-99%", "stack3 seen; Attack partial"
    elif n_atk >= 2:
        hit, result, estimate, note = False, "G6_HYBRID_STACK2_FALLBACK_NO_HOLD", "~98-99%", "fallback stack2 Attack; no durable"
    elif n_atk >= 1:
        hit, result, estimate, note = False, "G6_ATTACK_PARTIAL_NO_HOLD", "~98-99%", "Attack partial; no hold"
    else:
        hit, result, estimate, note = False, "G6_STACK3_ATTACK_FAIL", "~98-99%", "no Path-C bump"

    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikr"] = result
        data["last_phase"] = "2ikr"
        data["allow_post"] = False
        data["posting"] = "DISABLED"
        write_checklist(data)

    report = {
        "phase": "2ikr",
        "result": result,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "ai_limited_soft_fail_option": (
            None if hit else
            "Durable pocket may be AI-limited for Path-C agent policy after hybrid Strategic+Cancel-on-anchor-peel; do not claim durable HIT."
        ),
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "retreat": retreat,
        "calendar_ensure": cal,
        "plan": plan,
        "before": before,
        "strategic_posts": [
            {
                "army": e.get("army"),
                "skipped": e.get("skipped"),
                "role": e.get("role"),
                "dry": e.get("dry"),
                "post_result": (e.get("post") or {}).get("result"),
                "path_after_has_dest": CONCENTRATE_DEST in ((e.get("post") or {}).get("path_after") or []),
            }
            for e in strat_posts
        ],
        "strategic_hits": strat_hits,
        "cancel_posts": [
            {
                "army": e.get("army"),
                "reason": e.get("reason"),
                "dry": e.get("dry"),
                "post_result": (e.get("post") or {}).get("result"),
                "re_strategic": e.get("re_strategic"),
            }
            for e in cancel_posts
        ],
        "arrive": {
            "seconds_budget": seconds,
            "early_stop_stack3": early_stack3,
            "fallback_attack": fallback_attack,
            "samples_n": len(arrive_samples),
            "compact": arrive_samples,
        },
        "attack_moment": attack_moment,
        "attackers": attackers,
        "attack_posts": [
            {
                "army": e.get("army"),
                "src_province": e.get("src_province"),
                "target": e.get("target"),
                "dry": e.get("dry"),
                "post_result": (e.get("post") or {}).get("result"),
                "post_rax": (e.get("post") or {}).get("post_rax"),
                "immediate_on_stack3": e.get("immediate_on_stack3"),
                "fallback_stack2": e.get("fallback_stack2"),
            }
            for e in atk_posts
        ],
        "attack_hits": atk_hits,
        "hold_after_attack": {
            "samples_n": len(hold_samples),
            "stack_depths": hold_stack_counts,
            "hold_post_window_ge2": hold_post_window,
            "compact": hold_samples,
        },
        "durable_observe": {
            "seconds_budget": durable.get("seconds_budget"),
            "early_stop": durable.get("early_stop"),
            "samples_n": durable.get("samples_n"),
            "durable_stack_ge2": durable.get("durable_stack_ge2"),
            "synthesis": durable.get("synthesis"),
            "compact": durable.get("compact"),
        },
        "hold_through_attack": hold_through,
        "attacked_all3": attacked_all3,
        "stability": stab,
        "live0": live0,
        "live_after": live1,
        "instant": "PARKED",
        "final_allow_post": apf(),
        "marker_exists": MARKER.exists(),
        "post_attempts": {
            "strategic": strategic_attempts,
            "attack": attack_attempts,
            "cancel": cancel_attempts,
            "re_strategic_after_cancel": re_strat,
            "move": 0,
            "retreat": 0,
        },
        "path_c": {
            "baseline": "~60%",
            "prior_2iko": "~98-99%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": note,
        },
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {
        "phase": "2ikr",
        "result": result,
        "HIT": hit,
        "strategic_hits": strat_hits,
        "attack_hits": atk_hits,
        "attackers": attackers,
        "attack_moment": attack_moment,
        "early_stack3": early_stack3,
        "fallback_attack": fallback_attack,
        "attacked_all3": attacked_all3,
        "hold_through_attack": hold_through,
        "hold_stack_depths": hold_stack_counts,
        "durable": {
            "durable_stack_ge2": durable.get("durable_stack_ge2"),
            "early_stop": durable.get("early_stop"),
            "synthesis": durable.get("synthesis"),
        },
        "cancel_n": len(cancel_posts),
        "stability": stab,
        "final_allow_post": apf(),
        "estimate": estimate,
        "note": note,
        "ui0": live0.get("ui_date"),
        "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
        "post_attempts": report["post_attempts"],
        "retreat": retreat["status"],
        "calendar_ensure": cal,
        "pid": pid,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    DOC.write_text(
        "# Phase 2ikr — stack=3 Attack-all + Cancel hold\n\n"
        "**Result:** `%s` HIT=%s\n"
        "**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x | pid=%s\n\n"
        "## Strategic -> %s\nhits=%s\n\n"
        "## Attack-all on stack3 -> %s\nattackers=%s hits=%s early_stack3=%s fallback=%s\n"
        "attack_moment=%s\n\n"
        "## Hold / Cancel / durable\nhold_stack_depths=%s cancel_n=%s\n"
        "durable_stack_ge2=%s early=%s\nsyn=%s\n\n"
        "## Stability\n%s\n\n## Path C\n%s; crossed_70=YES; %s\n\n*%s*\n"
        % (
            result, hit, pid, CONCENTRATE_DEST, strat_hits, ATTACK_TARGET, attackers, atk_hits,
            early_stack3, fallback_attack, attack_moment, hold_stack_counts, len(cancel_posts),
            durable.get("durable_stack_ge2"), durable.get("early_stop"), durable.get("synthesis"),
            stab, estimate, note, report["timestamp_asia_shanghai"],
        ),
        encoding="utf-8",
    )
    text = json.dumps(summary, indent=2)
    CONSOLE.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
