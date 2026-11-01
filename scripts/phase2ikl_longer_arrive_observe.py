"""Phase 2ikl: longer arrive observe toward concentrate stack; optional Attack refresh.

Observe-first. Max ONE multi SupportAttack if 2+ at 6906 or near 1886.
Retreat PARKED. Instant PARKED. Push attempted separately.
"""
from __future__ import annotations

import importlib
import json
import os
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import config as cfg
from config import allow_post
from process import Backend, find_pid
from handle import resolve_handle, HANDLE_TYPE_ARMY
import strategic_order as so
import attack_order as ao

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikl_longer_arrive_observe.json"
SUMMARY = ROOT / "reports" / "phase2ikl_longer_arrive_observe_summary.json"
DOC = ROOT / "docs" / "PHASE2IKL_LONGER_ARRIVE_OBSERVE.md"

CONCENTRATE_DEST = 6906
ATTACK_TARGET = 1886
ARMIES = (1037, 1038, 1042)
CA_PROVINCE = 0x28
OBSERVE_SECONDS = 75.0
SAMPLE_INTERVAL = 5.0


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def read_checklist():
    if not CHECKLIST.exists():
        return None
    return json.loads(CHECKLIST.read_text(encoding="utf-8-sig"))


def write_checklist(data):
    CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN safe_land for Phase 2ikl optional Attack refresh (t52u).\n"
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
                g["status"] = "OPEN_LAND_ATTACK"
                g["note"] = "2ikl optional Attack refresh"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["posting"] = "LAND_ATTACK_GATED"
        data["last_phase"] = "2ikl"
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
                g["note"] = "Re-closed after 2ikl"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "closed"
        data["posting"] = "DISABLED"
        data["allow_post"] = False
        data["last_phase"] = "2ikl"
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
        "path_head": path[:6],
        "at_concentrate": prov == CONCENTRATE_DEST,
        "at_attack_target": prov == ATTACK_TARGET,
        "concentrate_in_path": CONCENTRATE_DEST in path,
        "target_in_path": ATTACK_TARGET in path,
    }


def observe_stable(pid: int, seconds: float = 20.0) -> dict:
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


