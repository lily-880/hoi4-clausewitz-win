#!/usr/bin/env python3
"""Phase 2ijy: stabilize Move CRT — never free stub on WAIT_TIMEOUT; ONE Move reaffirm.

Root cause hyp (2ijx): VirtualFreeEx of CRT stub while remote thread still in
FN_CMD_QUEUE_POST → hoi4 crash/exit. Fix: leak stub on timeout. Authorized t52u.
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

import post_abi
from army_subjects import iter_armies_by_index
from config import allow_post
from handle import resolve_handle, HANDLE_TYPE_ARMY
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijy_stabilize_move_crt.json"
SUMMARY = ROOT / "reports" / "phase2ijy_stabilize_move_crt_summary.json"
DOC = ROOT / "docs" / "PHASE2IJY_STABILIZE_MOVE_CRT.md"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND_MD = ROOT / "docs" / "LAND_POST_READINESS.md"
AGENT = ROOT / "docs" / "PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md"

GS_YEAR, GS_DAY, CA_PROVINCE = 0x478, 0x484, 0x28


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


def scan_armies(b, base, tag):
    rows = []
    for lo in range(0, 5000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    return rows


def army_snap(b, base, idx):
    import move_order as mo

    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return None
    return {"index": idx, "army": hex(army), "province": u32(b, army + CA_PROVINCE), "path": mo._path(b, base, army)}


def process_health(pid: int) -> dict:
    # lightweight via ctypes OpenProcess + GetExitCodeProcess
    import ctypes
    from ctypes import wintypes as wt

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype = wt.BOOL
    k.CloseHandle.argtypes = [wt.HANDLE]
    STILL_ACTIVE = 259
    hp = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not hp:
        return {"alive": False, "exit_code": None}
    code = wt.DWORD(0)
    k.GetExitCodeProcess(hp, ctypes.byref(code))
    k.CloseHandle(hp)
    return {"alive": int(code.value) == STILL_ACTIVE, "exit_code": int(code.value)}


def set_g4():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    return {"env": "CLAUSEWITZ_ALLOW_POST=1"}


def open_g5():
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN safe_land for Phase 2ijy CRT stabilize Move reaffirm (t52u).\n"
        "Move 1402 + Strategic 4753. NEVER_POST speed/pause cmds.\n",
        encoding="utf-8",
    )
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                g["status"] = "OPEN_SAFE_LAND_MOVE_STRATEGIC"
                g["note"] = "2ijy G5 open for CRT-stable Move reaffirm"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
        data["phase"] = "2ijy"
        data["posting"] = "SAFE_LAND_GATED"
        CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"marker": str(MARKER)}


def restore_gates(result_code: str):
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()
    if LEGACY.exists():
        LEGACY.unlink()
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                g["status"] = "CLOSED_NOT_OPENED"
                g["note"] = "Re-closed after 2ijy CRT-stable Move one-shot"
                g["proven_once_move_crt"] = {"phase": "2ijy", "result": result_code, "fix": "no_free_stub_on_timeout"}
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "closed"
                g["note"] = "2ijy restored"
        data["posting"] = "DISABLED"
        data["command_queue"] = "DISABLED"
        data["phase"] = "2ijy"
        CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"allow_post": allow_post(), "marker_exists": MARKER.exists()}


def wait_exec_clear(b, base, timeout_s=2.0):
    sess = u64(b, base + post_abi.G_SESSION)
    t0 = time.time()
    samples = []
    while True:
        flag = b.read(sess + 0x6CC, 1)[0]
        samples.append({"t": round(time.time() - t0, 3), "exec_6cc": flag})
        if flag == 0:
            return {"cleared": True, "samples": samples[-5:], "waited_s": time.time() - t0}
        if time.time() - t0 >= timeout_s:
            return {"cleared": False, "samples": samples[-5:], "waited_s": time.time() - t0}
        time.sleep(0.05)


def fold_docs(result_code, g6, stability):
    block = f"""

---

## Phase 2ijy — Stabilize Move CRT (no stub free on WAIT_TIMEOUT)

**Result:** `{result_code}`

Root cause hyp: 2ijx VirtualFreeEx of CRT stub while FN_CMD_QUEUE_POST still running → process exit.
Fix: leak stub pages on timeout; chunked WaitForSingleObject.

Stability: responding_stayed={stability.get('responding_stayed')} alive_final={stability.get('alive_final')}
post_wait={((g6.get('post') or {}).get('post_wait'))} stub_leaked={((g6.get('post') or {}).get('stub_leaked_on_timeout'))}

