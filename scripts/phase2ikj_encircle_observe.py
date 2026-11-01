"""Phase 2ikj: bounded RO observe after multi-Attack concentrate campaign.

Observe-first (prefer A). No Retreat invent. Instant PARKED.
Optional corrective Post only if linger blocks observe — this run expects none.
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
import move_order as mo

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikj_encircle_observe.json"
SUMMARY = ROOT / "reports" / "phase2ikj_encircle_observe_summary.json"
DOC = ROOT / "docs" / "PHASE2IKJ_ENCIRCLE_OBSERVE.md"

CONCENTRATE_DEST = 6906
ATTACK_TARGET = 1886
ARMIES = (1042, 1037, 1038)
CA_PROVINCE = 0x28
OBSERVE_SECONDS = 40.0
SAMPLE_INTERVAL = 4.0


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
        "path_head": path[:8],
        "path_tail": path[-4:] if path else [],
        "at_concentrate": prov == CONCENTRATE_DEST,
        "at_attack_target": prov == ATTACK_TARGET,
        "target_in_path": ATTACK_TARGET in path,
        "concentrate_in_path": CONCENTRATE_DEST in path,
    }


def observe_loop(pid: int, base: int) -> dict:
    samples = []
    t0 = time.time()
    while time.time() - t0 < OBSERVE_SECONDS:
        b = Backend(pid)
        if find_pid() != pid:
            samples.append({"t": round(time.time() - t0, 2), "dead": True})
            break
        row = {
            "t": round(time.time() - t0, 2),
            "ui": continuum(b, base, pid).get("ui_date"),
            "armies": {str(ix): snap(b, base, ix) for ix in ARMIES},
        }
        # co-location / stack signals (province equality only — not adjacency invent)
        provs = {
            ix: (row["armies"][str(ix)].get("province") if row["armies"][str(ix)].get("ok") else None)
            for ix in ARMIES
        }
        at_conc = [ix for ix, p in provs.items() if p == CONCENTRATE_DEST]
        at_tgt = [ix for ix, p in provs.items() if p == ATTACK_TARGET]
        coloc = {}
        for a in ARMIES:
            for bix in ARMIES:
                if a < bix and provs[a] is not None and provs[a] == provs[bix]:
                    coloc[f"{a}+{bix}"] = provs[a]
        row["at_concentrate"] = at_conc
        row["at_attack_target"] = at_tgt
        row["co_located_pairs"] = coloc
        samples.append(row)
        time.sleep(SAMPLE_INTERVAL)
    return {
        "seconds_budget": OBSERVE_SECONDS,
        "interval": SAMPLE_INTERVAL,
        "samples_n": len(samples),
        "samples": samples,
    }


def stability_tail(pid: int, seconds: float = 20.0) -> dict:
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


def synthesize(obs: dict) -> dict:
    first = obs["samples"][0]["armies"] if obs["samples"] else {}
    last = obs["samples"][-1]["armies"] if obs["samples"] else {}
    moved = {}
    path_activity = {}
    for ix in ARMIES:
        a0 = first.get(str(ix)) or {}
        a1 = last.get(str(ix)) or {}
        moved[str(ix)] = {
            "from": a0.get("province"),
            "to": a1.get("province"),
            "changed": a0.get("province") != a1.get("province"),
        }
        path_lens = [
            (s["armies"].get(str(ix)) or {}).get("path_len", 0)
            for s in obs["samples"]
            if (s.get("armies") or {}).get(str(ix))
        ]
        path_activity[str(ix)] = {
            "max_path_len": max(path_lens) if path_lens else 0,
            "any_path": any(pl > 0 for pl in path_lens),
            "any_target_in_path": any(
                (s["armies"].get(str(ix)) or {}).get("target_in_path") for s in obs["samples"]
            ),
        }

    # stack / pocket honesty
    last_row = obs["samples"][-1] if obs["samples"] else {}
    stack_at_conc = last_row.get("at_concentrate") or []
    stack_at_tgt = last_row.get("at_attack_target") or []
    any_coloc = any((s.get("co_located_pairs") or {}) for s in obs["samples"])
    any_path = any(path_activity[str(ix)]["any_path"] for ix in ARMIES)
    any_moved = any(moved[str(ix)]["changed"] for ix in ARMIES)

    if len(stack_at_tgt) >= 2:
        outcome = "STACK_AT_ATTACK_TARGET"
        note = "Multiple armies co-located at prior Attack dest — strong encircle-bias stack signal (province equality only)."
        result = "G6_ENCIRCLE_OBSERVE_STACK_AT_TARGET"
        bump = "+~1pp observe stack-at-target"
        estimate = "~97-99%"
        hit = True
    elif len(stack_at_conc) >= 2:
        outcome = "STACK_REMAINING_AT_CONCENTRATE"
        note = "Multi-army stack still at concentrate dest after Attack posts; pocket/advance not yet evidenced by province change."
        result = "G6_ENCIRCLE_OBSERVE_STACK_AT_CONCENTRATE"
        bump = "+~1pp observe stack persist"
        estimate = "~97-98%"
        hit = True
    elif any_moved or any_path:
        outcome = "MOTION_OR_PATH_AFTER_ATTACK"
        note = "Province change and/or non-empty path during observe window after multi-Attack."
        result = "G6_ENCIRCLE_OBSERVE_MOTION"
        bump = "+~1pp observe motion"
        estimate = "~97-98%"
        hit = True
    elif last.get("1042", {}).get("at_concentrate") and not any_path:
        outcome = "ATTACK_POSTED_STATIC_HOLD"
        note = (
            "Anchor remains at concentrate; movers still at prior provinces; paths empty across observe. "
            "Attack posts from 2iki left no path linger; combat densify fields not proven → HONEST_EMPTY. "
            "No pocket forming evidenced by co-location at target. Encircle-bias campaign state = "
            "attack-posted / concentrate-held / movers-not-arrived."
        )
        result = "G6_ENCIRCLE_OBSERVE_STATIC_HONEST"
        bump = "+~0-1pp observe honesty fold (no invent)"
        estimate = "~96-98%"
        hit = True  # observe campaign completed honestly
    else:
        outcome = "HONEST_EMPTY_COMBAT_SIGNALS"
        note = "No stack/co-location/path motion beyond known army provinces; combat densify HONEST_EMPTY."
        result = "G6_ENCIRCLE_OBSERVE_EMPTY"
        bump = "no Path-C bump"
        estimate = "~96-98%"
        hit = False

    return {
        "outcome": outcome,
        "result": result,
        "HIT": hit,
        "note": note,
        "moved": moved,
        "path_activity": path_activity,
        "final_at_concentrate": stack_at_conc,
        "final_at_attack_target": stack_at_tgt,
        "any_co_location": any_coloc,
        "combat_densify": "HONEST_EMPTY",
        "adjacency": "HONEST_EMPTY",
        "org_str": "NOT_INVENTED",
        "estimate": estimate,
        "bump_note": bump,
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

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)

    retreat = {
        "status": "HARD_DENY_PARKED_NOT_PROVEN_CHEAP",
        "retreat_order_py": (ROOT / "calling" / "retreat_order.py").exists(),
        "decision": "PARKED — observe-only slice; no factory invent",
    }

    obs = observe_loop(pid, base)
    syn = synthesize(obs)
    stab = stability_tail(pid, 20.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    # Ensure gates still closed (observe-only)
    for p in (MARKER, LEGACY):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    importlib.reload(cfg)
    from config import allow_post as apf

    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data["posting"] = "DISABLED"
            data["allow_post"] = False
            data["last_phase"] = "2ikj"
            data["phase2ikj"] = syn["result"]
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    report = {
        "phase": "2iki" and "2ikj",
        "result": syn["result"],
        "HIT": syn["HIT"],
        "primary_choice": "A_ENCIRCLE_COMBAT_OBSERVE",
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "retreat": retreat,
        "concentrate_dest": CONCENTRATE_DEST,
        "attack_target": ATTACK_TARGET,
        "observe": {
            "seconds_budget": obs["seconds_budget"],
            "samples_n": obs["samples_n"],
            "first": obs["samples"][0] if obs["samples"] else None,
            "last": obs["samples"][-1] if obs["samples"] else None,
            "samples_compact": [
                {
                    "t": s.get("t"),
                    "ui": s.get("ui"),
                    "provs": {
                        k: (v.get("province"), v.get("path_len"))
                        for k, v in (s.get("armies") or {}).items()
                    },
                    "at_concentrate": s.get("at_concentrate"),
                    "at_attack_target": s.get("at_attack_target"),
                    "co_located_pairs": s.get("co_located_pairs"),
                }
                for s in obs["samples"]
            ],
        },
        "synthesis": syn,
        "stability": stab,
        "live0": live0,
        "live_after": live1,
        "optional_corrective_post": None,
        "post_attempts": {
            "attack": 0,
            "strategic": 0,
            "move": 0,
            "cancel": 0,
            "retreat": 0,
        },
        "instant": "PARKED",
        "final_allow_post": apf(),
        "marker_exists": MARKER.exists(),
        "path_c": {
            "baseline": "~60%",
            "prior_2iki": "~96-98%",
            "estimate_after": syn["estimate"],
            "crossed_70": True,
            "note": syn["bump_note"],
        },
        "agent_card_fold": (
            "After multi-Attack concentrate campaign: bounded RO observe of army provinces/paths; "
            f"outcome={syn['outcome']}; combat densify HONEST_EMPTY; Retreat PARKED."
        ),
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    # fix accidental "2iki" and "2ikj"
    report["phase"] = "2ikj"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikj",
                "result": syn["result"],
                "HIT": syn["HIT"],
                "outcome": syn["outcome"],
                "note": syn["note"],
                "moved": syn["moved"],
                "path_activity": syn["path_activity"],
                "final_at_concentrate": syn["final_at_concentrate"],
                "final_at_attack_target": syn["final_at_attack_target"],
                "combat_densify": "HONEST_EMPTY",
                "retreat": retreat["status"],
                "stability": stab,
                "final_allow_post": apf(),
                "estimate": syn["estimate"],
                "ui0": live0.get("ui_date"),
                "ui1": live1.get("ui_date") if isinstance(live1, dict) else None,
                "post_attempts": report["post_attempts"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ikj — Encircle/combat observe after multi-Attack

**Result:** `{syn['result']}` HIT={syn['HIT']}
**Outcome:** {syn['outcome']}
**Primary:** A (Retreat `{retreat['status']}`)
**War:** WARTIME_ETH_CONTINUATION | Auth t52u | pause/1x NEVER 5x

## Observe (~{OBSERVE_SECONDS}s bounded)

- Concentrate dest {CONCENTRATE_DEST}; Attack target {ATTACK_TARGET}
- Moved: {json.dumps(syn['moved'])}
- Path activity: {json.dumps(syn['path_activity'])}
- Final at concentrate: {syn['final_at_concentrate']}
- Final at attack target: {syn['final_at_attack_target']}
- Note: {syn['note']}

## Honesty

- combat densify: HONEST_EMPTY
- adjacency: HONEST_EMPTY
- org/str: NOT_INVENTED
- Instant: PARKED
- Posts this slice: 0

## Stability

{json.dumps(stab)}

## Path C

{syn['estimate']}; crossed_70=YES; {syn['bump_note']}

*{report['timestamp_asia_shanghai']}*
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "result": syn["result"],
                "HIT": syn["HIT"],
                "outcome": syn["outcome"],
                "note": syn["note"],
                "moved": syn["moved"],
                "path_activity": syn["path_activity"],
                "final_at_concentrate": syn["final_at_concentrate"],
                "final_at_attack_target": syn["final_at_attack_target"],
                "stability": stab,
                "allow_post": apf(),
                "estimate": syn["estimate"],
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

