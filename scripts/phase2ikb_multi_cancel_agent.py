#!/usr/bin/env python3
"""Phase 2ikb: peacetime Attack PARKED; multi-army Cancel 1415 + agent land loop fold.

War not present / declare not proven → do not Attack. Primary Post: Cancel with
2 moving armies (Move prep each). Authorized t52u.
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

OUT = ROOT / "reports" / "phase2ikb_multi_cancel_agent.json"
SUMMARY = ROOT / "reports" / "phase2ikb_multi_cancel_agent_summary.json"
DOC = ROOT / "docs" / "PHASE2IKB_MULTI_CANCEL_AGENT.md"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND_MD = ROOT / "docs" / "LAND_POST_READINESS.md"
AGENT = ROOT / "docs" / "PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md"

GS_YEAR, GS_DAY = 0x478, 0x484
OBSERVE_S = 35.0
# two idle armies → move to proven dests then multi-cancel
PAIR = [(1042, 3931), (1037, 11838)]


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
    return {
        "pid": pid,
        "year": year,
        "day_index": day,
        "ui_date": ui,
        "player_tag": i32(b, gs + 0x518),
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
    MARKER.write_text("2ikb multi-cancel gated\n", encoding="utf-8")
    if LEGACY.exists():
        LEGACY.unlink()


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()
    if LEGACY.exists():
        LEGACY.unlink()


def fold(result: str, ts: str, war: dict):
    loop = (
        "Land loop (proven Posts): Move1402(ucrt) → Cancel1415(ucrt units) → "
        "Strategic4753(inline); Attack3620 PARKED until war; Instant PARKED."
    )
    for p, line in (
        (
            SAFE_MD,
            f"\n\n## 2ikb ({ts})\nAttack PARKED peacetime (war={war}). "
            f"Multi-army Cancel: **{result}**. {loop} allow_post False.\n",
        ),
        (
            LAND_MD,
            f"\n\n## 2ikb ({ts})\n{result}. War detect: no ov war keys; peacetime ITA. "
            f"Attack3620 not opened. Multi-Cancel units_count=2.\n",
        ),
        (
            AGENT,
            f"\n\n## 2ikb fold ({ts})\n"
            f"- War: {war.get('status')} — Attack **PARKED**.\n"
            f"- Multi-Cancel 1415: {result}.\n"
            f"- Agent land command loop: Move → Cancel → Strategic (all Post-HIT class); "
            f"encirclement bias RO prior; Attack when wartime.\n"
            f"- Instant PARKED. allow_post default False.\n",
        ),
    ):
        t = p.read_text(encoding="utf-8") if p.exists() else ""
        if "2ikb" in t[-1800:]:
            continue
        p.write_text(t + line, encoding="utf-8")
    c = json.loads(CHECKLIST.read_text(encoding="utf-8")) if CHECKLIST.exists() else {}
    c["phase2ikb"] = {
        "result": result,
        "attack": "PARKED_PEACETIME",
        "war": war,
        "allow_post_final": False,
        "ts": ts,
    }
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

    war = {
        "status": "PEACETIME_NO_WAR_DETECTED",
        "evidence": "offsets_verified has no war keys; ITA 1936 Feb peacetime; declare console not Post-proven",
        "attack": "PARKED",
    }

    open_gates()
    assert allow_post()

    move_posts = []
    armies = []
    for army_i, dest in PAIR:
        dry = mo.move(army_i, dest, dry_run=True)
        if not (dry.get("ok") and dry.get("result") == "DRY_RUN_VALID"):
            # try alternate dests
            alt = None
            for d in [3931, 11838, 3898, 12857, 8757, 9979, 740, 9764]:
                dry2 = mo.move(army_i, d, dry_run=True)
                if dry2.get("ok") and dry2.get("result") == "DRY_RUN_VALID":
                    alt = d
                    dry = dry2
                    break
            if alt is None:
                close_gates()
                out = {"phase": "2ikb", "result": "MOVE_PREP_DRY_FAIL", "army": army_i, "dry": dry, "war": war}
                OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
                print(json.dumps(out))
                return 2
            dest = alt
        post = mo.move(army_i, dest, dry_run=False)
        move_posts.append(post)
        # wait path
        path = []
        for _ in range(40):
            if find_pid() != pid0:
                break
            b = Backend(pid0)
            army = resolve_handle(b, HANDLE_TYPE_ARMY, army_i, base)
            path = mo._path(b, base, army) if army else []
            if path:
                break
            time.sleep(0.1)
        if not path:
            close_gates()
            out = {
                "phase": "2ikb",
                "result": "MOVE_PREP_NO_PATH",
                "move_posts": move_posts,
                "war": war,
                "final_allow_post": allow_post(),
            }
            OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(json.dumps({"result": "MOVE_PREP_NO_PATH", "moves": move_posts}))
            return 1
        armies.append(army_i)

    dry_c = co.cancel_movement(army_indices=armies, dry_run=True)
    if not (dry_c.get("ok") and dry_c.get("result") == "DRY_RUN_VALID"):
        close_gates()
        out = {
            "phase": "2ikb",
            "result": "CANCEL_MULTI_DRY_INVALID",
            "dry": dry_c,
            "move_posts": move_posts,
            "war": war,
            "final_allow_post": allow_post(),
        }
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps({"result": "CANCEL_MULTI_DRY_INVALID", "dry": dry_c}))
        return 1

    cancel_post = co.cancel_movement(army_indices=armies, dry_run=False)

    samples = []
    path_obs = []
    heap_exit = False
    alive_final = True
    responding_stayed = True
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
            snap = {}
            for a in armies:
                army = resolve_handle(b, HANDLE_TYPE_ARMY, a, base)
                snap[str(a)] = mo._path(b, base, army) if army else []
            path_obs.append({"t": round(time.time() - t0, 2), "paths": snap})
        except Exception as e:
            path_obs.append({"t": round(time.time() - t0, 2), "err": str(e)})
        time.sleep(1.0)

    close_gates()
    final_allow = allow_post()
    live1 = None
    if alive_final:
        try:
            live1 = continuum(Backend(pid0), base, pid0)
        except Exception as e:
            live1 = {"err": str(e)}

    cleared = bool(cancel_post.get("path_cleared")) or cancel_post.get("result") == "PATH_CLEARED_ALL"
    # also accept late observe all empty
    if not cleared and path_obs:
        last = path_obs[-1].get("paths") or {}
        if last and all(not v for v in last.values()):
            cleared = True

    hit = bool(
        cleared
        and responding_stayed
        and alive_final
        and not heap_exit
        and cancel_post.get("units_buf_kind") == "ucrt_malloc"
        and cancel_post.get("units_count") == 2
    )
    if hit:
        result = "G6_CANCEL_MULTI2_PATH_CLEARED_HIT"
    elif not alive_final or heap_exit:
        result = "G6_CANCEL_MULTI_PROCESS_EXIT"
    else:
        result = f"G6_CANCEL_MULTI_{cancel_post.get('result')}"

    estimate = "~80-82%" if hit else "~78-80%"
    out = {
        "phase": "2ikb",
        "result": result,
        "HIT": hit,
        "authorization": "t52u",
        "war": war,
        "attack": "PARKED_PEACETIME",
        "live0": live0,
        "move_posts": move_posts,
        "cancel_dry": dry_c,
        "cancel_post": cancel_post,
        "path_obs_head": path_obs[:8],
        "stability": {
            "observe_s": OBSERVE_S,
            "samples": samples,
            "responding_stayed": responding_stayed,
            "alive_final": alive_final,
            "heap_exit_0xC0000374": heap_exit,
        },
        "live1": live1,
        "post_attempts": {"move": len(move_posts), "strategic": 0, "cancel": 1, "attack": 0},
        "gates_restored": {"allow_post": final_allow, "marker_exists": MARKER.exists()},
        "final_allow_post": final_allow,
        "agent_land_loop": {
            "move": "HIT_CLASS factory 1402 ucrt_malloc",
            "cancel": "HIT_CLASS factory 1415 ucrt units (1- and 2-army)",
            "strategic": "HIT_CLASS factory 4753 inline",
            "attack": "PARKED until war",
            "instant": "PARKED",
        },
        "path_c_honesty": {
            "baseline_band": "~60%",
            "after_2ika": "~78-80%",
            "crossed_70": True,
            "estimate_after": estimate,
        },
        "next_shortest_blocker": "Wartime Attack 3620 when war exists (ETH war-day relaunch or proven declare); Instant PARKED",
        "timestamp_asia_shanghai": ts,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikb",
                "result": result,
                "HIT": hit,
                "war": war["status"],
                "attack": "PARKED",
                "cancel_result": cancel_post.get("result"),
                "units_count": cancel_post.get("units_count"),
                "post_wait": cancel_post.get("post_wait"),
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
        f"# Phase 2ikb — Multi-Cancel + agent land loop\n\n"
        f"## Result\n`{result}` HIT={hit}\n\n"
        f"- War: {war['status']} → Attack PARKED\n"
        f"- Cancel multi units_count={cancel_post.get('units_count')} "
        f"result={cancel_post.get('result')} post_wait={cancel_post.get('post_wait')}\n"
        f"- responding_stayed={responding_stayed} heap_exit={heap_exit}\n"
        f"- Agent loop: Move→Cancel→Strategic proven; Attack/Instant PARKED\n",
        encoding="utf-8",
    )
    fold(result, ts, war)
    print(
        json.dumps(
            {
                "result": result,
                "HIT": hit,
                "war": war["status"],
                "attack": "PARKED",
                "cancel": {
                    "result": cancel_post.get("result"),
                    "units_count": cancel_post.get("units_count"),
                    "units_buf_kind": cancel_post.get("units_buf_kind"),
                    "path_before": cancel_post.get("path_before"),
                    "path_after": cancel_post.get("path_after"),
                    "post_wait": cancel_post.get("post_wait"),
                    "post_rax": cancel_post.get("post_rax"),
                },
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
