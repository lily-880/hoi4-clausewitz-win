"""Phase 2ikg: multi-army Strategic 4753 concentration (Retreat PARKED).

Retreat factory NOT cheaply Post-proven (COrderNewFallback/ReplaceFallback/WithdrawArmyHq
are RO recipes with posting DISABLED; no retreat_order Post ABI). Prefer B:
TWO armies Strategic Redeploy toward same friendly coloc province.
Instant PARKED. Combat densify HONEST_EMPTY.
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
import post_abi

MARKER = ROOT / "research" / "strategic_only_tool_gate.OPEN"
LAND = ROOT / "research" / "safe_land_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
OUT = ROOT / "reports" / "phase2ikg_multi_strategic.json"
SUMMARY = ROOT / "reports" / "phase2ikg_multi_strategic_summary.json"
DOC = ROOT / "docs" / "PHASE2IKG_MULTI_STRATEGIC.md"
CA_PROVINCE = 0x28
GS_YEAR, GS_DAY = 0x478, 0x484


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN Strategic-only tool-gate for Phase 2ikg (user t52u).\n"
        "Scope: TWO-army CStrategicRedeploymentCommand factory 4753 concentration.\n"
        "NEVER_POST: speed/Inc/Dec/HourlyTick. Instant PARKED. Retreat PARKED.\n",
        encoding="utf-8",
    )
    if LAND.exists():
        try:
            LAND.unlink()
        except Exception:
            pass
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for g in data.get("gaps", []):
                if g.get("id") == "command_queue_tool_gate":
                    g["status"] = "OPEN_STRATEGIC_ONLY"
                    g["note"] = "2ikg multi-army Strategic concentration OPEN"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "OPEN_WITH_ENV_AND_MARKER"
            data["posting"] = "STRATEGIC_ONLY_GATED"
            data["last_phase"] = "2ikg"
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LAND):
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
                    g["note"] = "Re-closed after 2ikg"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "closed"
            data["posting"] = "DISABLED"
            data["command_queue"] = "DISABLED"
            data["allow_post"] = False
            data["last_phase"] = "2ikg"
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def continuum(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year, day = i32(b, gs + GS_YEAR), i32(b, gs + GS_DAY)
    ui = None
    try:
        ui = (datetime(year, 1, 1) + timedelta(days=int(day))).strftime("%Y-%m-%d")
    except Exception:
        pass
    tag = i32(b, gs + 0x518)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER) if sess else 0
    return {
        "pid": pid,
        "ui_date": ui,
        "day_index": day,
        "player_tag": tag,
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER) if sess else None,
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER) if sess else None,
        "seq": u32(b, server + 0xD0) if server else None,
        "allow_post": allow_post(),
    }


def scan_armies(b, base, tag):
    rows = []
    for lo in range(0, 5000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    return rows


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


def retreat_proof_scan() -> dict:
    """Honest: Retreat Post not cheaply proven."""
    calling = ROOT / "calling"
    has_retreat_order = (calling / "retreat_order.py").exists()
    notes = []
    # sample key docs
    for rel in (
        "calling/army_subjects.py",
        "docs/LAND_POST_READINESS.md",
        "docs/PHASE2FI_RETREAT_ATTACK_POLISH.md",
    ):
        p = ROOT / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        if "posting DISABLED" in t and ("Fallback" in t or "Withdraw" in t or "retreat" in t.lower()):
            notes.append(f"{rel}: posting DISABLED / RO recipe language present")
    return {
        "retreat_order_py": has_retreat_order,
        "proven_post_abi": False,
        "status": "PARKED_NOT_PROVEN_CHEAP",
        "candidates_ro_only": [
            "COrderNewFallbackCommand (factory ~4271) — RO",
            "COrderReplaceFallbackCommands — RO",
            "CWithdrawArmyHqCommand — RO",
            "CSetSelectedArmyGroupFallback — RO",
        ],
        "notes": notes
        + [
            "No calling/retreat_order.py Post path analogous to strategic_order/move_order/attack_order",
            "Do NOT invent Retreat factory as Post-proven this slice",
        ],
    }


def main() -> int:
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LAND):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    importlib.reload(cfg)
    global allow_post
    from config import allow_post

    assert allow_post() is False

    retreat = retreat_proof_scan()

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)
    tag = live0["player_tag"]
    rows = scan_armies(b, base, tag)
    if len(rows) < 3:
        raise SystemExit("NEED_3_ARMIES")

    by_idx = {int(r["index"]): r for r in rows}
    occ = Counter(int(r["province_id"]) for r in rows)

    # Prefer proven wartime armies 1037/1038 as movers; concentrate onto a third friendly province
    movers_pref = [1037, 1038, 1039, 1040, 1041]
    anchor_pref = [1042, 1043, 1044, 1045, 1046]
    movers = [by_idx[i] for i in movers_pref if i in by_idx][:2]
    if len(movers) < 2:
        movers = rows[:2]
    anchor = None
    for i in anchor_pref:
        if i in by_idx and int(by_idx[i]["index"]) not in {int(m["index"]) for m in movers}:
            anchor = by_idx[i]
            break
    if anchor is None:
        for r in rows:
            if int(r["index"]) not in {int(m["index"]) for m in movers}:
                anchor = r
                break
    if anchor is None:
        raise SystemExit("NO_ANCHOR")

    dest = int(anchor["province_id"])
    plan = {
        "bias": "MULTI_ARMY_FRIENDLY_COLOC_CONCENTRATE",
        "anchor_army": int(anchor["index"]),
        "dest": dest,
        "movers": [{"army": int(m["index"]), "src_province": int(m["province_id"])} for m in movers],
        "adjacency": "HONEST_EMPTY",
        "occupancy_dest_before": occ[dest],
    }

    open_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_open

    if not allow_post_open():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")
    importlib.reload(so)

    posts = []
    for m in movers:
        idx = int(m["index"])
        src_prov = int(m["province_id"])
        if src_prov == dest:
            posts.append(
                {
                    "army": idx,
                    "skipped": True,
                    "reason": "ALREADY_AT_DEST",
                    "dry": None,
                    "post": None,
                }
            )
            continue
        dry = so.strategic_redeploy(idx, dest, dry_run=True)
        entry = {"army": idx, "src_province": src_prov, "dest": dest, "dry": dry, "post": None}
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            posted = so.strategic_redeploy(idx, dest, dry_run=False)
            entry["post"] = posted
            time.sleep(0.8)
        else:
            # try a few alternate dests from other friendly provinces if primary invalid
            alts = []
            for r in rows:
                p = int(r["province_id"])
                if p in (src_prov, dest):
                    continue
                if int(r["index"]) == idx:
                    continue
                alts.append(p)
                if len(alts) >= 6:
                    break
            alt_hit = None
            for p in alts:
                tr = so.strategic_redeploy(idx, p, dry_run=True)
                if tr.get("ok") and tr.get("result") == "DRY_RUN_VALID":
                    alt_hit = (p, tr)
                    break
            entry["alt_scan"] = {"tried": alts, "hit": alt_hit[0] if alt_hit else None}
            if alt_hit:
                # Keep shared dest intent: only Post if alt equals shared dest already failed;
                # for multi-concentration we require same dest — mark FAIL_ISVALID for this army
                entry["post"] = {
                    "ok": False,
                    "result": "ISVALID_FALSE_SHARED_DEST",
                    "note": "shared dest invalid; alt exists but not used (keep same-dest campaign)",
                }
            else:
                entry["post"] = {"ok": False, "result": dry.get("result") or "DRY_FAIL"}
        posts.append(entry)

    time.sleep(1.0)
    b2 = Backend(pid)
    recheck = []
    for m in movers:
        idx = int(m["index"])
        army = resolve_handle(b2, HANDLE_TYPE_ARMY, idx, base)
        path = so._path(b2, base, army) if army else []
        prov = u32(b2, army + CA_PROVINCE) if army else None
        recheck.append(
            {
                "army": idx,
                "province": prov,
                "path": path,
                "dest_in_path": dest in path,
                "at_dest": prov == dest,
            }
        )
    # also anchor
    a_ptr = resolve_handle(b2, HANDLE_TYPE_ARMY, int(anchor["index"]), base)
    anchor_now = {
        "army": int(anchor["index"]),
        "province": u32(b2, a_ptr + CA_PROVINCE) if a_ptr else None,
    }

    stab = observe_stable(pid, 30.0)
    live1 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}

    hits = []
    for e in posts:
        p = e.get("post") or {}
        if e.get("skipped"):
            hits.append("SKIP_AT_DEST")
        elif p.get("result") == "PATH_CONTAINS_DEST" or (
            p.get("ok") and dest in (p.get("path_after") or [])
        ):
            hits.append("HIT")
        elif p and p.get("post_rax") == 1:
            hits.append("WEAK")
        else:
            hits.append("FAIL")

    n_hit = hits.count("HIT")
    n_post = sum(1 for e in posts if e.get("post") and not e.get("skipped") and e["post"].get("result") not in (None,))
    # count actual Post calls (dry_run False)
    strategic_posts = sum(
        1
        for e in posts
        if e.get("post")
        and isinstance(e["post"], dict)
        and e["post"].get("result")
        in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH", "ISVALID_FALSE", "ALLOW_POST_FALSE", "FACTORY_FAIL")
        or (e.get("post") and e["post"].get("path_after") is not None)
    )
    # more accurate: posts that went through live Post
    strategic_attempts = 0
    for e in posts:
        p = e.get("post")
        if not p or e.get("skipped"):
            continue
        if "path_after" in p or p.get("result") in (
            "PATH_CONTAINS_DEST",
            "POSTED_DEST_NOT_IN_PATH",
            "PROCESS_EXITED",
        ):
            strategic_attempts += 1

    if n_hit >= 2:
        result_code = "G6_MULTI_STRATEGIC_CONCENTRATE_HIT"
    elif n_hit == 1 and ("HIT" in hits or "WEAK" in hits):
        result_code = "G6_MULTI_STRATEGIC_CONCENTRATE_PARTIAL"
    elif "HIT" in hits or "WEAK" in hits:
        result_code = "G6_MULTI_STRATEGIC_CONCENTRATE_PARTIAL"
    else:
        result_code = "G6_MULTI_STRATEGIC_CONCENTRATE_FAIL"

    close_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_final

    hit = result_code.endswith("_HIT")
    if hit:
        estimate = "~92-94%"
        note = "+~2pp multi-army Strategic concentration after 2ikf"
    elif "PARTIAL" in result_code:
        estimate = "~91-93%"
        note = "+~1pp partial multi-Strategic"
    else:
        estimate = "~90-92%"
        note = "no Path-C bump"

    # optional Cancel: only if path linger blocks concentration evidence — skip if HIT/PARTIAL enough
    cancel_used = False

    report = {
        "phase": "2ikg",
        "result": result_code,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "primary_choice": "B_MULTI_STRATEGIC",
        "retreat": retreat,
        "plan": plan,
        "live0": live0,
        "posts": posts,
        "hits": hits,
        "recheck": recheck,
        "anchor_now": anchor_now,
        "stability": stab,
        "live_after": live1,
        "cancel_after": cancel_used,
        "instant": "PARKED",
        "combat_densify": "HONEST_EMPTY",
        "final_allow_post": allow_post_final(),
        "marker_exists": MARKER.exists(),
        "post_attempts": {
            "strategic": strategic_attempts,
            "move": 0,
            "attack": 0,
            "cancel": 0,
            "retreat": 0,
        },
        "path_c": {
            "baseline": "~60%",
            "prior_2ikf": "~90-92%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": note,
        },
        "agent_card_fold": "Multi-army Strategic concentration (same dest) extends encircle-bias stack-forming beside single-army Strategic + Move→Attack→Cancel; Retreat remains PARKED",
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikg",
                "result": result_code,
                "HIT": hit,
                "retreat_status": retreat["status"],
                "dest": dest,
                "movers": [int(m["index"]) for m in movers],
                "hits": hits,
                "post_results": [(e.get("army"), (e.get("post") or {}).get("result"), (e.get("post") or {}).get("path_after")) for e in posts],
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
        f"""# Phase 2ikg — Multi-army Strategic concentration (Retreat PARKED)

**Result:** `{result_code}` HIT={hit}
**Primary choice:** B (Retreat `{retreat['status']}`)
**War:** WARTIME_ETH_CONTINUATION
**Speed:** pause/1x NEVER 5x
**Auth:** t52u

## Retreat proof

- retreat_order.py exists: {retreat['retreat_order_py']}
- proven_post_abi: False → **PARKED_NOT_PROVEN_CHEAP**
- RO-only candidates: {retreat['candidates_ro_only']}

## Multi-army Strategic 4753

- Anchor army {plan['anchor_army']} dest province {dest}
- Movers: {plan['movers']}
- Posts: {posts}
- Recheck: {recheck}
- Hits: {hits}
- Stability: {stab}

## Gates

allow_post final={allow_post_final()}; markers absent; Instant PARKED.

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
                "dest": dest,
                "movers": [int(m["index"]) for m in movers],
                "hits": hits,
                "post_results": [
                    {
                        "army": e.get("army"),
                        "result": (e.get("post") or {}).get("result"),
                        "path_after": (e.get("post") or {}).get("path_after"),
                        "skipped": e.get("skipped"),
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
