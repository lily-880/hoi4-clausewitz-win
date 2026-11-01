#!/usr/bin/env python3
"""Phase 2ijz: ONE Move Post with province_buf_kind=ucrt_malloc; stability observe.

Success: PATH_CONTAINS_DEST AND Responding/alive stayed True AND no 0xC0000374
for bounded observe (~45s). Authorized t52u.
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
from army_subjects import iter_armies_by_index
from config import allow_post
from handle import resolve_handle, HANDLE_TYPE_ARMY
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijz_move_ucrt_malloc.json"
SUMMARY = ROOT / "reports" / "phase2ijz_move_ucrt_malloc_summary.json"
DOC = ROOT / "docs" / "PHASE2IJZ_MOVE_UCRT_MALLOC.md"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND_MD = ROOT / "docs" / "LAND_POST_READINESS.md"
AGENT = ROOT / "docs" / "PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md"

GS_YEAR, GS_DAY, CA_PROVINCE = 0x478, 0x484, 0x28
OBSERVE_S = 45.0
DEST_POOL = [3931, 11838, 3898, 12857, 8757, 9979, 740, 9764]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


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
        "clock_class": "CONTINUOUS" if not (year == 1936 and day < 48) else "RELOAD_OR_NEW_CAMPAIGN",
        "drain": try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": try_u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "stage": try_u32(b, sess + post_abi.CSession_STAGE_COUNT),
        "gate725": b.read(sess + 0x725, 1)[0] if sess else None,
        "exec_6cc": b.read(sess + 0x6CC, 1)[0] if sess else None,
        "seq": try_u32(b, server + 0xD0) if server else None,
        "allow_post": allow_post(),
    }


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + 0x518)


def process_health(pid: int) -> dict:
    import ctypes
    from ctypes import wintypes as wt

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype = wt.BOOL
    k.CloseHandle.argtypes = [wt.HANDLE]
    STILL_ACTIVE = 259
    h = k.OpenProcess(0x1000 | 0x0400, False, pid)  # QUERY_LIMITED | QUERY
    if not h:
        return {"alive": False, "exit_code": None, "open_err": ctypes.get_last_error()}
    try:
        code = wt.DWORD(0)
        k.GetExitCodeProcess(h, ctypes.byref(code))
        c = int(code.value)
        return {"alive": c == STILL_ACTIVE, "exit_code": c}
    finally:
        k.CloseHandle(h)


def army_snap(b, base, idx):
    import move_order as mo

    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return None
    return {"index": idx, "army": hex(army), "province": u32(b, army + CA_PROVINCE), "path": mo._path(b, base, army)}


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("2ijz Move ucrt_malloc gated one-shot\n", encoding="utf-8")
    if LEGACY.exists():
        LEGACY.unlink()


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()
    if LEGACY.exists():
        LEGACY.unlink()


def fold_docs(result: str, ts: str):
    line_safe = (
        f"\n\n## 2ijz ({ts})\n"
        f"Move ucrt_malloc one-shot: **{result}**. "
        f"province_buf_kind=ucrt_malloc for live Post. allow_post restored False.\n"
    )
    line_land = (
        f"\n\n## 2ijz ({ts})\n"
        f"G6 Move with ucrt malloc: {result}. "
        f"Next: Cancel 1415 if HIT else heap/alloc follow-up.\n"
    )
    line_agent = (
        f"\n\n## 2ijz fold ({ts})\n"
        f"- Move Post ucrt_malloc: {result}.\n"
        f"- Instant PARKED. Attack PARKED peacetime. allow_post default False.\n"
    )
    for p, line in ((SAFE_MD, line_safe), (LAND_MD, line_land), (AGENT, line_agent)):
        t = p.read_text(encoding="utf-8") if p.exists() else ""
        if "2ijz" in t[-1200:]:
            continue
        p.write_text(t + line, encoding="utf-8")
    if CHECKLIST.exists():
        c = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    else:
        c = {}
    c["phase2ijz"] = {
        "result": result,
        "province_buf_kind": "ucrt_malloc",
        "allow_post_final": False,
        "ts": ts,
    }
    CHECKLIST.write_text(json.dumps(c, indent=2), encoding="utf-8")


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " Asia/Shanghai"
    pid0 = find_pid()
    if not pid0:
        raise SystemExit("NO_HOI4")
    b = Backend()
    base = b.image_base
    live0 = continuum(b, base, pid0)
    health0 = process_health(pid0)

    import move_order as mo

    # prefer army 1042
    tag = player_tag(b, base)
    src_army = 1042
    snap = army_snap(b, base, src_army)
    if not snap:
        # fallback first ITA army
        for lo in range(0, 5000, 500):
            rows = iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag)
            if rows:
                src_army = int(rows[0]["index"])
                snap = army_snap(b, base, src_army)
                break
    if not snap:
        raise SystemExit("NO_ARMY")

    trials = []
    chosen = None
    for dest in DEST_POOL:
        dry = mo.move(src_army, dest, dry_run=True)
        trials.append(dry)
        if dry.get("ok") and dry.get("result") == "DRY_RUN_VALID":
            chosen = dry
            break
    if not chosen:
        close_gates()
        out = {
            "phase": "2ijz",
            "result": "NO_VALID_DEST",
            "live0": live0,
            "trials": trials,
            "final_allow_post": allow_post(),
            "timestamp_asia_shanghai": ts,
        }
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps({"result": "NO_VALID_DEST", "allow_post": allow_post()}))
        return 2

    dest = int(chosen["province"])
    open_gates()
    g4 = {"env": "CLAUSEWITZ_ALLOW_POST=1", "marker": str(MARKER)}
    assert allow_post() is True

    t_post0 = time.time()
    post = mo.move(src_army, dest, dry_run=False)
    t_post1 = time.time()

    # wait exec_6cc clear briefly
    exec_samples = []
    t_clear0 = time.time()
    cleared = False
    while time.time() - t_clear0 < 5.0:
        try:
            b2 = Backend(pid0)
            sess = u64(b2, base + post_abi.G_SESSION)
            v = b2.read(sess + 0x6CC, 1)[0]
            exec_samples.append({"t": round(time.time() - t_clear0, 3), "exec_6cc": v})
            if v == 0:
                cleared = True
                break
        except Exception as e:
            exec_samples.append({"err": str(e)})
            break
        time.sleep(0.05)

    path_hit = post.get("result") == "PATH_CONTAINS_DEST"
    buf_kind = post.get("province_buf_kind")

    # stability observe
    samples = []
    responding_stayed = True
    heap_exit = False
    alive_final = True
    t0 = time.time()
    while time.time() - t0 < OBSERVE_S:
        h = process_health(pid0)
        alive = bool(h.get("alive"))
        code = h.get("exit_code")
        samples.append({"t": round(time.time() - t0, 2), "alive": alive, "exit_code": code})
        if not alive:
            responding_stayed = False
            alive_final = False
            if code == 3221226356:  # 0xC0000374
                heap_exit = True
            break
        time.sleep(1.0)
    else:
        h = process_health(pid0)
        alive_final = bool(h.get("alive"))
        responding_stayed = alive_final
        if h.get("exit_code") == 3221226356:
            heap_exit = True

    # path re-read if alive
    path_late = None
    live1 = None
    if alive_final:
        try:
            b3 = Backend(pid0)
            live1 = continuum(b3, base, pid0)
            path_late = army_snap(b3, base, src_army)
        except Exception as e:
            live1 = {"err": str(e)}

    close_gates()
    final_allow = allow_post()

    hit = bool(path_hit and responding_stayed and alive_final and not heap_exit and buf_kind == "ucrt_malloc")
    if hit:
        result = "G6_MOVE_UCRT_MALLOC_STABLE_HIT"
    elif path_hit and (not alive_final or heap_exit):
        result = "G6_MOVE_PATH_HIT_BUT_PROCESS_EXIT"
    elif path_hit and not responding_stayed:
        result = "G6_MOVE_PATH_HIT_BUT_NOT_RESPONDING"
    elif post.get("result") == "PROCESS_EXITED":
        result = "G6_MOVE_PROCESS_EXITED_DURING_POST"
    else:
        result = f"G6_MOVE_FAIL_{post.get('result', 'UNKNOWN')}"

    out = {
        "phase": "2ijz",
        "result": result,
        "HIT": hit,
        "authorization": "t52u — Move ucrt_malloc one-shot",
        "live0": live0,
        "health0": health0,
        "g4": g4,
        "g6": {
            "src_army": src_army,
            "src_snap": snap,
            "dest": dest,
            "trials": trials,
            "chosen": chosen,
            "post": post,
            "post_elapsed_s": round(t_post1 - t_post0, 3),
            "exec_clear": {"cleared": cleared, "samples": exec_samples},
            "path_late": path_late,
        },
        "stability": {
            "observe_s": OBSERVE_S,
            "samples": samples,
            "responding_stayed": responding_stayed,
            "alive_final": alive_final,
            "heap_exit_0xC0000374": heap_exit,
            "pid_unchanged": find_pid() == pid0 if alive_final else False,
        },
        "live1": live1,
        "province_buf_kind": buf_kind,
        "post_attempts": {"move": 1, "strategic": 0, "cancel": 0},
        "gates_restored": {"allow_post": final_allow, "marker_exists": MARKER.exists()},
        "final_allow_post": final_allow,
        "path_c_honesty": {
            "baseline_band": "~60%",
            "after_2ijy": "~74-76%",
            "crossed_70": True,
            "estimate_after": "~76-78%" if hit else "~74-76%",
        },
        "next_shortest_blocker": (
            "Cancel 1415 gated one-shot OR wartime Attack when war exists; Instant PARKED"
            if hit
            else "If heap again: confirm vector free path / alternate embed; if no path: IsValid/dest hunt. Instant PARKED."
        ),
        "timestamp_asia_shanghai": ts,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijz",
                "result": result,
                "HIT": hit,
                "province_buf_kind": buf_kind,
                "path_result": post.get("result"),
                "post_wait": post.get("post_wait"),
                "responding_stayed": responding_stayed,
                "alive_final": alive_final,
                "heap_exit": heap_exit,
                "final_allow_post": final_allow,
                "estimate": out["path_c_honesty"]["estimate_after"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"# Phase 2ijz — Move ucrt_malloc\n\n"
        f"## Result\n`{result}` HIT={hit}\n\n"
        f"- province_buf_kind={buf_kind}\n"
        f"- path={post.get('result')} post_wait={post.get('post_wait')}\n"
        f"- responding_stayed={responding_stayed} alive_final={alive_final} heap_exit={heap_exit}\n"
        f"- allow_post final={final_allow}\n",
        encoding="utf-8",
    )
    fold_docs(result, ts)
    print(
        json.dumps(
            {
                "result": result,
                "HIT": hit,
                "post": {
                    "ok": post.get("ok"),
                    "result": post.get("result"),
                    "province_buf_kind": buf_kind,
                    "post_wait": post.get("post_wait"),
                    "path_after": post.get("path_after"),
                },
                "stability": {
                    "responding_stayed": responding_stayed,
                    "alive_final": alive_final,
                    "heap_exit": heap_exit,
                },
                "allow_post": final_allow,
                "ui": (live1 or live0).get("ui_date") if isinstance(live1 or live0, dict) else None,
            }
        )
    )
    return 0 if hit else 1


if __name__ == "__main__":
    raise SystemExit(main())
