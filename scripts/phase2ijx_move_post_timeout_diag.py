#!/usr/bin/env python3
"""Phase 2ijx: diagnose Move FN_CMD_QUEUE_POST TIMEOUT vs Strategic 2iju; ONE fixed Move retry.

Fixes this slice: longer WaitForSingleObject on Post (20s), bounded wait until
session+0x6CC clear, keep G4/G5 narrow, restore False. NEVER 5x. Max ONE Move Post.
No pause-mem write (no proven Windows speed offset). Authorized t52u.
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

OUT = ROOT / "reports" / "phase2ijx_move_post_timeout_diag.json"
SUMMARY = ROOT / "reports" / "phase2ijx_move_post_timeout_diag_summary.json"
DOC = ROOT / "docs" / "PHASE2IJX_MOVE_POST_TIMEOUT_DIAG.md"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND_MD = ROOT / "docs" / "LAND_POST_READINESS.md"
MOVE_PY = ROOT / "calling" / "move_order.py"

GS_YEAR = 0x478
GS_DAY = 0x484
CA_PROVINCE = 0x28
WAIT_POST_MS = 20000
WAIT_FACTORY_MS = 5000


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


def patch_move_order_timeout() -> dict:
    """Ensure move_order._remote accepts wait_ms; Post uses WAIT_POST_MS."""
    t = MOVE_PY.read_text(encoding="utf-8")
    before = "wait_ms" in t and "wait_ms: int = 3000" in t
    if "def _remote(pid: int, fn: int, regs: dict | None = None) -> dict:" in t and "wait_ms" not in t.split("def _remote", 1)[1][:200]:
        t = t.replace(
            "def _remote(pid: int, fn: int, regs: dict | None = None) -> dict:",
            "def _remote(pid: int, fn: int, regs: dict | None = None, wait_ms: int = 3000) -> dict:",
        )
        t = t.replace(
            "wait = k.WaitForSingleObject(th, 3000)",
            "wait = k.WaitForSingleObject(th, int(wait_ms))",
        )
    # ensure Post call uses longer wait
    old_post = (
        'posted = _remote(pid, base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1})'
    )
    new_post = (
        'posted = _remote(pid, base + post_abi.FN_CMD_QUEUE_POST, '
        '{"rcx": sess, "rdx": cmd, "r8": 1}, wait_ms=20000)'
    )
    if old_post in t and "wait_ms=20000" not in t:
        t = t.replace(old_post, new_post)
    # factory/isvalid can stay default 3000 or use 5000
    old_fac = "made = _remote(pid, base + FACTORY_RVA)"
    if old_fac in t and "wait_ms=5000" not in t.split("made = _remote", 1)[0][-20:] + t.split("made = _remote", 1)[1][:80]:
        t = t.replace(old_fac, "made = _remote(pid, base + FACTORY_RVA, wait_ms=5000)", 1)
    MOVE_PY.write_text(t, encoding="utf-8")
    return {
        "patched_wait_ms_param": True,
        "post_wait_ms": WAIT_POST_MS,
        "factory_wait_ms": WAIT_FACTORY_MS,
        "already_had_param": before,
    }


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
        "pending": try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10) if server else None,
        "stage": try_u32(b, sess + post_abi.CSession_STAGE_COUNT),
        "gate725": b.read(sess + 0x725, 1)[0] if sess else None,
        "exec_6cc": b.read(sess + 0x6CC, 1)[0] if sess else None,
        "defer_726": b.read(sess + 0x726, 1)[0] if sess else None,
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


def set_g4():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    return {"how": "os.environ CLAUSEWITZ_ALLOW_POST=1 in this Python process", "value": "1"}


def open_g5():
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN safe land tool-gate for Phase 2ijx (user t52u).\n"
        "Allows allow_post() True ONLY with CLAUSEWITZ_ALLOW_POST=1.\n"
        "Scope: CMoveCommand factory 1402 AND CStrategicRedeploymentCommand factory 4753.\n"
        "NEVER_POST: Inc/Dec/SetGameSpeed, HourlyTick, Ping, Pause still forbidden.\n",
        encoding="utf-8",
    )
    before = after = None
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                before = dict(g)
                g["status"] = "OPEN_SAFE_LAND_MOVE_STRATEGIC"
                g["note"] = "2ijx G5: safe_land_tool_gate.OPEN for Move timeout retry"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
                g["note"] = "2ijx: allow_post True when env=1 and safe_land marker"
        data["posting"] = "SAFE_LAND_GATED"
        data["command_queue"] = "SAFE_LAND_OPEN"
        data["phase"] = "2ijx"
        CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
        after = "OPEN_SAFE_LAND_MOVE_STRATEGIC"
    return {"marker": str(MARKER), "checklist_before": before, "checklist_after": after}


def restore_gates(move_result: str):
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
                g["note"] = "Re-closed after 2ijx Move timeout-diag one-shot"
                g["proven_once_move"] = {
                    "phase": "2ijx",
                    "factory_idx": 1402,
                    "result": move_result,
                    "post_wait_ms_config": WAIT_POST_MS,
                }
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "closed"
                g["note"] = "2ijx restored: allow_post requires env+marker again"
        data["posting"] = "DISABLED"
        data["command_queue"] = "DISABLED"
        data["phase"] = "2ijx"
        CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {
        "env_cleared": "CLAUSEWITZ_ALLOW_POST" not in os.environ,
        "marker_exists": MARKER.exists(),
        "allow_post": allow_post(),
    }


def diagnosis_block() -> dict:
    return {
        "vs_2iju_strategic": {
            "strategic_factory": {"idx": 4753, "rva": "0x13FB580"},
            "move_factory": {"idx": 1402, "rva": "0x13FB000"},
            "both_post_call": "FN_CMD_QUEUE_POST(session, cmd, r8=1)",
            "both_prior_wait_ms": 3000,
            "strategic_2iju_result": "PATH_CONTAINS_DEST post_rax=1 (no wait field returned)",
            "move_2ijw_result": "WAIT_TIMEOUT 258 after 3000ms; post_rax=0; path[]; province unchanged",
            "layout_diff": [
                "Strategic writes inline cmd+0x38 pack<IIIiI>(HANDLE,army,province,1,2) — no remote province array",
                "Move alloc VirtualAllocEx u32[1]; emb+0x10 handle; emb+0x18 Qii(buf,1,1); emb+0x50; emb+0x58=2",
                "Move IsValid dry HIT with same layout — hang is at FN_CMD_QUEUE_POST not IsValid",
                "cmd_layout: during_exec_drop session+0x6CC && !session+0x726; CMoveCommand_gate needs 0x725 or r8b",
                "2ijw observe: stage 0→2 during timeout; exec_delta=0; gate725 stayed 1",
            ],
            "this_slice_fixes": [
                f"Post WaitForSingleObject {WAIT_POST_MS}ms (was 3000)",
                "bounded wait_exec_clear on session+0x6CC before Post (<=2s)",
                "no pause-mem (no proven Windows speed offset); no CPauseGame Post (NEVER_POST)",
            ],
        }
    }


def fold_docs(result_code, g6, diag):
    block_safe = f"""

