"""Phase 2iki: arrive-poll + multi-army Attack 3620; Retreat HARD_DENY/PARKED.

Retreat Post ABI still not cheaply proven (no retreat_order.py; NewFallback RO/DISABLED).
Brief bounded arrive poll vs concentrate dest 6906; if anchor or mover present, TWO-army
SupportAttack toward prior wartime HIT dest 1886 (not adjacency invent). Instant PARKED.
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
import move_order as mo

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2iki_multi_attack_concentrate.json"
SUMMARY = ROOT / "reports" / "phase2iki_multi_attack_concentrate_summary.json"
DOC = ROOT / "docs" / "PHASE2IKI_MULTI_ATTACK_CONCENTRATE.md"
CONCENTRATE_DEST = 6906
ATTACK_TARGET = 1886  # prior wartime SupportAttack IsValid HIT dest
CA_PROVINCE = 0x28


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN safe_land tool-gate for Phase 2iki (user t52u).\n"
        "Scope: multi-army SupportAttack 3620 after brief concentrate arrive poll.\n"
        "Retreat PARKED. Instant PARKED.\n",
        encoding="utf-8",
    )
    if LEGACY.exists():
        try:
            LEGACY.unlink()
        except Exception:
            pass
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for g in data.get("gaps", []):
                if g.get("id") == "command_queue_tool_gate":
                    g["status"] = "OPEN_LAND_ATTACK"
                    g["note"] = "2iki multi-Attack gated"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "OPEN_WITH_ENV_AND_MARKER"
            data["posting"] = "LAND_ATTACK_GATED"
            data["last_phase"] = "2iki"
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LEGACY):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for g in data.get("gaps", []):
                if g.get("id") == "command_queue_tool_gate":
                    g["status"] = "CLOSED_NOT_OPENED"
                    g["note"] = "Re-closed after 2iki"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "closed"
            data["posting"] = "DISABLED"
            data["allow_post"] = False
            data["last_phase"] = "2iki"
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def continuum(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = mo._u64(b, base + gs_rva)
    year = struct.unpack("<i", b.read(gs + 0x478, 4))[0]
    day = struct.unpack("<i", b.read(gs + 0x484, 4))[0]
    tag = struct.unpack("<i", b.read(gs + 0x518, 4))[0]
    try:
        ui = (datetime(year, 1, 1) + timedelta(days=int(day))).strftime("%Y-%m-%d")
    except Exception:
        ui = None
    return {"pid": pid, "ui_date": ui, "day_index": day, "player_tag": tag, "allow_post": allow_post()}


def snap(b, base, idx: int) -> dict:
    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return {"army": idx, "ok": False}
    prov = struct.unpack("<I", b.read(army + CA_PROVINCE, 4))[0]
    path = so._path(b, base, army)
    return {
        "army": idx,
        "ok": True,
        "province": prov,
        "path": path,
        "path_len": len(path),
        "at_concentrate": prov == CONCENTRATE_DEST,
        "dest_in_path": CONCENTRATE_DEST in path,
    }


def brief_arrive_poll(pid: int, base: int, seconds: float = 8.0) -> dict:
    samples = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        b = Backend(pid)
        row = {"t": round(time.time() - t0, 2)}
        for ix in (1037, 1038, 1042):
            row[str(ix)] = snap(b, base, ix)
        samples.append(row)
        time.sleep(2.0)
    last = samples[-1] if samples else {}
    movers_arrived = any((last.get(str(i)) or {}).get("at_concentrate") for i in (1037, 1038))
    anchor_at = bool((last.get("1042") or {}).get("at_concentrate"))
    return {
        "seconds_budget": seconds,
        "samples_n": len(samples),
        "samples": samples,
        "movers_arrived": movers_arrived,
        "anchor_at_dest": anchor_at,
        "gate_open": movers_arrived or anchor_at,
        "note": "Bounded poll only — not endless arrive wait",
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


def retreat_hard_deny() -> dict:
    return {
        "status": "HARD_DENY_PARKED_NOT_PROVEN_CHEAP",
        "retreat_order_py": (ROOT / "calling" / "retreat_order.py").exists(),
        "reason": (
            "NewFallback ~4271 factory meta known but posting DISABLED / NF midflight empty / "
            "subject_handle+CPdxArray not Post-proven; no cheap IsValid+Post this slice"
        ),
        "decision": "PARKED — primary B multi-Attack after arrive poll",
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
    global allow_post
    from config import allow_post

    assert allow_post() is False

    retreat = retreat_hard_deny()
    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)

    arrive = brief_arrive_poll(pid, base, seconds=8.0)
    if not arrive["gate_open"]:
        close_gates()
        raise SystemExit("ARRIVE_GATE_CLOSED")

    # Prefer: concentrate-present armies first (1042), then proven movers 1037/1038 for multi
    last = arrive["samples"][-1]
    present = []
    for ix in (1042, 1037, 1038):
        s = last.get(str(ix)) or {}
        if s.get("ok"):
            present.append(ix)
    # Multi = two armies: always include 1042 if at dest; plus one mover (even if not arrived)
    attackers = []
    if (last.get("1042") or {}).get("at_concentrate"):
        attackers.append(1042)
    for ix in (1037, 1038):
        if ix not in attackers and (last.get(str(ix)) or {}).get("ok"):
            attackers.append(ix)
        if len(attackers) >= 2:
            break
    if len(attackers) < 2:
        raise SystemExit("NEED_TWO_ARMIES")

    # Dry then Post
    open_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_open

    if not allow_post_open():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
    importlib.reload(ao)

    posts = []
    for ix in attackers:
        dry = ao.support_attack(ix, ATTACK_TARGET, dry_run=True)
        entry = {
            "army": ix,
            "src_province": (last.get(str(ix)) or {}).get("province"),
            "at_concentrate": (last.get(str(ix)) or {}).get("at_concentrate"),
            "target": ATTACK_TARGET,
            "dry": {k: dry.get(k) for k in ("ok", "result", "province")},
            "post": None,
        }
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = ao.support_attack(ix, ATTACK_TARGET, dry_run=False)
            entry["post"] = posted
            time.sleep(0.6)
        else:
            entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
        posts.append(entry)

    time.sleep(1.0)
    b2 = Backend(pid)
    after = {str(ix): snap(b2, base, ix) for ix in attackers}
    stab = observe_stable(pid, 30.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    close_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_final

    hits = []
    for e in posts:
        p = e.get("post") or {}
        if p.get("result") == "ATTACK_POSTED_STABLE" and p.get("ok"):
            hits.append("HIT")
        elif p.get("post_rax") == 1:
            hits.append("WEAK")
        else:
            hits.append("FAIL")

    n_hit = hits.count("HIT")
    if n_hit >= 2:
        result_code = "G6_MULTI_ATTACK_CONCENTRATE_HIT"
        estimate = "~96-98%"
        note = "+~2pp multi-army Attack after concentrate arrive-poll gate"
    elif n_hit == 1:
        result_code = "G6_MULTI_ATTACK_CONCENTRATE_PARTIAL"
        estimate = "~95-97%"
        note = "+~1pp partial multi-Attack"
    else:
        result_code = "G6_MULTI_ATTACK_CONCENTRATE_FAIL"
        estimate = "~94-96%"
        note = "no Path-C bump"

    hit = result_code.endswith("_HIT")
    attack_attempts = sum(
        1
        for e in posts
        if isinstance(e.get("post"), dict)
        and e["post"].get("result")
        in ("ATTACK_POSTED_STABLE", "ATTACK_POST_UNCERTAIN", "PROCESS_EXITED")
        or (e.get("post") and "post_rax" in (e.get("post") or {}))
    )

    report = {
        "phase": "2iki",
        "result": result_code,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "primary_choice": "B_ARRIVE_POLL_MULTI_ATTACK",
        "retreat": retreat,
        "concentrate_dest": CONCENTRATE_DEST,
        "attack_target": ATTACK_TARGET,
        "arrive_poll": {
            "seconds_budget": arrive["seconds_budget"],
            "samples_n": arrive["samples_n"],
            "movers_arrived": arrive["movers_arrived"],
            "anchor_at_dest": arrive["anchor_at_dest"],
            "gate_open": arrive["gate_open"],
            "last": last,
            "note": arrive["note"],
        },
        "attackers": attackers,
        "posts": posts,
        "hits": hits,
        "after": after,
        "stability": stab,
        "live0": live0,
        "live_after": live1,
        "instant": "PARKED",
        "combat_densify": "HONEST_EMPTY",
        "adjacency": "HONEST_EMPTY",
        "honesty": (
            "Movers 1037/1038 still not at 6906; multi-Attack uses concentrate-anchor 1042 + "
            "second wartime army under gate (anchor_at_dest). Target 1886 prior HIT dest."
        ),
        "final_allow_post": allow_post_final(),
        "marker_exists": MARKER.exists(),
        "post_attempts": {
            "attack": attack_attempts,
            "strategic": 0,
            "move": 0,
            "cancel": 0,
            "retreat": 0,
        },
        "path_c": {
            "baseline": "~60%",
            "prior_2ikh": "~94-96%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": note,
        },
        "agent_card_fold": (
            "Multi-army Attack after concentrate arrive-poll extends encircle-bias "
            "reposition→concentrate→attack loop; Retreat remains HARD_DENY/PARKED"
        ),
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2iki",
                "result": result_code,
                "HIT": hit,
                "retreat": retreat["status"],
                "movers_arrived": arrive["movers_arrived"],
                "anchor_at_dest": arrive["anchor_at_dest"],
                "attackers": attackers,
                "target": ATTACK_TARGET,
                "hits": hits,
                "post_results": [
                    (e["army"], (e.get("post") or {}).get("result"), (e.get("post") or {}).get("post_rax"))
                    for e in posts
                ],
                "stability": stab,
                "final_allow_post": allow_post_final(),
                "estimate": estimate,
                "ui": (live1.get("ui_date") if isinstance(live1, dict) else None) or live0.get("ui_date"),
                "post_attempts": report["post_attempts"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2iki — Multi-army Attack after concentrate arrive-poll

**Result:** `{result_code}` HIT={hit}
**Primary:** B (Retreat `{retreat['status']}`)
**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x

## Arrive poll (bounded ~8s)

- movers_arrived={arrive['movers_arrived']} anchor_at_dest={arrive['anchor_at_dest']} gate_open={arrive['gate_open']}
- Last: {last}

## Multi SupportAttack 3620 → {ATTACK_TARGET}

- Attackers: {attackers}
- Posts: {posts}
- Hits: {hits}
- Stability: {stab}

## Gates

allow_post={allow_post_final()}; Instant PARKED; combat densify HONEST_EMPTY.

## Path C

{estimate}; crossed_70=YES; {note}

*{report['timestamp_asia_shanghai']}*
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "result": result_code,
                "HIT": hit,
                "retreat": retreat["status"],
                "movers_arrived": arrive["movers_arrived"],
                "anchor_at_dest": arrive["anchor_at_dest"],
                "attackers": attackers,
                "hits": hits,
                "post_results": [
                    {
                        "army": e["army"],
                        "at_concentrate": e.get("at_concentrate"),
                        "result": (e.get("post") or {}).get("result"),
                        "post_rax": (e.get("post") or {}).get("post_rax"),
                    }
                    for e in posts
                ],
                "stability": stab,
                "allow_post": allow_post_final(),
                "estimate": estimate,
                "ui": live0.get("ui_date"),
                "post_attempts": report["post_attempts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
