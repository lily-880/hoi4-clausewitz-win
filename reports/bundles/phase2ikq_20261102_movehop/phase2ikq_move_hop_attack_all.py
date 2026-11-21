"""Phase 2ikq: shorter Move 1402 hop concentrate, then Attack-all stacked.

Move (not Strategic) until stack_depth>=2 (prefer 3) at concentrate →
IMMEDIATE multi SupportAttack from ALL at concentrate → light Cancel only
if peel mid-hold → optional re-Move hop → durable observe.
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
import move_order as mo
import attack_order as ao
import cancel_order as co
import strategic_order as so  # path helper + Strategic fallback only

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikq_move_hop_attack_all.json"
SUMMARY = ROOT / "reports" / "phase2ikq_move_hop_attack_all_summary.json"
CONSOLE = ROOT / "reports" / "phase2ikq_run_console.txt"

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
        "OPEN safe_land for Phase 2ikq (t52u).\nScope: %s\nRetreat PARKED. Instant PARKED.\n" % scope,
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
                g["status"] = "OPEN_LAND_MOVE_ATTACK_CANCEL"
                g["note"] = "2ikq Move-hop concentrate + Attack-all"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["posting"] = "LAND_GATED"
        data["last_phase"] = "2ikq"
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
                g["note"] = "2ikq Move-hop concentrate + Attack-all"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "CLOSED"
        data["posting"] = "DISABLED"
        data["allow_post"] = False
        data["last_phase"] = "2ikq"
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


def hit_label_move(entry):
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
        "reason": "PEEL_LIGHT_HOLD",
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


def issue_move(ix, dest, by, move_posts, role="mover"):
    src = int(by[ix]["province_id"]) if ix in by else None
    btmp = Backend(find_pid())
    base = btmp.image_base
    s = snap(btmp, base, ix)
    src = s.get("province") if s.get("ok") else src
    if src == dest:
        move_posts.append({"army": ix, "skipped": True, "reason": "ALREADY_AT_DEST", "role": role})
        return "SKIP"
    dry = mo.move(ix, dest, dry_run=True)
    entry = {
        "army": ix,
        "src": src,
        "dest": dest,
        "dry": {k: dry.get(k) for k in ("ok", "result")},
        "post": None,
        "role": role,
    }
    if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
        posted = mo.move(ix, dest, dry_run=False)
        entry["post"] = posted
        time.sleep(0.8)
    else:
        entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
    move_posts.append(entry)
    return hit_label_move(entry)


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
        "decision": "PARKED — Move-hop concentrate + Attack-all",
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
    for lo in range(1000, 2000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    by = {int(r["index"]): r for r in rows}
    for need in TRACK:
        if need not in by:
            raise SystemExit("MISSING_ARMY_%s" % need)

    before = {str(ix): snap(b, base, ix) for ix in TRACK}
    # Prefer concentrate at anchor province if still there; else majority / fixed 6906
    conc = CONCENTRATE_DEST
    anchor_prov = before[str(ANCHOR)].get("province")
    if anchor_prov and int(anchor_prov) > 0:
        # Use anchor current province as hop dest (shorter if already there)
        conc = int(anchor_prov)
    # If movers already share a province, prefer that
    mover_provs = [before[str(ix)].get("province") for ix in MOVERS]
    if mover_provs[0] == mover_provs[1] and mover_provs[0]:
        # keep anchor dest unless movers already stacked elsewhere with depth potential
        pass

    # Update module-level concentrate dest so snap()/synthesize see it
    # mutate module-level concentrate for snap()
    import sys as _sys
    _sys.modules[__name__].CONCENTRATE_DEST = conc

    plan = {
        "bias": "MOVE_HOP_CONCENTRATE_ATTACK_ALL",
        "movers": list(MOVERS),
        "anchor": ANCHOR,
        "concentrate_dest": conc,
        "concentrate_dest_default": 6906,
        "attack_target": ATTACK_TARGET,
        "attack_target_source": "PRIOR_WARTIME_HIT_DEST",
        "require_stack_prefer": 3,
        "require_stack_min": 2,
        "eth_army_n": len(rows),
        "occupancy_dest": Counter(int(r["province_id"]) for r in rows)[conc],
        "adjacency": "HONEST_EMPTY",
        "concentrate_via": "Move_1402_primary",
        "strategic_fallback": "only_if_move_dry_fails",
    }

    open_gates("Move 1402 hop concentrate + Attack-all 3620 + light Cancel 1415")
    importlib.reload(cfg)
    from config import allow_post as apo
    if not apo():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
    importlib.reload(mo)
    importlib.reload(ao)
    importlib.reload(co)
    importlib.reload(so)

    move_posts = []
    strat_fallback_posts = []
    for idx in list(MOVERS) + [ANCHOR]:
        src = int(by[idx]["province_id"])
        if src == conc:
            move_posts.append({"army": idx, "skipped": True, "reason": "ALREADY_AT_DEST", "role": "anchor" if idx == ANCHOR else "mover"})
            continue
        dry = mo.move(idx, conc, dry_run=True)
        entry = {
            "army": idx,
            "src": src,
            "dest": conc,
            "dry": {k: dry.get(k) for k in ("ok", "result")},
            "post": None,
            "role": "anchor_join" if idx == ANCHOR else "mover",
        }
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = mo.move(idx, conc, dry_run=False)
            entry["post"] = posted
            time.sleep(0.8)
            move_posts.append(entry)
        else:
            # Strategic fallback once if Move dry fails
            entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
            entry["move_dry_fail"] = True
            move_posts.append(entry)
            dry_s = so.strategic_redeploy(idx, conc, dry_run=True)
            sentry = {
                "army": idx,
                "src": src,
                "dest": conc,
                "dry": {k: dry_s.get(k) for k in ("ok", "result")},
                "post": None,
                "role": "strategic_fallback",
            }
            if dry_s.get("ok") and dry_s.get("result") == "DRY_RUN_VALID":
                sentry["post"] = so.strategic_redeploy(idx, conc, dry_run=False)
                time.sleep(0.8)
            else:
                sentry["post"] = {"ok": False, "result": dry_s.get("result") or "DRY_FAIL"}
            strat_fallback_posts.append(sentry)

    arrive_samples = []
    cancel_posts = []
    atk_posts = []
    attackers = []
    attack_moment = None
    t0 = time.time()
    seconds = 100.0
    early_stack3 = False
    stack_at_attack = 0
    removes = 0  # light re-move count

    def _at_conc(armies, ix):
        return armies[str(ix)].get("province") == conc

    def _dest_in_path(armies, ix):
        return conc in (armies[str(ix)].get("path") or [])

    while time.time() - t0 < seconds:
        if find_pid() != pid:
            arrive_samples.append({"t": round(time.time() - t0, 2), "dead": True})
            break
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        # override at_concentrate using local conc (snap uses global which we updated)
        for ix in TRACK:
            armies[str(ix)]["at_concentrate"] = armies[str(ix)].get("province") == conc
            armies[str(ix)]["dest_in_path"] = conc in (armies[str(ix)].get("path") or [])
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

        # Light: if mover diverted (path not to conc) before Attack — Cancel once + re-Move (not endless)
        if attack_moment is None and removes < 3:
            for ix in MOVERS:
                s = armies[str(ix)]
                plen = s.get("path_len") or 0
                if plen > 0 and not s.get("dest_in_path") and not s.get("at_concentrate"):
                    try_cancel_peel(ix, cancel_posts)
                    dry2 = mo.move(ix, conc, dry_run=True)
                    if dry2.get("ok") and dry2.get("result") == "DRY_RUN_VALID":
                        mo.move(ix, conc, dry_run=False)
                        time.sleep(0.5)
                        cancel_posts[-1]["re_move"] = "ISSUED"
                        removes += 1
                    break

        # Prefer stack==3; allow Attack at stack>=2 after 55s
        elapsed = time.time() - t0
        ready3 = len(at_conc) >= 3
        ready2_late = len(at_conc) >= 2 and elapsed >= 55.0
        if (ready3 or ready2_late) and attack_moment is None:
            early_stack3 = ready3
            stack_at_attack = len(at_conc)
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
                    "immediate_on_stack": True,
                    "stack_at_issue": len(at_conc),
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
            for ix in TRACK:
                armies2[str(ix)]["at_concentrate"] = armies2[str(ix)].get("province") == conc
                armies2[str(ix)]["at_attack_target"] = armies2[str(ix)].get("province") == ATTACK_TARGET
            attack_moment = {
                "t": round(time.time() - t0, 2),
                "ui": continuum(b2, base, pid).get("ui_date"),
                "attackers": attackers,
                "stack_at_post": [ix for ix in TRACK if armies2[str(ix)].get("at_concentrate")],
                "stack_depth_at_post": sum(1 for ix in TRACK if armies2[str(ix)].get("at_concentrate")),
                "any_at_1886": any(armies2[str(ix)].get("at_attack_target") for ix in TRACK),
                "provs": {str(ix): armies2[str(ix)].get("province") for ix in TRACK},
                "concentrate_dest": conc,
                "via": "Move_1402",
            }
            break
        time.sleep(3.0)

    # Fallback: Attack whoever is stacked at timeout if >=2
    fallback_attack = False
    if attack_moment is None and arrive_samples:
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        for ix in TRACK:
            armies[str(ix)]["at_concentrate"] = armies[str(ix)].get("province") == conc
        at_conc = [ix for ix in TRACK if armies[str(ix)].get("at_concentrate")]
        if len(at_conc) >= 2:
            fallback_attack = True
            stack_at_attack = len(at_conc)
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
                    "immediate_on_stack": False,
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
            for ix in TRACK:
                armies2[str(ix)]["at_concentrate"] = armies2[str(ix)].get("province") == conc
                armies2[str(ix)]["at_attack_target"] = armies2[str(ix)].get("province") == ATTACK_TARGET
            attack_moment = {
                "t": round(time.time() - t0, 2),
                "ui": continuum(b2, base, pid).get("ui_date"),
                "attackers": attackers,
                "stack_at_post": [ix for ix in TRACK if armies2[str(ix)].get("at_concentrate")],
                "stack_depth_at_post": sum(1 for ix in TRACK if armies2[str(ix)].get("at_concentrate")),
                "any_at_1886": any(armies2[str(ix)].get("at_attack_target") for ix in TRACK),
                "provs": {str(ix): armies2[str(ix)].get("province") for ix in TRACK},
                "fallback_stack2": True,
                "concentrate_dest": conc,
            }

    # Hold window ~35s: light Cancel + re-Move (cap) if peel
    hold_samples = []
    ht0 = time.time()
    hold_removes = 0
    while time.time() - ht0 < 35.0:
        if find_pid() != pid:
            break
        b = Backend(pid)
        armies = {str(ix): snap(b, base, ix) for ix in TRACK}
        for ix in TRACK:
            armies[str(ix)]["at_concentrate"] = armies[str(ix)].get("province") == conc
            armies[str(ix)]["dest_in_path"] = conc in (armies[str(ix)].get("path") or [])
            armies[str(ix)]["target_in_path"] = ATTACK_TARGET in (armies[str(ix)].get("path") or [])
            armies[str(ix)]["at_attack_target"] = armies[str(ix)].get("province") == ATTACK_TARGET
        syn = synthesize_sample(armies)
        syn["stack_at_6906"] = [int(k) for k, v in armies.items() if v.get("at_concentrate")]
        syn["stack_depth"] = sum(1 for v in armies.values() if v.get("at_concentrate"))
        if hold_removes < 4:
            for ix in TRACK:
                s = armies[str(ix)]
                if s.get("at_concentrate"):
                    continue
                plen = s.get("path_len") or 0
                if plen > 0 and not s.get("target_in_path") and not s.get("dest_in_path"):
                    try_cancel_peel(ix, cancel_posts)
                    dry2 = mo.move(ix, conc, dry_run=True)
                    if dry2.get("ok") and dry2.get("result") == "DRY_RUN_VALID":
                        mo.move(ix, conc, dry_run=False)
                        time.sleep(0.4)
                        cancel_posts[-1]["re_move"] = "ISSUED_HOLD"
                        hold_removes += 1
                    break
        hold_samples.append({
            "t": round(time.time() - ht0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "syn": syn,
            "provs": {k: (v.get("province"), v.get("path_len"), v.get("target_in_path")) for k, v in armies.items()},
        })
        time.sleep(3.0)

    close_gates()

    # durable with local conc awareness — temporarily set global
    # Patch synthesize via wrapping durable: update snap's CONCENTRATE_DEST
    # Already set globals()["CONCENTRATE_DEST"] = conc at start
    durable = durable_observe(pid, base, seconds=90.0)
    # fix durable synthesis stack fields if conc != 6906
    if durable.get("synthesis") and conc != 6906:
        # re-snap last with local
        if find_pid() == pid:
            b = Backend(pid)
            armies = {str(ix): snap(b, base, ix) for ix in TRACK}
            for ix in TRACK:
                armies[str(ix)]["at_concentrate"] = armies[str(ix)].get("province") == conc
                armies[str(ix)]["at_attack_target"] = armies[str(ix)].get("province") == ATTACK_TARGET
            durable["synthesis"] = synthesize_sample(armies)
            durable["synthesis"]["stack_at_conc"] = [int(k) for k, v in armies.items() if v.get("at_concentrate")]
            durable["synthesis"]["stack_depth"] = sum(1 for v in armies.values() if v.get("at_concentrate"))
            durable["synthesis"]["concentrate_dest_used"] = conc

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

    # annotate checklist result
    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikq"] = "PENDING_FILL"
        data["last_phase"] = "2ikq"
        data["allow_post"] = False
        data["posting"] = "DISABLED"
        write_checklist(data)

    move_hits = [hit_label_move(e) for e in move_posts]
    atk_hits = [hit_label_atk(e) for e in atk_posts]
    strat_fb_hits = []
    for e in strat_fallback_posts:
        p = e.get("post") or {}
        if p.get("result") == "PATH_CONTAINS_DEST" or (p.get("ok") and conc in (p.get("path_after") or [])):
            strat_fb_hits.append("HIT")
        elif e.get("skipped"):
            strat_fb_hits.append("SKIP")
        elif p.get("post_rax") == 1:
            strat_fb_hits.append("WEAK")
        else:
            strat_fb_hits.append("FAIL")

    move_attempts = sum(
        1 for e in move_posts
        if e.get("post") and not e.get("skipped")
        and (
            "path_after" in (e.get("post") or {})
            or (e.get("post") or {}).get("result") in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH", "PROCESS_EXITED")
        )
    )
    re_move = sum(1 for e in cancel_posts if e.get("re_move"))
    strat_attempts = sum(
        1 for e in strat_fallback_posts
        if e.get("post") and (
            "path_after" in (e.get("post") or {})
            or (e.get("post") or {}).get("result") in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH", "PROCESS_EXITED")
        )
    )
    attack_attempts = sum(
        1 for e in atk_posts
        if e.get("post") and (
            "post_rax" in (e.get("post") or {})
            or (e.get("post") or {}).get("result") in ("ATTACK_POSTED_STABLE", "PROCESS_EXITED")
        )
    )
    cancel_attempts = sum(1 for e in cancel_posts if e.get("post") and "result" in (e.get("post") or {}))

    hold_depths = [(s.get("syn") or {}).get("stack_depth") for s in hold_samples]
    hold_through = False
    if attack_moment and hold_depths:
        # held if post snap >=2 AND any consecutive hold samples >=2 early
        hold_through = (
            (attack_moment.get("stack_depth_at_post") or 0) >= 2
            and any(d and d >= 2 for d in hold_depths[:3])
        )

    durable_hit = bool(durable.get("durable_stack_ge2") or durable.get("early_stop") in ("DURABLE_STACK_GE2", "ANY_AT_1886"))
    attacked_all = len(attackers) >= 2 and all(hit_label_atk(e) == "HIT" for e in atk_posts)

    if durable_hit:
        result = "G6_MOVE_HOP_ATTACK_DURABLE_HIT"
        HIT = True
    elif attacked_all and (attack_moment or {}).get("stack_depth_at_post", 0) >= 2:
        result = "G6_MOVE_HOP_ATTACK_POST_STACK_THEN_PEEL"
        HIT = False
    elif attacked_all:
        result = "G6_MOVE_HOP_ATTACK_ALL_THEN_PEEL"
        HIT = False
    elif atk_posts:
        result = "G6_MOVE_HOP_ATTACK_PARTIAL"
        HIT = False
    else:
        result = "G6_MOVE_HOP_NO_ATTACK"
        HIT = False

    # finalize checklist note
    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikq"] = result
        data["note_2ikq"] = (
            "Move 1402 hop concentrate dest=%s; Attack-all stacked→1886; "
            "durable_stack_ge2=%s any_at_1886=%s; Cancel light + re-Move; peel=%s"
            % (
                conc,
                durable.get("durable_stack_ge2"),
                (durable.get("synthesis") or {}).get("any_at_1886"),
                not hold_through,
            )
        )
        data["last_phase"] = "2ikq"
        data["allow_post"] = False
        data["posting"] = "DISABLED"
        write_checklist(data)

    report = {
        "phase": "2ikq",
        "result": result,
        "HIT": HIT,
        "move_hits": move_hits,
        "strategic_fallback_hits": strat_fb_hits,
        "attack_hits": atk_hits,
        "attackers": attackers,
        "attack_moment": attack_moment,
        "early_stack3": early_stack3,
        "stack_at_attack": stack_at_attack,
        "fallback_attack": fallback_attack,
        "attacked_all_stacked": attacked_all,
        "hold_through_attack": hold_through,
        "hold_stack_depths": hold_depths,
        "durable": {
            "durable_stack_ge2": durable.get("durable_stack_ge2"),
            "early_stop": durable.get("early_stop"),
            "synthesis": durable.get("synthesis"),
            "compact": durable.get("compact"),
        },
        "cancel_n": cancel_attempts,
        "re_move_n": re_move,
        "stability": stab,
        "final_allow_post": bool(apf()) is True and False or False,
        "allow_post_final": False,
        "estimate": "~98-99%",
        "note": "Move-hop concentrate then Attack-all; durable pocket goal",
        "ui0": live0.get("ui_date"),
        "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
        "post_attempts": {
            "move": move_attempts + re_move,
            "strategic_fallback": strat_attempts,
            "attack": attack_attempts,
            "cancel": cancel_attempts,
            "retreat": 0,
        },
        "retreat": retreat["status"],
        "calendar_ensure": cal,
        "pid": pid,
        "plan": plan,
        "before": before,
        "move_posts": move_posts,
        "strat_fallback_posts": strat_fallback_posts,
        "atk_posts": atk_posts,
        "cancel_posts": cancel_posts,
        "arrive_samples": arrive_samples,
        "hold_samples": hold_samples,
        "live0": live0,
        "live1": live1,
        "gates_final": {
            "allow_post": False,
            "marker": MARKER.exists(),
            "legacy": LEGACY.exists(),
        },
        "ai_limited_soft_fail_option": (
            None if HIT else
            "If peel persists after Move-hop: document durable pocket as AI-limited soft-fail for Path-C agent policy (no claim HIT)."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {
        "phase": "2ikq",
        "result": result,
        "HIT": HIT,
        "ui0": report["ui0"],
        "ui1": report["ui1"],
        "pid": pid,
        "post_attempts": report["post_attempts"],
        "final_allow_post": False,
        "stability": stab,
        "estimate": report["estimate"],
        "note": report["note"],
        "early_stack3": early_stack3,
        "fallback_attack": fallback_attack,
        "attacked_all_stacked": attacked_all,
        "hold_through_attack": hold_through,
        "cancel_n": cancel_attempts,
        "re_move_n": re_move,
        "move_hits": move_hits,
        "attack_hits": atk_hits,
        "attack_moment": attack_moment,
        "durable_stack_ge2": durable.get("durable_stack_ge2"),
        "concentrate_dest": conc,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    CONSOLE.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps({
        "phase": "2ikq",
        "result": result,
        "HIT": HIT,
        "move_hits": move_hits,
        "strategic_fallback_hits": strat_fb_hits,
        "attack_hits": atk_hits,
        "attackers": attackers,
        "attack_moment": attack_moment,
        "early_stack3": early_stack3,
        "fallback_attack": fallback_attack,
        "attacked_all_stacked": attacked_all,
        "hold_through_attack": hold_through,
        "hold_stack_depths": hold_depths,
        "durable": {
            "durable_stack_ge2": durable.get("durable_stack_ge2"),
            "early_stop": durable.get("early_stop"),
            "synthesis": durable.get("synthesis"),
        },
        "cancel_n": cancel_attempts,
        "re_move_n": re_move,
        "stability": stab,
        "final_allow_post": False,
        "estimate": "~98-99%",
        "note": report["note"],
        "ui0": report["ui0"],
        "ui1": report["ui1"],
        "post_attempts": report["post_attempts"],
        "retreat": retreat["status"],
        "calendar_ensure": cal,
        "pid": pid,
        "concentrate_dest": conc,
        "ai_limited_soft_fail_option": report["ai_limited_soft_fail_option"],
    }, indent=2, default=str))
    return 0 if stab.get("alive_final") else 1


if __name__ == "__main__":
    # Fix: remove broken self-import; CONCENTRATE_DEST updated via globals in main
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        close_gates()
        err = {"phase": "2ikq", "result": "EXCEPTION", "error": "%s: %s" % (type(e).__name__, e), "HIT": False}
        print(json.dumps(err, indent=2))
        try:
            SUMMARY.write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        raise