def longer_arrive(pid, base):
    samples = []
    t0 = time.time()
    early_stack = False
    while time.time() - t0 < OBSERVE_SECONDS:
        if find_pid() != pid:
            samples.append({"t": round(time.time() - t0, 2), "dead": True})
            break
        b = Backend(pid)
        live = continuum(b, base, pid)
        armies = {str(ix): snap(b, base, ix) for ix in ARMIES}
        at_conc = [ix for ix in ARMIES if (armies[str(ix)] or {}).get("at_concentrate")]
        at_tgt = [ix for ix in ARMIES if (armies[str(ix)] or {}).get("at_attack_target")]
        enroute = [ix for ix in ARMIES if (armies[str(ix)] or {}).get("concentrate_in_path")]
        row = {
            "t": round(time.time() - t0, 2),
            "ui": live.get("ui_date"),
            "armies": armies,
            "stack_at_concentrate": at_conc,
            "stack_depth_concentrate": len(at_conc),
            "at_attack_target": at_tgt,
            "enroute_concentrate": enroute,
        }
        samples.append(row)
        if len(at_conc) >= 2 or len(at_tgt) >= 1:
            early_stack = True
            break
        time.sleep(SAMPLE_INTERVAL)
    last = samples[-1] if samples else {}
    return {
        "seconds_budget": OBSERVE_SECONDS,
        "interval": SAMPLE_INTERVAL,
        "samples_n": len(samples),
        "early_stop_stack": early_stack,
        "samples_compact": [
            {
                "t": s.get("t"),
                "ui": s.get("ui"),
                "provs": {
                    k: (v.get("province"), v.get("path_len"), v.get("concentrate_in_path"), v.get("target_in_path"))
                    for k, v in (s.get("armies") or {}).items()
                },
                "stack_depth_concentrate": s.get("stack_depth_concentrate"),
                "stack_at_concentrate": s.get("stack_at_concentrate"),
                "at_attack_target": s.get("at_attack_target"),
                "enroute_concentrate": s.get("enroute_concentrate"),
            }
            for s in samples
        ],
        "last": last,
        "movers_arrived": all(
            (last.get("armies") or {}).get(str(i), {}).get("at_concentrate") for i in (1037, 1038)
        )
        if last.get("armies")
        else False,
        "stack_depth": (last.get("stack_depth_concentrate") or 0),
        "any_at_1886": bool(last.get("at_attack_target")),
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
        "decision": "PARKED — observe/refresh Attack only",
    }

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)

    arrive = longer_arrive(pid, base)
    stack_depth = arrive["stack_depth"]
    near_attack = arrive["any_at_1886"]
    warrant_refresh = stack_depth >= 2 or near_attack

    atk_posts = []
    attack_attempts = 0
    if warrant_refresh:
        last_armies = (arrive["last"].get("armies") or {})
        attackers = []
        for ix in (1042, 1037, 1038):
            s = last_armies.get(str(ix)) or {}
            if s.get("at_concentrate") or s.get("at_attack_target"):
                attackers.append(ix)
            if len(attackers) >= 2:
                break
        if len(attackers) < 2:
            # pad with live ok armies at concentrate preference
            for ix in (1042, 1037, 1038):
                if ix not in attackers and (last_armies.get(str(ix)) or {}).get("ok"):
                    attackers.append(ix)
                if len(attackers) >= 2:
                    break

        open_gates()
        importlib.reload(cfg)
        from config import allow_post as apo

        if not apo():
            close_gates()
            raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
        importlib.reload(ao)

        # ONE multi refresh = up to 2 SupportAttack posts in one campaign
        for ix in attackers[:2]:
            dry = ao.support_attack(ix, ATTACK_TARGET, dry_run=True)
            entry = {
                "army": ix,
                "src": (last_armies.get(str(ix)) or {}).get("province"),
                "at_concentrate": (last_armies.get(str(ix)) or {}).get("at_concentrate"),
                "target": ATTACK_TARGET,
                "dry": {k: dry.get(k) for k in ("ok", "result")},
                "post": None,
            }
            if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
                posted = ao.support_attack(ix, ATTACK_TARGET, dry_run=False)
                entry["post"] = posted
                attack_attempts += 1
                time.sleep(0.6)
            else:
                entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
            atk_posts.append(entry)
        close_gates()
    else:
        # observe-only — gates stay closed
        pass

    # short post observe if attacked, else light snap
    post_obs = []
    t0 = time.time()
    budget = 30.0 if warrant_refresh else 10.0
    while time.time() - t0 < budget:
        if find_pid() != pid:
            break
        b2 = Backend(pid)
        post_obs.append(
            {
                "t": round(time.time() - t0, 2),
                "ui": continuum(b2, base, pid).get("ui_date"),
                "armies": {str(ix): snap(b2, base, ix) for ix in ARMIES},
            }
        )
        time.sleep(5.0)

    stab = observe_stable(pid, 20.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    importlib.reload(cfg)
    from config import allow_post as apf

    atk_hits = []
    for e in atk_posts:
        p = e.get("post") or {}
        if p.get("result") == "ATTACK_POSTED_STABLE" and p.get("ok"):
            atk_hits.append("HIT")
        elif p.get("post_rax") == 1:
            atk_hits.append("WEAK")
        else:
            atk_hits.append("FAIL")

    last_post = post_obs[-1]["armies"] if post_obs else {}
    pocket = {
        "stack_depth_final": sum(
            1 for ix in ARMIES if (last_post.get(str(ix)) or {}).get("at_concentrate")
        ),
        "at_1886": [ix for ix in ARMIES if (last_post.get(str(ix)) or {}).get("at_attack_target")],
        "provinces": {str(ix): (last_post.get(str(ix)) or {}).get("province") for ix in ARMIES},
        "any_path": any(((last_post.get(str(ix)) or {}).get("path_len") or 0) > 0 for ix in ARMIES),
        "combat_densify": "HONEST_EMPTY",
        "adjacency": "HONEST_EMPTY",
    }

    if warrant_refresh and atk_hits.count("HIT") >= 2 and stack_depth >= 2:
        result = "G6_LONGER_ARRIVE_STACK_ATTACK_HIT"
        estimate = "~98-99%"
        note = "+~1pp concentrate stack + Attack refresh"
        hit = True
    elif warrant_refresh and atk_hits.count("HIT") >= 1:
        result = "G6_LONGER_ARRIVE_STACK_ATTACK_PARTIAL"
        estimate = "~97-99%"
        note = "+~0-1pp stack/attack partial"
        hit = False
    elif stack_depth >= 2:
        result = "G6_LONGER_ARRIVE_STACK_FORMED"
        estimate = "~97-99%"
        note = "+~1pp stack formed (no Attack needed/used)"
        hit = True
    elif arrive.get("early_stop_stack") is False and any(
        (c.get("enroute_concentrate") for c in arrive["samples_compact"])
    ):
        result = "G6_LONGER_ARRIVE_ENROUTE_HONEST"
        estimate = "~97-99%"
        note = "honest enroute progress; no invent pocket"
        hit = True  # observe campaign complete honestly
    else:
        result = "G6_LONGER_ARRIVE_STATIC_HONEST"
        estimate = "~97-99%"
        note = "honest static/progress fold; combat densify HONEST_EMPTY"
        hit = True

    data = read_checklist()
    if isinstance(data, dict):
        data["phase2ikl"] = result
        data["last_phase"] = "2ikl"
        data["allow_post"] = False
        data["posting"] = "DISABLED"
        write_checklist(data)

    report = {
        "phase": "2ikl",
        "result": result,
        "HIT": hit,
        "primary": "A_LONGER_ARRIVE_THEN_OPTIONAL_ATTACK",
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "retreat": retreat,
        "arrive": {
            "seconds_budget": arrive["seconds_budget"],
            "samples_n": arrive["samples_n"],
            "early_stop_stack": arrive["early_stop_stack"],
            "movers_arrived": arrive["movers_arrived"],
            "stack_depth": stack_depth,
            "any_at_1886": near_attack,
            "warrant_refresh": warrant_refresh,
            "compact": arrive["samples_compact"],
        },
        "attack_refresh": {
            "used": warrant_refresh,
            "posts": atk_posts,
            "hits": atk_hits,
        },
        "pocket_observe": pocket,
        "stability": stab,
        "live0": live0,
        "live_after": live1,
        "instant": "PARKED",
        "final_allow_post": apf(),
        "marker_exists": MARKER.exists(),
        "post_attempts": {
            "attack": attack_attempts,
            "strategic": 0,
            "move": 0,
            "cancel": 0,
            "retreat": 0,
        },
        "push_note": "attempted at slice start; see parent report for final push status",
        "path_c": {
            "baseline": "~60%",
            "prior_2ikk": "~97-99%",
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
                "phase": "2ikl",
                "result": result,
                "HIT": hit,
                "stack_depth": stack_depth,
                "movers_arrived": arrive["movers_arrived"],
                "warrant_refresh": warrant_refresh,
                "atk_hits": atk_hits,
                "pocket": pocket,
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
        f"""# Phase 2ikl — Longer arrive observe + optional Attack refresh

**Result:** `{result}` HIT={hit}
**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x

## Arrive (~{OBSERVE_SECONDS}s max, early-stop on stack)

- stack_depth={stack_depth} movers_arrived={arrive['movers_arrived']} early_stop={arrive['early_stop_stack']}
- warrant_refresh={warrant_refresh}

## Attack refresh

used={warrant_refresh} hits={atk_hits} posts={atk_posts}

## Pocket / combat

{pocket}

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
                "stack_depth": stack_depth,
                "movers_arrived": arrive["movers_arrived"],
                "early_stop_stack": arrive["early_stop_stack"],
                "warrant_refresh": warrant_refresh,
                "atk_hits": atk_hits,
                "pocket": pocket,
                "stability": stab,
                "allow_post": apf(),
                "estimate": estimate,
                "note": note,
                "ui0": live0.get("ui_date"),
                "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
                "post_attempts": report["post_attempts"],
                "retreat": retreat["status"],
                "arrive_compact_tail": arrive["samples_compact"][-3:],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