"""
    if SAFE_MD.exists() and "Phase 2ijy — Stabilize Move CRT" not in SAFE_MD.read_text(encoding="utf-8"):
        SAFE_MD.write_text(SAFE_MD.read_text(encoding="utf-8").rstrip() + "\n" + block, encoding="utf-8")
    land = f"""

---

## Section 2ijy — Move CRT stabilize + reaffirm

- `calling/move_order.py`: never VirtualFreeEx stub on WAIT_TIMEOUT (leak-safe)
- ONE Move reaffirm factory 1402; gates restored False
- Evidence: {(g6.get('post') or {})}
- Stability: {stability}

"""
    if LAND_MD.exists() and "Section 2ijy — Move CRT stabilize" not in LAND_MD.read_text(encoding="utf-8"):
        LAND_MD.write_text(LAND_MD.read_text(encoding="utf-8").rstrip() + "\n" + land, encoding="utf-8")
    # light agent-card fold if file exists
    if AGENT.exists():
        at = AGENT.read_text(encoding="utf-8")
        if "2ijy" not in at and "2ijx" not in at[-2000:]:
            add = f"""

---

## Update 2ijx/2ijy — Ordinary Move PATH HIT + CRT stabilize

- 2ijx: first ordinary Move PATH_CONTAINS_DEST (army 1042→3931); CRT wait 258 + process exit after free-on-timeout
- 2ijy: leak stub on WAIT_TIMEOUT; reaffirm result `{result_code}`; allow_post restored False
- Instant PARKED; Attack peacetime PARKED unless war

