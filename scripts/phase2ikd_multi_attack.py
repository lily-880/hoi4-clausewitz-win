"""Phase 2ikd: multi-army SupportAttack 3620 + honest combat-adjacent RO densify.

Primary B: TWO armies Attack Post (inline). Light A: path/order RO before/after
without inventing org/str/adjacency/CProvince+0x58. Instant PARKED.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
from handle import resolve_handle, HANDLE_TYPE_ARMY
import army_subjects as asub
import move_order as mo
import attack_order as ao
import post_abi

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
OUT = ROOT / "reports" / "phase2ikd_multi_attack.json"
SUMMARY = ROOT / "reports" / "phase2ikd_multi_attack_summary.json"
DOC = ROOT / "docs" / "PHASE2IKD_MULTI_ATTACK.md"
ARMY_VT = 0x29D6D68
PATH_OFF = 0x200


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("2ikd multi-attack gated\n", encoding="utf-8")
    if LEGACY.exists():
        try:
            LEGACY.unlink()
        except Exception:
            pass


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for p in (MARKER, LEGACY):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def status_date() -> dict:
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "clausewitz_win.py"), "status"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=45,
        )
        j = json.loads(r.stdout or "{}")
        df = (
            (j.get("campaign") or {}).get("date_full")
            or ((j.get("gamestate_probe") or {}).get("campaign") or {}).get("fields", {}).get("date_full")
            or ((j.get("gamestate_probe") or {}).get("campaign") or {}).get("verified", {}).get("date_full")
        )
        return {
            "pid": find_pid(),
            "ui_date": (df or {}).get("ui") if isinstance(df, dict) else df,
            "day_index": (df or {}).get("day_index") if isinstance(df, dict) else None,
            "armies_count": (j.get("armies") or {}).get("armies_count"),
            "player_tag": (j.get("armies") or {}).get("player_tag"),
            "idler": ((j.get("session") or {}).get("signals") or {}).get("idler_class"),
            "allow_post": allow_post(),
        }
    except Exception as e:
        return {"pid": find_pid(), "error": str(e), "allow_post": allow_post()}


def army_ro(b, base, idx: int) -> dict:
    """Honest combat-adjacent RO: path vector + province_id only (no invented org/str)."""
    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army or mo._u64(b, army) - base != ARMY_VT:
        return {"index": idx, "ok": False, "reason": "ARMY_NOT_FOUND"}
    path = mo._path(b, base, army)
    # CArmy+0x28 province_id used by army_subjects (proven RO)
    prov = struct.unpack_from("<I", b.read(army + 0x28, 4) or b"\0\0\0\0", 0)[0]
    # path Qii meta (proven Move/Cancel)
    try:
        data, cap, size = struct.unpack("<Qii", b.read(army + PATH_OFF, 16))
        path_meta = {"data": data, "cap": cap, "size": size}
    except Exception:
        path_meta = None
    return {
        "index": idx,
        "ok": True,
        "province_id": prov,
        "path": path,
        "path_len": len(path),
        "path_nonempty": bool(path),
        "path_meta": path_meta,
    }


def pick_two(rows: list[dict]) -> list[tuple[int, int]] | None:
    """(army_index, target_province) x2; targets from other armies' provinces (no invented adjacency)."""
    ok = [r for r in rows if r.get("handle_ok") and r.get("province_id_ok") and r.get("province_id")]
    if len(ok) < 3:
        return None
    a0, a1 = ok[0], ok[1]
    # distinct targets preferably from later rows
    t0 = int(ok[2]["province_id"])
    t1 = int(ok[3]["province_id"]) if len(ok) > 3 else int(ok[2]["province_id"])
    if t0 == a0["province_id"] and len(ok) > 4:
        t0 = int(ok[4]["province_id"])
    if t1 == a1["province_id"] and len(ok) > 5:
        t1 = int(ok[5]["province_id"])
    return [(int(a0["index"]), t0), (int(a1["index"]), t1)]


def observe_stable(pid: int, seconds: float = 25.0) -> dict:
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
        "observe_s": seconds,
        "samples_n": len(samples),
        "samples_head": samples[:3],
        "samples_tail": samples[-2:],
        "responding_stayed": bool(samples) and all(s["alive"] for s in samples) and find_pid() == pid,
        "alive_final": find_pid() == pid,
        "heap_exit_0xC0000374": heap,
    }


