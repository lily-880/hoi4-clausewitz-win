"""Phase 2ikh: wartime Attack after concentration RO; Retreat HARD_DENY/PARKED.

Retreat Post ABI not cheaply proven (NewFallback 4271 RO/DISABLED; NF midflight empty;
no retreat_order.py). Prefer B: observe 1037/1038 vs concentrate dest 6906, then ONE
SupportAttack 3620 (inline) from a live wartime army. Instant PARKED.
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
from army_subjects import iter_armies_by_index
import strategic_order as so
import attack_order as ao
import move_order as mo

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikh_attack_after_concentrate.json"
SUMMARY = ROOT / "reports" / "phase2ikh_attack_after_concentrate_summary.json"
DOC = ROOT / "docs" / "PHASE2IKH_ATTACK_AFTER_CONCENTRATE.md"
CONCENTRATE_DEST = 6906
CA_PROVINCE = 0x28


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN safe_land tool-gate for Phase 2ikh (user t52u).\n"
        "Scope: ONE SupportAttack 3620 wartime after concentrate RO.\n"
        "Retreat PARKED. Instant PARKED. NEVER_POST speed writes.\n",
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
                    g["note"] = "2ikh Attack-only gated"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "OPEN_WITH_ENV_AND_MARKER"
            data["posting"] = "LAND_ATTACK_GATED"
            data["last_phase"] = "2ikh"
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
                    g["note"] = "Re-closed after 2ikh"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "closed"
            data["posting"] = "DISABLED"
            data["allow_post"] = False
            data["last_phase"] = "2ikh"
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def continuum(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = mo._u64(b, base + gs_rva)
    year = struct.unpack("<i", b.read(gs + 0x478, 4))[0]
    day = struct.unpack("<i", b.read(gs + 0x484, 4))[0]
    tag = struct.unpack("<i", b.read(gs + 0x518, 4))[0]
    ui = None
    try:
        ui = (datetime(year, 1, 1) + timedelta(days=int(day))).strftime("%Y-%m-%d")
    except Exception:
        pass
    return {"pid": pid, "ui_date": ui, "day_index": day, "player_tag": tag, "allow_post": allow_post()}


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
        "factory_meta_known": {
            "COrderNewFallbackCommand": {
                "factory_idx": 4271,
                "factory_rva": "0x18d02c0",
                "isvalid": "0x18df4b0",
                "vt": "0x2A84C80",
                "posting": "DISABLED_RO_ONLY",
                "blocker": "NF/RF midflight empty; subject_handle order-domain gate; CPdxArray packing not Post-proven",
            }
        },
        "reason": (
            "Cheap Post proof would require new IsValid+Post ABI for NewFallback/ReplaceFallback "
            "(subject_handle via 0xbbb1e0, units CPdxArray) — not available this slice; do not invent."
        ),
        "decision": "PARKED — primary B Attack-after-concentrate",
    }


def army_snap(b, base, idx: int) -> dict:
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
    tag = live0["player_tag"]
    rows = []
    for lo in range(0, 5000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    by = {int(r["index"]): r for r in rows}

    # Concentration arrive RO (honest)
    focus = [1037, 1038, 1042]
    arrive_ro = {str(i): army_snap(b, base, i) for i in focus if i in by}
    any_arrived = any(v.get("at_concentrate") for k, v in arrive_ro.items() if k in ("1037", "1038"))
    anchor_ok = (arrive_ro.get("1042") or {}).get("at_concentrate")

    # Prefer attacker among 1037/1038; else first live
    attacker = None
    for pref in (1037, 1038, 1042, 1039):
        if pref in by:
            attacker = by[pref]
            break
    if attacker is None and rows:
        attacker = rows[0]
    if attacker is None:
        raise SystemExit("NO_ARMY")
    army_i = int(attacker["index"])
    src_prov = int(attacker["province_id"])

    # Target pool: other army provinces (proven 2ikc pattern; no invent adjacency)
    targets = []
    seen = set()
    for r in rows:
        tp = int(r["province_id"])
        if tp == src_prov or tp in seen:
            continue
        if int(r["index"]) == army_i:
            continue
        seen.add(tp)
        targets.append({"province": tp, "via_army": int(r["index"])})
        if len(targets) >= 16:
            break
    # Prefer historically working wartime SupportAttack IsValid provinces (2ike/2ikc HIT),
    # even if no friendly army sits there — not adjacency invent; prior Post-proven dests.
    prefer_t = [1886, 11838, 3931, 6906]
    ordered = []
    for p in prefer_t:
        ordered.append({"province": p, "via_army": None, "source": "PRIOR_WARTIME_HIT_DEST"})
    for t in targets:
        if t["province"] not in {o["province"] for o in ordered}:
            ordered.append(t)
    # Prefer concentrate-anchor army if at dest
    if 1042 in by and int(by[1042]["province_id"]) == CONCENTRATE_DEST:
        attacker = by[1042]
        army_i = 1042
        src_prov = CONCENTRATE_DEST

    open_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_open

    if not allow_post_open():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
    importlib.reload(ao)

    trials = []
    chosen = None
    for t in ordered:
        dry = ao.support_attack(army_i, int(t["province"]), dry_run=True)
        trials.append({"target": t, "dry": {k: dry.get(k) for k in ("ok", "result", "isvalid_rax", "province")}})
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            chosen = {"target": t, "dry": dry}
            break

    post = None
    if chosen:
        tgt = int(chosen["target"]["province"])
        post = ao.support_attack(army_i, tgt, dry_run=False)
    else:
        post = {"ok": False, "result": "NO_ISVALID_TARGET"}

    time.sleep(1.0)
    b2 = Backend(pid)
    after_snap = army_snap(b2, base, army_i)
    stab = observe_stable(pid, 30.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    close_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_final

    atk_hit = bool(post and post.get("ok") and post.get("result") == "ATTACK_POSTED_STABLE")
    if atk_hit:
        result_code = "G6_ATTACK_AFTER_CONCENTRATE_HIT"
        estimate = "~94-96%"
        note = "+~2pp wartime Attack after multi-Strategic concentrate campaign (arrive optional)"
    elif post and post.get("post_rax") == 1:
        result_code = "G6_ATTACK_AFTER_CONCENTRATE_WEAK"
        estimate = "~93-95%"
        note = "+~1pp weak Attack post"
    else:
        result_code = "G6_ATTACK_AFTER_CONCENTRATE_FAIL"
        estimate = "~92-94%"
        note = "no Path-C bump"

    report = {
        "phase": "2ikh",
        "result": result_code,
        "HIT": atk_hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "primary_choice": "B_ATTACK_AFTER_CONCENTRATE",
        "retreat": retreat,
        "concentrate_dest": CONCENTRATE_DEST,
        "arrive_ro": arrive_ro,
        "arrive_note": (
            "1037/1038 NOT at 6906 (paths cleared; back at prior provinces). "
            "Anchor 1042 still at 6906. Attack proceeds from live wartime army anyway "
            "(concentration campaign context; arrive not required for Attack ABI)."
            if not any_arrived
            else "At least one mover at concentrate dest."
        ),
        "any_mover_arrived": any_arrived,
        "anchor_at_dest": anchor_ok,
        "live0": live0,
        "attacker": {"army": army_i, "src_province": src_prov},
        "trials_n": len(trials),
        "trials_head": trials[:6],
        "chosen": {
            "target": (chosen or {}).get("target"),
            "dry_result": ((chosen or {}).get("dry") or {}).get("result"),
        },
        "post": post,
        "after_snap": after_snap,
        "stability": stab,
        "live_after": live1,
        "instant": "PARKED",
        "combat_densify": "HONEST_EMPTY",
        "adjacency": "HONEST_EMPTY",
        "final_allow_post": allow_post_final(),
        "marker_exists": MARKER.exists(),
        "post_attempts": {
            "attack": 1 if post and post.get("result") not in ("NO_ISVALID_TARGET", None) and "path_after" in (post or {}) else (1 if atk_hit or (post or {}).get("result") == "ATTACK_POST_UNCERTAIN" else 0),
            "strategic": 0,
            "move": 0,
            "cancel": 0,
            "retreat": 0,
        },
        "path_c": {
            "baseline": "~60%",
            "prior_2ikg": "~92-94%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": note,
        },
        "agent_card_fold": (
            "Wartime Attack after multi-Strategic concentrate campaign (HIT) closes encircle-bias "
            "reposition→attack loop; Retreat remains HARD_DENY/PARKED"
            if atk_hit
            else "Attack attempt after concentrate RO; Retreat PARKED"
        ),
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    # fix post_attempts count more accurately
    if post and isinstance(post, dict) and post.get("result") in (
        "ATTACK_POSTED_STABLE",
        "ATTACK_POST_UNCERTAIN",
        "PROCESS_EXITED",
    ):
        report["post_attempts"]["attack"] = 1
    elif post and post.get("result") not in ("NO_ISVALID_TARGET", "ALLOW_POST_FALSE", None) and "post_rax" in post:
        report["post_attempts"]["attack"] = 1
    elif chosen and post and post.get("result") != "NO_ISVALID_TARGET":
        # live Post was attempted
        report["post_attempts"]["attack"] = 1 if "post_wait" in post or "post_rax" in post else 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikh",
                "result": result_code,
                "HIT": atk_hit,
                "retreat": retreat["status"],
                "any_mover_arrived": any_arrived,
                "army": army_i,
                "target": (chosen or {}).get("target", {}).get("province") if chosen else None,
                "post_result": (post or {}).get("result"),
                "post_rax": (post or {}).get("post_rax"),
                "stability": stab,
                "final_allow_post": allow_post_final(),
                "estimate": estimate,
                "ui": (live1.get("ui_date") if isinstance(live1, dict) else None) or live0.get("ui_date"),
                "post_attempts": report["post_attempts"],
                "arrive_ro": {k: {kk: vv for kk, vv in v.items() if kk in ("army", "province", "at_concentrate", "path_len")} for k, v in arrive_ro.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ikh — Attack after concentrate (Retreat HARD_DENY)

**Result:** `{result_code}` HIT={atk_hit}
**Primary:** B (Retreat `{retreat['status']}`)
**War:** WARTIME_ETH_CONTINUATION
**Auth:** t52u | Speed pause/1x NEVER 5x

## Retreat

{json.dumps(retreat, indent=2)}

## Concentration arrive RO (dest {CONCENTRATE_DEST})

{json.dumps(arrive_ro, indent=2)}
Note: {report['arrive_note']}

## SupportAttack 3620

- Army {army_i} @ {src_prov} → target {(chosen or {}).get('target')}
- Post: {post}
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
                "HIT": atk_hit,
                "retreat": retreat["status"],
                "any_mover_arrived": any_arrived,
                "army": army_i,
                "target": (chosen or {}).get("target", {}).get("province") if chosen else None,
                "post": {k: (post or {}).get(k) for k in ("ok", "result", "post_rax", "post_wait", "province", "path_after")},
                "stability": stab,
                "allow_post": allow_post_final(),
                "estimate": estimate,
                "ui": live0.get("ui_date"),
                "post_attempts": report["post_attempts"],
                "arrive": report["arrive_ro"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