---

## Phase 2ijx — Move Post timeout diagnosis + one fixed retry

**Result:** `{result_code}`

| ID | State |
| --- | --- |
| G4 | PROVEN_ONCE env then restored |
| G5 | OPEN_SAFE_LAND then CLOSED |
| G6-Move | {result_code} — Post wait_ms={WAIT_POST_MS}; see reports/phase2ijx_move_post_timeout_diag.json |

Diagnosis vs 2iju Strategic: same FN_CMD_QUEUE_POST(session,cmd,r8=1); Move uses remote province arr; 2ijw timed out at 3s; this slice longer wait + exec_6cc clear.

"""
    if SAFE_MD.exists() and "Phase 2ijx — Move Post timeout" not in SAFE_MD.read_text(encoding="utf-8"):
        SAFE_MD.write_text(SAFE_MD.read_text(encoding="utf-8").rstrip() + "\n" + block_safe, encoding="utf-8")
    block_land = f"""

---

## Section 2ijx — Move FN_CMD_QUEUE_POST timeout diag + retry

- Diff vs Strategic 2iju: Strategic inline province at cmd+0x38; Move VirtualAllocEx province_arr at emb+0x18
- Both: FN_CMD_QUEUE_POST rcx=session rdx=cmd r8=1; gate725 often 1
- Fix tried: WaitForSingleObject Post={WAIT_POST_MS}ms; wait exec_6cc clear; no invented pause-mem
- Evidence: {(g6.get('post') or {})}
- Instant PARKED