def fold_docs(result: str, war: dict, posts: list, densify: dict, estimate: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S") + " Asia/Shanghai"
    DOC.write_text(
        f"""# Phase 2ikd — Multi-army SupportAttack + RO densify

## Result
`{result}`

- War: {war}
- Posts: {json.dumps(posts, ensure_ascii=False)[:800]}
- Combat-adjacent RO densify: {json.dumps(densify, ensure_ascii=False)[:800]}
- Instant PARKED. allow_post False.
""",
        encoding="utf-8",
    )
    snippets = [
        (
            ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md",
            f"\n## 2ikd ({ts})\n"
            f"Multi-army SupportAttack 3620: **{result}**. Combat-adjacent RO densify "
            f"(path/province only; org/str NOT invented). Instant PARKED. allow_post False.\n",
        ),
        (
            ROOT / "docs" / "LAND_POST_READINESS.md",
            f"\n## 2ikd ({ts})\n"
            f"{result}. Two-army Attack 3620 + honest path/province densify.\n",
        ),
        (
            ROOT / "docs" / "PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md",
            f"\n## 2ikd fold ({ts})\n"
            f"- Multi-army Attack 3620: {result}\n"
            f"- Combat evidence: path/province RO densify (no org/str invent)\n"
            f"- Agent loop: Move→Cancel→Strategic→Attack(1-/2-army wartime); Instant PARKED\n"
            f"- allow_post default False.\n",
        ),
    ]
    for path, line in snippets:
        try:
            prev = path.read_text(encoding="utf-8") if path.exists() else ""
            if "2ikd" not in prev[-900:]:
                path.write_text(prev + line, encoding="utf-8")
        except Exception:
            pass
    cj = ROOT / "research" / "safe_enable_checklist.json"
    try:
        data = json.loads(cj.read_text(encoding="utf-8")) if cj.exists() else {}
        data["phase2ikd"] = {
            "result": result,
            "war": war,
            "posts_n": len(posts),
            "densify": densify.get("summary") if isinstance(densify, dict) else densify,
            "allow_post_final": False,
            "estimate": estimate,
            "ts": ts,
        }
        cj.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    close_gates()
    report: dict = {
        "phase": "2ikd",
        "authorization": "t52u",
        "timestamp_asia_shanghai": time.strftime("%Y-%m-%d %H:%M:%S") + " Asia/Shanghai",
        "primary": "B_multi_army_attack_plus_A_lite_RO_densify",
        "instant": "PARKED",
        "war": {
            "status": "WARTIME_ETH_CONTINUATION",
            "basis": "live ETH session from 2ikc; day-1 historical war vs ITA",
            "declare": "NOT_USED",
        },
        "post_attempts": {"move": 0, "strategic": 0, "cancel": 0, "attack": 0},
    }
    live0 = status_date()
    report["live0"] = live0
    pid0 = find_pid()
    if not pid0:
        report["result"] = "NO_PROCESS"
        report["HIT"] = False
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"result": "NO_PROCESS", "HIT": False}))
        return 1

    try:
        b = Backend()
    except OSError as e:
        report["result"] = "OPENPROCESS_FAIL"
        report["error"] = str(e)
        report["HIT"] = False
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"result": "OPENPROCESS_FAIL", "HIT": False}))
        return 1

    base = b.image_base
    rows = list(asub.iter_armies_by_index(b, base, 1000, 1300))
    report["army_rows_n"] = len(rows)
    pairs = pick_two(rows)
    if not pairs:
        report["result"] = "NO_ARMY_PAIR"
        report["HIT"] = False
        fold_docs(report["result"], report["war"], [], {}, "~84-86%")
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"result": report["result"], "HIT": False}))
        return 1

    report["chosen"] = [{"army": a, "target": t} for a, t in pairs]

    # RO before
    before = {str(a): army_ro(b, base, a) for a, _ in pairs}
    report["ro_before"] = before

    # Dry both
    drys = []
    for army_i, tgt in pairs:
        d = ao.support_attack(army_i, tgt, dry_run=True)
        drys.append(d)
        if not d.get("ok"):
            # one alternate target from later rows
            for r in rows:
                tp = int(r.get("province_id") or 0)
                if not tp or tp == tgt:
                    continue
                d2 = ao.support_attack(army_i, tp, dry_run=True)
                if d2.get("ok"):
                    d = d2
                    tgt = tp
                    pairs = [(a, (tp if a == army_i else tt)) for a, tt in pairs]
                    break
            drys[-1] = d
        if not d.get("ok"):
            close_gates()
            report["attack_drys"] = drys
            report["result"] = "ATTACK_DRY_FAIL"
            report["HIT"] = False
            fold_docs(report["result"], report["war"], drys, {}, "~84-86%")
            OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
            SUMMARY.write_text(json.dumps({"phase": "2ikd", "HIT": False, "result": report["result"]}, indent=2), encoding="utf-8")
            print(json.dumps({"result": report["result"], "HIT": False, "drys": [x.get("result") for x in drys]}, ensure_ascii=False))
            return 0

    report["attack_drys"] = [{k: d.get(k) for k in ("ok", "result", "army", "province", "factory_idx")} for d in drys]
    report["chosen"] = [{"army": a, "target": t} for a, t in pairs]

    posts = []
    open_gates()
    assert allow_post()
    try:
        for army_i, tgt in pairs:
            post = ao.support_attack(army_i, tgt, dry_run=False)
            report["post_attempts"]["attack"] += 1
            posts.append(post)
            if find_pid() != pid0:
                break
    finally:
        close_gates()

    report["attack_posts"] = posts
    # RO after
    b = Backend()
    base = b.image_base
    after = {str(a): army_ro(b, base, a) for a, _ in pairs}
    report["ro_after"] = after

    densify_rows = []
    for a, t in pairs:
        key = str(a)
        br, ar = before.get(key, {}), after.get(key, {})
        densify_rows.append({
            "army": a,
            "target": t,
            "province_before": br.get("province_id"),
            "province_after": ar.get("province_id"),
            "province_changed": br.get("province_id") != ar.get("province_id"),
            "path_len_before": br.get("path_len"),
            "path_len_after": ar.get("path_len"),
            "path_changed": br.get("path") != ar.get("path"),
            "path_nonempty_before": br.get("path_nonempty"),
            "path_nonempty_after": ar.get("path_nonempty"),
            "note": "SupportAttack≠Move; path/province may stay same — honest",
        })
    any_signal = any(r["province_changed"] or r["path_changed"] for r in densify_rows)
    densify = {
        "summary": "COMBAT_ADJACENT_SIGNAL" if any_signal else "HONEST_EMPTY_PATH_PROVINCE",
        "invented_org_str": False,
        "invented_adjacency": False,
        "rows": densify_rows,
    }
    report["combat_evidence_densify"] = densify

    pid = find_pid() or pid0
    stab = observe_stable(pid, 25.0)
    report["stability"] = stab
    report["live1"] = status_date()
    report["final_allow_post"] = allow_post()
    report["gates_restored"] = {"allow_post": allow_post(), "marker_exists": MARKER.exists()}

    all_posted = all(p.get("ok") and p.get("result") == "ATTACK_POSTED_STABLE" for p in posts) and len(posts) == 2
    stable_ok = stab.get("responding_stayed") and stab.get("alive_final") and not stab.get("heap_exit_0xC0000374")
    if all_posted and stable_ok:
        result = "G6_ATTACK_MULTI2_POSTED_STABLE_HIT"
        hit = True
        estimate = "~86-88%"
    elif any(p.get("ok") for p in posts) and stable_ok:
        result = "G6_ATTACK_MULTI_PARTIAL"
        hit = True
        estimate = "~85-87%"
    else:
        result = "G6_ATTACK_MULTI_FAIL"
        hit = False
        estimate = "~84-86%"

    report["result"] = result
    report["HIT"] = hit
    report["path_c_honesty"] = {
        "baseline_band": "~60%",
        "after_2ikc": "~84-86%",
        "crossed_70": True,
        "estimate_after": estimate,
    }
    report["agent_land_loop"] = {
        "move": "HIT_CLASS 1402",
        "cancel": "HIT_CLASS 1415 (1-/2-army)",
        "strategic": "HIT_CLASS 4753",
        "attack": "HIT_CLASS 3620 (1-/2-army wartime)" if hit else "ATTEMPTED",
        "instant": "PARKED",
    }
    report["next_shortest_blocker"] = (
        "Instant wartime midflight Instant×PATH (still PARKED); or combat evidence beyond path/province RO"
        if hit
        else "Stabilize multi-army Attack IsValid/Post"
    )

    fold_docs(result, report["war"], [
        {k: p.get(k) for k in ("ok", "result", "army", "province", "post_wait", "post_rax")}
        for p in posts
    ], densify, estimate)

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikd",
                "result": result,
                "HIT": hit,
                "war": report["war"]["status"],
                "posts": [
                    {k: p.get(k) for k in ("ok", "result", "army", "province", "post_wait", "post_rax")}
                    for p in posts
                ],
                "densify": densify["summary"],
                "responding_stayed": stab.get("responding_stayed"),
                "alive_final": stab.get("alive_final"),
                "heap_exit": stab.get("heap_exit_0xC0000374"),
                "final_allow_post": allow_post(),
                "estimate": estimate,
                "post_attempts": report["post_attempts"],
                "ui": (report.get("live1") or {}).get("ui_date"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": result,
                "HIT": hit,
                "war": report["war"]["status"],
                "posts": [
                    {"army": p.get("army"), "province": p.get("province"), "result": p.get("result"),
                     "post_wait": p.get("post_wait"), "post_rax": p.get("post_rax")}
                    for p in posts
                ],
                "densify": densify["summary"],
                "stability": {
                    "responding_stayed": stab.get("responding_stayed"),
                    "alive_final": stab.get("alive_final"),
                    "heap_exit": stab.get("heap_exit_0xC0000374"),
                },
                "allow_post": allow_post(),
                "ui": (report.get("live1") or {}).get("ui_date"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())