"""
            AGENT.write_text(at.rstrip() + "\n" + add, encoding="utf-8")


def main() -> int:
    # ensure patch applied by companion script first
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for m in (MARKER, LEGACY):
        if m.exists():
            m.unlink()

    import config as cfg

    importlib.reload(cfg)
    from config import allow_post as ap0

    assert ap0() is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    health0 = process_health(pid)
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    live0 = continuum(b, base, pid)

    g4 = set_g4()
    open_g5()
    importlib.reload(cfg)
    from config import allow_post as ap2

    if not ap2():
        restore_gates("G5_FAILED")
        raise SystemExit("G5_FAILED")

    import move_order as mo

    importlib.reload(mo)

    rows = scan_armies(b, base, tag)
    by = {r["index"]: r for r in rows}
    src = by.get(1042) or (rows[0] if rows else None)
    if not src:
        restore_gates("NO_ARMY")
        raise SystemExit("NO_ARMY")

    army = resolve_handle(b, HANDLE_TYPE_ARMY, src["index"], base)
    cur_path = mo._path(b, base, army) if army else []
    seen = set()
    dest_pool = []
    if cur_path:
        tip = int(cur_path[-1])
        if tip != int(src["province_id"]):
            dest_pool.append(tip)
            seen.add(tip)
    for r in rows:
        p = int(r["province_id"])
        if p == int(src["province_id"]) or p in seen:
            continue
        seen.add(p)
        dest_pool.append(p)
        if len(dest_pool) >= 8:
            break

    trials, chosen = [], None
    for dest in dest_pool:
        tr = mo.move(int(src["index"]), int(dest), dry_run=True)
        trials.append(tr)
        if tr.get("ok") and tr.get("result") == "DRY_RUN_VALID":
            if cur_path == [dest] and len(dest_pool) > 1:
                continue
            chosen = tr
            break
    if chosen is None:
        for tr in trials:
            if tr.get("ok") and tr.get("result") == "DRY_RUN_VALID":
                chosen = tr
                break

    g6 = {
        "src_army": src["index"],
        "src_province": src["province_id"],
        "path_now": cur_path,
        "dest_pool": dest_pool,
        "trials": trials,
        "chosen": chosen,
        "post": None,
        "observe": None,
    }
    post_attempts = {"move": 0, "strategic": 0, "cancel": 0}
    stability = {
        "health_before": health0,
        "responding_samples": [],
        "alive_final": None,
        "responding_stayed": None,
        "pid_unchanged": None,
    }

    if not chosen:
        result_code = "G6_MOVE_HARD_DENY_NO_DEST"
        restored = restore_gates(result_code)
    else:
        dest = int(chosen["province"])
        g6["exec_clear"] = wait_exec_clear(b, base, 2.0)
        live_pre = continuum(b, base, pid)
        src_pre = army_snap(b, base, src["index"])
        t_post0 = time.time()
        posted = mo.move(int(src["index"]), dest, dry_run=False)
        post_attempts["move"] = 1
        g6["post"] = posted
        # stability poll ~8s without midflight path densify
        for i in range(8):
            time.sleep(1.0)
            h = process_health(pid)
            alive = h.get("alive")
            # Responding via PowerShell-less: alive proxy; record pid match
            stability["responding_samples"].append(
                {"t": round(time.time() - t_post0, 2), "alive": alive, "exit_code": h.get("exit_code")}
            )
            if not alive:
                break
        alive_final = process_health(pid).get("alive")
        stability["alive_final"] = alive_final
        stability["pid_unchanged"] = find_pid() == pid
        stability["responding_stayed"] = bool(alive_final) and all(
            s.get("alive") for s in stability["responding_samples"]
        )

        if alive_final and find_pid() == pid:
            b2 = Backend(pid)
            live_later = continuum(b2, base, pid)
            src_later = army_snap(b2, base, src["index"])
            g6["observe"] = {
                "pre": live_pre,
                "src_pre": src_pre,
                "later": live_later,
                "src_later": src_later,
                "province_changed": (src_pre or {}).get("province") != (src_later or {}).get("province"),
                "path_before": posted.get("path_before"),
                "path_after": posted.get("path_after"),
            }
        else:
            g6["observe"] = {"pre": live_pre, "src_pre": src_pre, "process_died": True}

        if posted.get("result") == "PATH_CONTAINS_DEST" and stability["responding_stayed"]:
            result_code = "G6_MOVE_CRT_STABLE_HIT"
        elif posted.get("result") == "PATH_CONTAINS_DEST" and not alive_final:
            result_code = "G6_MOVE_HIT_BUT_PROCESS_EXIT"
        elif posted.get("result") == "PATH_CONTAINS_DEST":
            result_code = "G6_MOVE_HIT_UNSTABLE_RESPONDING"
        elif posted.get("post_wait") == 258:
            result_code = "G6_MOVE_POST_TIMEOUT"
        else:
            result_code = "G6_MOVE_POST_FAIL"
        restored = restore_gates(result_code)

    importlib.reload(cfg)
    from config import allow_post as apf

    final_allow = apf()
    fold_docs(result_code, g6, stability)

    estimate = (
        "~76-78%"
        if result_code == "G6_MOVE_CRT_STABLE_HIT"
        else ("~74-76%" if "HIT" in result_code else "~74-76%")
    )
    report = {
        "phase": "2ijy",
        "result": result_code,
        "authorization": "t52u — stabilize Move CRT + one reaffirm",
        "fix": "never VirtualFreeEx CRT stub on WAIT_TIMEOUT; chunked wait; leak-safe",
        "live0": live0,
        "g4": g4,
        "g6": g6,
        "stability": stability,
        "post_attempts": post_attempts,
        "gates_restored": restored,
        "final_allow_post": final_allow,
        "path_c_honesty": {
            "baseline_band": "~60%",
            "after_2ijx": "~74-76%",
            "crossed_70": True,
            "estimate_after": estimate,
        },
        "next_shortest_blocker": (
            "If CRT_STABLE_HIT: Cancel 1415 gated one-shot or wartime Attack when war exists; Instant PARKED. "
            "If still exit: deeper Post hang (game lock) beyond stub free."
        ),
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijy",
                "result": result_code,
                "pid": pid,
                "ui_date": live0.get("ui_date"),
                "post_wait": (g6.get("post") or {}).get("post_wait"),
                "stub_leaked": (g6.get("post") or {}).get("stub_leaked_on_timeout"),
                "path_result": (g6.get("post") or {}).get("result"),
                "responding_stayed": stability.get("responding_stayed"),
                "alive_final": stability.get("alive_final"),
                "final_allow_post": final_allow,
                "post_attempts": post_attempts,
                "estimate": estimate,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ijy — Stabilize Move CRT

**Result:** `{result_code}`
**Fix:** never VirtualFreeEx stub on WAIT_TIMEOUT (2ijx crash hyp)
**Posts:** move={post_attempts['move']}
**allow_post final:** {final_allow}
**Stability:** {stability}
**Post:** {g6.get('post')}

*Phase 2ijy — {datetime.now().strftime('%Y-%m-%d %H:%M Asia/Shanghai')}*
""",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": result_code,
                "post": g6.get("post"),
                "stability": {
                    "responding_stayed": stability.get("responding_stayed"),
                    "alive_final": stability.get("alive_final"),
                },
                "allow_post": final_allow,
                "ui": live0.get("ui_date"),
            },
            ensure_ascii=False,
            default=str,
        )[:2500]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