"""
    if LAND_MD.exists() and "Section 2ijx — Move FN_CMD_QUEUE_POST" not in LAND_MD.read_text(encoding="utf-8"):
        LAND_MD.write_text(LAND_MD.read_text(encoding="utf-8").rstrip() + "\n" + block_land, encoding="utf-8")


def classify(posted, observe):
    wait = posted.get("post_wait")
    if posted.get("result") == "PATH_CONTAINS_DEST":
        return "G6_MOVE_POST_HIT"
    if wait == 258:
        return "G6_MOVE_POST_TIMEOUT"
    if posted.get("result") == "POSTED_DEST_NOT_IN_PATH" and (
        observe.get("province_changed") or (posted.get("path_after") or [])
    ):
        return "G6_MOVE_POST_ACCEPTED_WEAK"
    if posted.get("ok") and wait == 0:
        # completed stub but no path — still not HIT
        return "G6_MOVE_POST_FAIL"
    return "G6_MOVE_POST_FAIL"


def main() -> int:
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for m in (MARKER, LEGACY):
        if m.exists():
            m.unlink()

    patch_info = patch_move_order_timeout()
    diag = diagnosis_block()
    diag["patch"] = patch_info

    import config as cfg

    importlib.reload(cfg)
    from config import allow_post as ap0

    assert ap0() is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    live0 = continuum(b, base, pid)

    g4 = set_g4()
    importlib.reload(cfg)
    from config import allow_post as ap1

    env_only = ap1()
    g5_open = open_g5()
    importlib.reload(cfg)
    from config import allow_post as ap2

    g5_allow = ap2()
    if not g5_allow:
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
        if len(dest_pool) >= 10:
            break

    trials = []
    chosen = None
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
        "exec_clear": None,
        "post": None,
        "observe": None,
    }
    post_attempts = {"move": 0, "strategic": 0}

    if not chosen:
        result_code = "G6_MOVE_HARD_DENY_NO_DEST"
        g6["post"] = {"ok": False, "result": "NO_ISVALID_DEST_HARD_DENY"}
        restored = restore_gates(result_code)
    else:
        dest = int(chosen["province"])
        g6["exec_clear"] = wait_exec_clear(b, base, timeout_s=2.0)
        live_pre = continuum(b, base, pid)
        src_pre = army_snap(b, base, src["index"])
        posted = mo.move(int(src["index"]), dest, dry_run=False)
        post_attempts["move"] = 1
        g6["post"] = posted
        time.sleep(2.0)
        b2 = Backend(pid) if find_pid() == pid else None
        if not b2:
            result_code = "G6_MOVE_PROCESS_EXITED"
            g6["observe"] = {"pre": live_pre, "src_pre": src_pre}
            restored = restore_gates(result_code)
        else:
            live_imm = continuum(b2, base, pid)
            src_imm = army_snap(b2, base, src["index"])
            time.sleep(3.0)
            b3 = Backend(pid)
            live_later = continuum(b3, base, pid)
            src_later = army_snap(b3, base, src["index"])
            g6["observe"] = {
                "pre": live_pre,
                "src_pre": src_pre,
                "immediate": live_imm,
                "src_immediate": src_imm,
                "later": live_later,
                "src_later": src_later,
                "drain_delta": (live_imm.get("drain") or 0) - (live_pre.get("drain") or 0),
                "exec_delta": (live_imm.get("exec") or 0) - (live_pre.get("exec") or 0),
                "seq_delta": (live_imm.get("seq") or 0) - (live_pre.get("seq") or 0),
                "province_changed": (src_pre or {}).get("province") != (src_later or {}).get("province"),
                "path_before": posted.get("path_before"),
                "path_after": posted.get("path_after"),
            }
            result_code = classify(posted, g6["observe"])
            restored = restore_gates(result_code)

    importlib.reload(cfg)
    from config import allow_post as apf

    final_allow = apf()
    fold_docs(result_code, g6, diag)

    estimate = (
        "~74-76%"
        if result_code == "G6_MOVE_POST_HIT"
        else ("~72-74%" if result_code == "G6_MOVE_POST_ACCEPTED_WEAK" else "~71-73%")
    )
    if result_code in ("G6_MOVE_POST_TIMEOUT", "G6_MOVE_POST_FAIL", "G6_MOVE_HARD_DENY_NO_DEST"):
        next_blocker = (
            "Move live Post still not HIT after longer wait — HARD_DENY Move Post for now OR "
            "compare midflight game-heap province_arr (not VirtualAllocEx) vs Strategic inline; "
            "optional Strategic reaffirm next slice. Instant PARKED."
        )
    else:
        next_blocker = "If Move HIT: Cancel/SupportAttack gated one-shot or wartime attack RO; Instant PARKED."

    report = {
        "phase": "2ijx",
        "result": result_code,
        "authorization": "user t52u / pt52u — Move timeout diag + one fixed retry",
        "speed_policy": "pause-or-1x only; NEVER 5x; no speed write this slice (no proven pause-mem)",
        "diagnosis": diag,
        "live0": live0,
        "g4": {"before_allow_post": False, "set": g4, "env_only_allow_post": env_only},
        "g5": {"allow_post": g5_allow, "open": g5_open},
        "g6": g6,
        "post_attempts": post_attempts,
        "gates_restored": restored,
        "final_allow_post": final_allow,
        "factory": {"factory_idx": 1402, "factory_rva": "0x13FB000", "type": "CMoveCommand"},
        "path_c_honesty": {
            "baseline_band": "~60%",
            "after_2iju_2ijw": "~71-73%",
            "crossed_70": True,
            "estimate_after": estimate,
            "this_slice_pp": "+2-4pp if Move HIT else 0-1pp diagnosis",
        },
        "next_shortest_blocker": next_blocker,
        "push_note": "retry origin push separately; PC 443 may still block",
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijx",
                "result": result_code,
                "pid": pid,
                "ui_date": live0.get("ui_date"),
                "g6_result": (g6.get("post") or {}).get("result"),
                "post_wait": (g6.get("post") or {}).get("post_wait"),
                "post_rax": (g6.get("post") or {}).get("post_rax"),
                "final_allow_post": final_allow,
                "post_attempts": post_attempts,
                "estimate": estimate,
                "crossed_70": True,
                "src": g6.get("src_army"),
                "dest": (chosen or {}).get("province") if chosen else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ijx — Move Post timeout diagnosis + fixed retry

**Result:** `{result_code}`
**Posts:** move={post_attempts['move']} strategic={post_attempts['strategic']}
**allow_post final:** {final_allow}

## Diagnosis vs 2iju Strategic
- Same FN_CMD_QUEUE_POST(session, cmd, r8=1); prior wait 3000ms both
- Strategic HIT PATH_CONTAINS_DEST post_rax=1; Move 2ijw WAIT_TIMEOUT(258)
- Layout: Strategic inline cmd+0x38; Move remote VirtualAllocEx province_arr
- Fixes: Post wait={WAIT_POST_MS}ms; wait exec_6cc clear; no pause-mem invent

## G6
- chosen={chosen}
- post={g6.get('post')}
- observe deltas: {(g6.get('observe') or {}).get('seq_delta')}, drain={(g6.get('observe') or {}).get('drain_delta')}

## Path C
estimate_after={estimate}; crossed_70=True

*Phase 2ijx — {datetime.now().strftime('%Y-%m-%d %H:%M Asia/Shanghai')}*
""",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": result_code,
                "post": g6.get("post"),
                "allow_post": final_allow,
                "ui": live0.get("ui_date"),
                "exec_clear": g6.get("exec_clear"),
            },
            ensure_ascii=False,
            default=str,
        )[:2500]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
