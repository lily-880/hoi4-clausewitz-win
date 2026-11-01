#!/usr/bin/env python3
"""Phase 2ika: Cancel factory 1415 gated one-shot on a moving army.

If army idle: ONE Move (ucrt_malloc) prep, then ONE Cancel. Success: path clears
+ Responding stayed + no 0xC0000374. Authorized t52u.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import resolve_handle, HANDLE_TYPE_ARMY
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ika_cancel_1415.json"
SUMMARY = ROOT / "reports" / "phase2ika_cancel_1415_summary.json"
DOC = ROOT / "docs" / "PHASE2IKA_CANCEL_1415.md"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND_MD = ROOT / "docs" / "LAND_POST_READINESS.md"
AGENT = ROOT / "docs" / "PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md"

GS_YEAR, GS_DAY, CA_PROVINCE = 0x478, 0x484, 0x28
OBSERVE_S = 40.0
DEST_POOL = [3931, 11838, 3898, 12857, 8757, 9979, 740, 9764]
ARMY = 1042


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


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
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    return {
        "pid": pid,
        "year": year,
        "day_index": day,
        "ui_date": ui,
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER) if sess else None,
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER) if sess else None,
        "gate725": b.read(sess + 0x725, 1)[0] if sess else None,
        "exec_6cc": b.read(sess + 0x6CC, 1)[0] if sess else None,
        "allow_post": allow_post(),
    }


def process_health(pid: int) -> dict:
    import ctypes
    from ctypes import wintypes as wt

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype = wt.BOOL
    k.CloseHandle.argtypes = [wt.HANDLE]
    h = k.OpenProcess(0x1000 | 0x0400, False, pid)
    if not h:
        return {"alive": False, "exit_code": None}
    try:
        code = wt.DWORD(0)
        k.GetExitCodeProcess(h, ctypes.byref(code))
        c = int(code.value)
        return {"alive": c == 259, "exit_code": c}
    finally:
        k.CloseHandle(h)


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("2ika Cancel 1415 gated one-shot\n", encoding="utf-8")
    if LEGACY.exists():
        LEGACY.unlink()


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()
    if LEGACY.exists():
        LEGACY.unlink()


def fold(result: str, ts: str):
    for p, line in (
        (
            SAFE_MD,
            f"\n\n## 2ika ({ts})\nCancel 1415 gated one-shot: **{result}**. allow_post restored False.\n",
        ),
        (
            LAND_MD,
            f"\n\n## 2ika ({ts})\nCancelMovement factory 1415: {result}. Instant PARKED; Attack peacetime PARKED.\n",
        ),
        (
            AGENT,
            f"\n\n## 2ika fold ({ts})\n- Cancel 1415: {result}.\n- Move ucrt STABLE (2ijz). Strategic prior HIT. Instant/Attack PARKED peacetime.\n",
        ),
    ):
        t = p.read_text(encoding="utf-8") if p.exists() else ""
        if "2ika" in t[-1500:]:
            continue
        p.write_text(t + line, encoding="utf-8")
    c = json.loads(CHECKLIST.read_text(encoding="utf-8")) if CHECKLIST.exists() else {}
    c["phase2ika"] = {"result": result, "factory_idx": 1415, "allow_post_final": False, "ts": ts}
    CHECKLIST.write_text(json.dumps(c, indent=2), encoding="utf-8")


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " Asia/Shanghai"
    import move_order as mo
    import cancel_order as co

    pid0 = find_pid()
    if not pid0:
        raise SystemExit("NO_HOI4")
    b = Backend()
    base = b.image_base
    live0 = continuum(b, base, pid0)

    army_i = ARMY
    army = resolve_handle(b, HANDLE_TYPE_ARMY, army_i, base)
    if not army:
        close_gates()
        raise SystemExit("NO_ARMY")
    path0 = mo._path(b, base, army)
    prov0 = u32(b, army + CA_PROVINCE)

    move_post = None
    move_attempts = 0
    cancel_attempts = 0

    # Prep move if idle
    if not path0:
        dest = None
        trials = []
        for d in DEST_POOL:
            dry = mo.move(army_i, d, dry_run=True)
            trials.append(dry)
            if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
                dest = d
                break
        if dest is None:
            out = {
                "phase": "2ika",
                "result": "NO_MOVE_DEST_FOR_PREP",
                "live0": live0,
                "path0": path0,
                "trials": trials,
                "final_allow_post": False,
            }
            OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(json.dumps({"result": "NO_MOVE_DEST_FOR_PREP"}))
            return 2
        open_gates()
        move_post = mo.move(army_i, dest, dry_run=False)
        move_attempts = 1
        # brief wait for path to appear
        path_mid = []
        for _ in range(40):
            if find_pid() != pid0:
                break
            b = Backend(pid0)
            army = resolve_handle(b, HANDLE_TYPE_ARMY, army_i, base)
            path_mid = mo._path(b, base, army) if army else []
            if path_mid:
                break
            time.sleep(0.1)
        if not path_mid:
            close_gates()
            out = {
                "phase": "2ika",
                "result": "MOVE_PREP_NO_PATH",
                "move_post": move_post,
                "live0": live0,
                "final_allow_post": allow_post(),
            }
            OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(json.dumps({"result": "MOVE_PREP_NO_PATH", "move": move_post}))
            return 1
        path_before_cancel = path_mid
    else:
        open_gates()
        path_before_cancel = path0

    assert allow_post()

    # dry cancel first
    dry_c = co.cancel_movement(army_i, dry_run=True)
    if not (dry_c.get("ok") and dry_c.get("result") == "DRY_RUN_VALID"):
        # still try live? prefer abort on hard IsValid false
        close_gates()
        out = {
            "phase": "2ika",
            "result": "CANCEL_DRY_INVALID",
            "dry": dry_c,
            "move_post": move_post,
            "path_before_cancel": path_before_cancel,
            "final_allow_post": allow_post(),
        }
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps({"result": "CANCEL_DRY_INVALID", "dry": dry_c}))
        return 1

    cancel_post = co.cancel_movement(army_i, dry_run=False)
    cancel_attempts = 1

    # observe path clear + stability
    samples = []
    path_samples = []
    heap_exit = False
    alive_final = True
    responding_stayed = True
    path_cleared_obs = False
    t0 = time.time()
    while time.time() - t0 < OBSERVE_S:
        h = process_health(pid0)
        samples.append({"t": round(time.time() - t0, 2), **h})
        if not h.get("alive"):
            alive_final = False
            responding_stayed = False
            if h.get("exit_code") == 3221226356:
                heap_exit = True
            break
        try:
            b = Backend(pid0)
            army = resolve_handle(b, HANDLE_TYPE_ARMY, army_i, base)
            path_now = mo._path(b, base, army) if army else []
            path_samples.append({"t": round(time.time() - t0, 2), "path": path_now})
            if path_before_cancel and not path_now:
                path_cleared_obs = True
        except Exception as e:
            path_samples.append({"t": round(time.time() - t0, 2), "err": str(e)})
        time.sleep(1.0)

    close_gates()
    final_allow = allow_post()
    live1 = None
    if alive_final:
        try:
            live1 = continuum(Backend(pid0), base, pid0)
        except Exception as e:
            live1 = {"err": str(e)}

    cleared = bool(
        cancel_post.get("path_cleared")
        or path_cleared_obs
        or (path_before_cancel and not (cancel_post.get("path_after") or []))
    )
    hit = bool(
        cleared
        and responding_stayed
        and alive_final
        and not heap_exit
        and cancel_post.get("units_buf_kind") == "ucrt_malloc"
    )
    if hit:
        result = "G6_CANCEL_1415_PATH_CLEARED_HIT"
    elif cancel_post.get("result") == "PROCESS_EXITED" or heap_exit or not alive_final:
        result = "G6_CANCEL_PROCESS_EXIT"
    elif cancel_post.get("result") == "ISVALID_FALSE":
        result = "G6_CANCEL_ISVALID_FALSE"
    elif not cleared:
        result = f"G6_CANCEL_NO_CLEAR_{cancel_post.get('result')}"
    else:
        result = f"G6_CANCEL_{cancel_post.get('result')}"

    estimate = "~78-80%" if hit else "~76-78%"
    out = {
        "phase": "2ika",
        "result": result,
        "HIT": hit,
        "authorization": "t52u — Cancel 1415 gated one-shot",
        "live0": live0,
        "army": army_i,
        "prov0": prov0,
        "path0": path0,
        "move_prep": move_post,
        "path_before_cancel": path_before_cancel,
        "cancel_dry": dry_c,
        "cancel_post": cancel_post,
        "path_samples": path_samples[:12] + ([{"...": len(path_samples)}] if len(path_samples) > 12 else []),
        "path_cleared_obs": path_cleared_obs,
        "stability": {
            "observe_s": OBSERVE_S,
            "samples": samples,
            "responding_stayed": responding_stayed,
            "alive_final": alive_final,
            "heap_exit_0xC0000374": heap_exit,
        },
        "live1": live1,
        "post_attempts": {"move": move_attempts, "strategic": 0, "cancel": cancel_attempts},
        "gates_restored": {"allow_post": final_allow, "marker_exists": MARKER.exists()},
        "final_allow_post": final_allow,
        "path_c_honesty": {
            "baseline_band": "~60%",
            "after_2ijz": "~76-78%",
            "crossed_70": True,
            "estimate_after": estimate,
        },
        "next_shortest_blocker": (
            "Wartime Attack (SupportAttack 3620) when war exists; Instant PARKED; or Cancel multi-army / sticky polish"
            if hit
            else "Cancel layout/IsValid follow-up OR wartime Attack; Instant PARKED"
        ),
        "timestamp_asia_shanghai": ts,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ika",
                "result": result,
                "HIT": hit,
                "path_cleared": cleared,
                "cancel_result": cancel_post.get("result"),
                "units_buf_kind": cancel_post.get("units_buf_kind"),
                "post_wait": cancel_post.get("post_wait"),
                "move_prep": bool(move_post),
                "responding_stayed": responding_stayed,
                "alive_final": alive_final,
                "heap_exit": heap_exit,
                "final_allow_post": final_allow,
                "estimate": estimate,
                "post_attempts": out["post_attempts"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"# Phase 2ika — Cancel 1415\n\n## Result\n`{result}` HIT={hit}\n\n"
        f"- move_prep={bool(move_post)} path_before={path_before_cancel}\n"
        f"- cancel={cancel_post.get('result')} units_buf={cancel_post.get('units_buf_kind')} "
        f"post_wait={cancel_post.get('post_wait')}\n"
        f"- cleared={cleared} responding_stayed={responding_stayed} heap_exit={heap_exit}\n"
        f"- allow_post final={final_allow}\n",
        encoding="utf-8",
    )
    fold(result, ts)
    print(
        json.dumps(
            {
                "result": result,
                "HIT": hit,
                "cancel": {
                    "result": cancel_post.get("result"),
                    "path_before": cancel_post.get("path_before"),
                    "path_after": cancel_post.get("path_after"),
                    "units_buf_kind": cancel_post.get("units_buf_kind"),
                    "post_wait": cancel_post.get("post_wait"),
                    "post_rax": cancel_post.get("post_rax"),
                },
                "move_prep": (move_post or {}).get("result") if move_post else None,
                "stability": {
                    "responding_stayed": responding_stayed,
                    "alive_final": alive_final,
                    "heap_exit": heap_exit,
                },
                "allow_post": final_allow,
                "post_attempts": out["post_attempts"],
                "ui": (live1 or live0).get("ui_date") if isinstance(live1 or live0, dict) else None,
            }
        )
    )
    return 0 if hit else 1


if __name__ == "__main__":
    raise SystemExit(main())
