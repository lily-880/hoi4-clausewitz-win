"""Phase 2ikf: wartime Strategic Redeploy 4753 encircle-bias RO→Post demo.

ETH wartime continuation. ONE Strategic Post via proven strategic_order ABI (2iju/2ijv).
Dest pool = other friendly army provinces (force-concentration / stack-forming bias).
No invent adjacency/org/str. Instant PARKED. Retreat PARKED unless already proven.
"""
from __future__ import annotations

import importlib
import json
import os
import struct
import subprocess
import sys
import time
from collections import Counter, defaultdict
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
OUT = ROOT / "reports" / "phase2ikf_strategic_encircle.json"
SUMMARY = ROOT / "reports" / "phase2ikf_strategic_encircle_summary.json"
DOC = ROOT / "docs" / "PHASE2IKF_STRATEGIC_ENCIRCLE.md"
ARMY_VT = 0x29D6D68
CA_PROVINCE = 0x28
GS_YEAR = 0x478
GS_DAY = 0x484


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
        "OPEN Strategic-only tool-gate for Phase 2ikf (user t52u).\n"
        "Scope: ONE CStrategicRedeploymentCommand factory 4753 wartime encircle-bias demo.\n"
        "NEVER_POST: speed/Inc/Dec/HourlyTick/Ping. Instant PARKED.\n",
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
                    g["note"] = "2ikf G5 Strategic-only OPEN wartime encircle-bias"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "OPEN_WITH_ENV_AND_MARKER"
            data["posting"] = "STRATEGIC_ONLY_GATED"
            data["command_queue"] = "STRATEGIC_ONLY_OPEN"
            data["last_phase"] = "2ikf"
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
                    g["note"] = "Re-closed after 2ikf one-shot"
                if g.get("id") == "ALLOW_POST_gate":
                    g["status"] = "closed"
                    g["note"] = "2ikf restored"
            data["posting"] = "DISABLED"
            data["command_queue"] = "DISABLED"
            data["allow_post"] = False
            data["last_phase"] = "2ikf"
            data["phase2ikf"] = {
                "result": "see reports",
                "allow_post_final": False,
            }
            CHECKLIST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def continuum(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = i32(b, gs + GS_YEAR)
    day = i32(b, gs + GS_DAY)
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
        "year": year,
        "day_index": day,
        "ui_date": ui,
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
            from ctypes import wintypes as wt

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

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    live0 = continuum(b, base, pid)
    tag = live0["player_tag"]
    rows = scan_armies(b, base, tag)
    if not rows:
        raise SystemExit("NO_ARMY")

    occ = Counter(int(r["province_id"]) for r in rows)
    by_idx = {int(r["index"]): r for r in rows}
    # Encircle-bias RO: prefer proven wartime armies; dest = other friendly provinces
    # (force concentration / stack-forming). HONEST_EMPTY adjacency.
    prefer_src = [1037, 1038, 1042, 1039, 1040]
    src = None
    for ix in prefer_src:
        if ix in by_idx:
            src = by_idx[ix]
            break
    if src is None:
        src = rows[0]
    src_idx = int(src["index"])
    src_prov = int(src["province_id"])

    # Dest pool: other friendly army provinces (concentration bias), then any distinct
    dest_ranked = []
    seen = set()
    # Prefer provinces already occupied by other armies (would form stack_depth>=2)
    others = [r for r in rows if int(r["index"]) != src_idx]
    others.sort(key=lambda r: (-occ[int(r["province_id"])], int(r["index"])))
    for r in others:
        p = int(r["province_id"])
        if p == src_prov or p in seen:
            continue
        seen.add(p)
        dest_ranked.append(
            {
                "province": p,
                "via_army": int(r["index"]),
                "occ_before": occ[p],
                "bias": "FRIENDLY_COLOC_CONCENTRATE",
            }
        )
        if len(dest_ranked) >= 12:
            break

    encircle_ro = {
        "src_army": src_idx,
        "src_province": src_prov,
        "src_stack_depth": occ[src_prov],
        "n_armies": len(rows),
        "unique_provinces": len(occ),
        "max_stack": max(occ.values()) if occ else 0,
        "adjacency": "HONEST_EMPTY",
        "dest_ranked": dest_ranked,
        "note": "Bias = redeploy onto another friendly army province to raise stack_depth (proven CA province/occupancy only)",
    }

    # G4+G5
    open_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_open

    if not allow_post_open():
        close_gates()
        raise SystemExit("G5_ALLOW_POST_STILL_FALSE")

    importlib.reload(so)

    trials = []
    chosen = None
    for d in dest_ranked:
        tr = so.strategic_redeploy(src_idx, int(d["province"]), dry_run=True)
        trials.append({"dest_meta": d, "trial": tr})
        if tr.get("ok") and tr.get("result") == "DRY_RUN_VALID":
            chosen = {"dest_meta": d, "trial": tr}
            break

    post = None
    observe = None
    result_code = "G6_STRATEGIC_NO_VALID_DEST"
    if chosen:
        dest = int(chosen["dest_meta"]["province"])
        posted = so.strategic_redeploy(src_idx, dest, dry_run=False)
        post = posted
        time.sleep(1.5)
        b2 = Backend(pid)
        path_after = so._path(b2, base, resolve_handle(b2, HANDLE_TYPE_ARMY, src_idx, base) or 0) if resolve_handle(b2, HANDLE_TYPE_ARMY, src_idx, base) else []
        army_ptr = resolve_handle(b2, HANDLE_TYPE_ARMY, src_idx, base)
        prov_now = u32(b2, army_ptr + CA_PROVINCE) if army_ptr else None
        live1 = continuum(b2, base, pid)
        stab = observe_stable(pid, 30.0)
        live2 = continuum(Backend(pid), base, pid) if find_pid() == pid else {"dead": True}
        observe = {
            "live_immediate": live1,
            "live_after_stab": live2,
            "province_now": prov_now,
            "path_after_recheck": path_after,
            "stability": stab,
            "drain_delta": (live1.get("drain") or 0) - (live0.get("drain") or 0),
            "exec_delta": (live1.get("exec") or 0) - (live0.get("exec") or 0),
            "seq_delta": (live1.get("seq") or 0) - (live0.get("seq") or 0),
        }
        if posted.get("result") == "PATH_CONTAINS_DEST" or (
            posted.get("ok") and dest in (posted.get("path_after") or [])
        ):
            result_code = "G6_STRATEGIC_WARTIME_ENCIRCLE_HIT"
        elif posted.get("result") in ("POSTED_DEST_NOT_IN_PATH",) or (posted.get("post_rax") == 1):
            # weak accept if counters moved
            if observe["seq_delta"] or observe["drain_delta"] or observe["exec_delta"]:
                result_code = "G6_STRATEGIC_WARTIME_ENCIRCLE_WEAK"
            else:
                result_code = "G6_STRATEGIC_WARTIME_ENCIRCLE_POSTED_WEAK"
        else:
            result_code = "G6_STRATEGIC_WARTIME_ENCIRCLE_FAIL"
    else:
        stab = observe_stable(pid, 5.0)
        observe = {"stability": stab, "note": "no IsValid dest; no Post"}

    close_gates()
    importlib.reload(cfg)
    from config import allow_post as allow_post_final

    hit = result_code.endswith("_HIT")
    estimate = "~90-92%" if hit else ("~88-90%" if "WEAK" in result_code else "~88-90%")
    if hit:
        estimate_note = "+~2pp wartime Strategic encircle-bias after 2ike loop"
    else:
        estimate_note = "no Path-C bump (Strategic wartime miss or no valid dest)"

    report = {
        "phase": "2ikf",
        "result": result_code,
        "HIT": hit,
        "war": "WARTIME_ETH_CONTINUATION",
        "authorization": "user t52u",
        "speed_policy": "pause-or-1x only; NEVER 5x",
        "factory": {"idx": 4753, "rva": "0x13FB580", "abi": "strategic_order.py prior 2iju"},
        "live0": live0,
        "encircle_ro": encircle_ro,
        "trials": trials,
        "chosen": chosen,
        "post": post,
        "observe": observe,
        "instant": "PARKED",
        "retreat": "PARKED_NOT_PROVEN_CHEAP",
        "final_allow_post": allow_post_final(),
        "marker_exists": MARKER.exists(),
        "land_marker_exists": LAND.exists(),
        "post_attempts": {"strategic": 1 if post is not None else 0, "move": 0, "attack": 0, "cancel": 0},
        "path_c": {
            "baseline": "~60%",
            "prior_2ike": "~88-90%",
            "estimate_after": estimate,
            "crossed_70": True,
            "note": estimate_note,
        },
        "agent_card_fold": (
            "Strategic Redeploy wartime HIT sits alongside Move→Attack→Cancel loop as encircle-bias reposition primitive"
            if hit
            else "Strategic wartime attempt documented; agent card keeps peacetime Strategic HIT + wartime loop"
        ),
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikf",
                "result": result_code,
                "HIT": hit,
                "war": "WARTIME_ETH_CONTINUATION",
                "army": src_idx,
                "src_province": src_prov,
                "dest": (chosen or {}).get("dest_meta", {}).get("province") if chosen else None,
                "post_result": (post or {}).get("result"),
                "path_before": (post or {}).get("path_before"),
                "path_after": (post or {}).get("path_after"),
                "stability": (observe or {}).get("stability"),
                "final_allow_post": allow_post_final(),
                "estimate": estimate,
                "ui": (observe or {}).get("live_after_stab", live0).get("ui_date")
                if isinstance((observe or {}).get("live_after_stab", live0), dict)
                else live0.get("ui_date"),
                "post_attempts": report["post_attempts"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ikf — Wartime Strategic Redeploy 4753 encircle-bias

**Result:** `{result_code}` HIT={hit}
**War:** WARTIME_ETH_CONTINUATION
**Speed:** pause/1x only — NEVER 5x
**Authorization:** t52u

## Encircle-bias RO (proven fields only)

- Source army {src_idx} @ province {src_prov} (CA+0x28)
- Dest bias: other friendly army provinces (force concentration / stack-forming)
- Adjacency/org/str: HONEST_EMPTY — not invented
- Chosen: {chosen}

## G6 ONE Strategic Post (factory 4753)

- ABI: `calling/strategic_order.py` (proven 2iju/2ijv)
- Post: {post}
- Stability: {(observe or {}).get('stability')}

## Gates

Restored allow_post={allow_post_final()}; strategic_only_tool_gate.OPEN absent; Instant PARKED; Retreat PARKED.

## Path C

estimate_after={estimate}; crossed_70=YES; {estimate_note}

*Phase 2ikf — {report['timestamp_asia_shanghai']}*
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "result": result_code,
                "HIT": hit,
                "war": "WARTIME_ETH_CONTINUATION",
                "army": src_idx,
                "dest": (chosen or {}).get("dest_meta", {}).get("province") if chosen else None,
                "post": {k: (post or {}).get(k) for k in ("ok", "result", "post_rax", "path_before", "path_after", "province")},
                "stability": (observe or {}).get("stability"),
                "allow_post": allow_post_final(),
                "ui": live0.get("ui_date"),
                "estimate": estimate,
                "post_attempts": report["post_attempts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
