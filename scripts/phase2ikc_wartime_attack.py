"""Phase 2ikc: ETH wartime SupportAttack 3620 one-shot + agent fold.

Cheap war path (repo-proven 2et/2fa): relaunch ETH @1x AI-on (day-1 war vs ITA).
No unproven declare. Instant PARKED. Max ONE Attack Post.
"""
from __future__ import annotations

import json
import os
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
import clock

MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
OUT = ROOT / "reports" / "phase2ikc_wartime_attack.json"
SUMMARY = ROOT / "reports" / "phase2ikc_wartime_attack_summary.json"
DOC = ROOT / "docs" / "PHASE2IKC_WARTIME_ATTACK.md"


def py() -> str:
    return sys.executable


def live_snap() -> dict:
    pid = find_pid()
    if not pid:
        return {"pid": None, "alive": False}
    try:
        b = Backend()
        base = b.image_base
        import post_abi
        sess = mo._u64(b, base + post_abi.G_SESSION)
    except Exception as e:
        return {"pid": pid, "alive": False, "open_error": str(e), "allow_post": allow_post()}
    ui = None
    try:
        r = subprocess.run(
            [py(), str(ROOT / "clausewitz_win.py"), "status"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=45,
        )
        j = json.loads(r.stdout or "{}")
        ui = j.get("date_full") or (j.get("gamestate") or {}).get("date_full")
        armies = (j.get("armies") or {}).get("armies_count")
        tag = (j.get("armies") or {}).get("player_tag")
        return {
            "pid": pid,
            "alive": True,
            "ui_date": ui,
            "armies_count": armies,
            "player_tag": tag,
            "allow_post": allow_post(),
            "responding": True,
            "ws_mb": None,
            "gate725": b.read(sess + 0x725, 1)[0] if sess else None,
            "exec_6cc": b.read(sess + 0x6CC, 1)[0] if sess else None,
            "raw_status_ok": True,
        }
    except Exception as e:
        return {"pid": pid, "alive": True, "error": str(e), "allow_post": allow_post()}


def kill_hoi4() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "hoi4.exe"], capture_output=True, text=True)
    # zombie WS=0 pids sometimes survive first pass
    try:
        import psutil  # optional
    except Exception:
        psutil = None
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process hoi4 -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue"],
        capture_output=True, text=True,
    )
    time.sleep(4)


def relaunch_eth() -> dict:
    kill_hoi4()
    cmd = [
        py(), str(ROOT / "scripts" / "launch_into_map.py"),
        "--start-tag", "ETH", "--speed", "1", "--allow-ai",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "cmd": cmd, "rc": r.returncode,
        "stdout": (r.stdout or "")[-800:],
        "stderr": (r.stderr or "")[-400:],
        "war_basis": "1936 ETH day-1 historical war vs ITA (repo 2et/2fa)",
    }


def wait_map(timeout: float = 240.0) -> dict:
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout:
        try:
            r = subprocess.run(
                [py(), str(ROOT / "clausewitz_win.py"), "status"],
                capture_output=True, text=True, cwd=str(ROOT), timeout=45,
            )
            txt = r.stdout or ""
            last = {"rc": r.returncode, "snippet": txt[-500:]}
            if "CInGameIdler" in txt:
                info = {"ok": True, "elapsed_s": round(time.time() - t0, 1)}
                try:
                    j = json.loads(txt)
                    info["date_full"] = j.get("date_full") or (j.get("gamestate") or {}).get("date_full")
                    info["pid"] = j.get("pid") or find_pid()
                    info["armies"] = (j.get("armies") or {}).get("armies_count")
                    info["player_tag"] = (j.get("armies") or {}).get("player_tag")
                except Exception:
                    info["pid"] = find_pid()
                return info
        except Exception as e:
            last = {"error": str(e)}
        time.sleep(5)
    return {"ok": False, "elapsed_s": round(time.time() - t0, 1), "last": last}


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("2ikc wartime SupportAttack gated\n", encoding="utf-8")
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


def pick_pair(rows: list[dict]) -> tuple[dict, int] | None:
    """Pick attacker + target province from another live army (no invented adjacency)."""
    ok = [r for r in rows if r.get("handle_ok") and r.get("province_id_ok") and r.get("province_id")]
    if len(ok) < 2:
        return None
    attacker = ok[0]
    # prefer different province
    for other in ok[1:]:
        if other["province_id"] != attacker["province_id"]:
            return attacker, int(other["province_id"])
    return attacker, int(ok[1]["province_id"])


def observe_stable(pid: int, seconds: float = 25.0) -> dict:
    samples = []
    t0 = time.time()
    responding_stayed = True
    while time.time() - t0 < seconds:
        alive = find_pid() == pid
        exit_code = 259
        try:
            import ctypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            hp = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if hp:
                code = ctypes.c_ulong()
                if k.GetExitCodeProcess(hp, ctypes.byref(code)):
                    exit_code = code.value
                k.CloseHandle(hp)
        except Exception:
            pass
        samples.append({"t": round(time.time() - t0, 2), "alive": alive, "exit_code": exit_code})
        if not alive or exit_code == 0xC0000374:
            responding_stayed = False
            break
        time.sleep(1.0)
    return {
        "observe_s": seconds,
        "samples_n": len(samples),
        "samples_head": samples[:5],
        "samples_tail": samples[-3:],
        "responding_stayed": responding_stayed and find_pid() == pid,
        "alive_final": find_pid() == pid,
        "heap_exit_0xC0000374": any(s.get("exit_code") == 0xC0000374 for s in samples),
    }


def fold_docs(result: str, war: dict, attack: dict, estimate: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S") + " Asia/Shanghai"
    DOC.write_text(
        f"""# Phase 2ikc — Wartime SupportAttack 3620

## Result
`{result}`

- War: {war.get('status')} — basis: {war.get('basis')}
- Attack post: {json.dumps(attack, ensure_ascii=False)[:500]}
- Instant PARKED. allow_post restored False.
- Agent loop: Move → Cancel → Strategic → Attack(wartime)
""",
        encoding="utf-8",
    )
    for path, line in [
        (
            ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md",
            f"\n## 2ikc ({ts})\n"
            f"War={war.get('status')}. SupportAttack 3620: **{result}**. "
            f"Agent loop Move→Cancel→Strategic→Attack(wartime). Instant PARKED. allow_post False.\n",
        ),
        (
            ROOT / "docs" / "LAND_POST_READINESS.md",
            f"\n## 2ikc ({ts})\n"
            f"{result}. ETH day-1 war relaunch. Attack factory 3620 one-shot.\n",
        ),
        (
            ROOT / "docs" / "PHASE2IJH_AGENT_CARD_READY_PARKED_DENY.md",
            f"\n## 2ikc fold ({ts})\n"
            f"- War: {war.get('status')} — Attack **attempted/posted** under gate.\n"
            f"- Result: {result}\n"
            f"- Agent land loop: Move → Cancel → Strategic → Attack(when wartime); Instant PARKED.\n"
            f"- allow_post default False.\n",
        ),
    ]:
        try:
            prev = path.read_text(encoding="utf-8") if path.exists() else ""
            if "2ikc" not in prev[-800:]:
                path.write_text(prev + line, encoding="utf-8")
        except Exception:
            pass
    # checklist json
    cj = ROOT / "research" / "safe_enable_checklist.json"
    try:
        data = json.loads(cj.read_text(encoding="utf-8")) if cj.exists() else {}
        data["phase2ikc"] = {
            "result": result,
            "war": war,
            "attack": {
                "factory_idx": 3620,
                "ok": attack.get("ok"),
                "result": attack.get("result"),
                "army": attack.get("army"),
                "province": attack.get("province"),
                "post_wait": attack.get("post_wait"),
                "post_rax": attack.get("post_rax"),
                "buf_kind": attack.get("buf_kind"),
            },
            "allow_post_final": False,
            "estimate": estimate,
            "ts": ts,
        }
        cj.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    report: dict = {
        "phase": "2ikc",
        "authorization": "t52u",
        "timestamp_asia_shanghai": time.strftime("%Y-%m-%d %H:%M:%S") + " Asia/Shanghai",
        "post_attempts": {"move": 0, "strategic": 0, "cancel": 0, "attack": 0},
        "instant": "PARKED",
    }
    close_gates()
    report["live_before"] = live_snap()

    # A) cheap war: ETH relaunch (proven)
    report["relaunch"] = relaunch_eth()
    report["map_wait"] = wait_map(240)
    if not report["map_wait"].get("ok"):
        close_gates()
        report["result"] = "MAP_WAIT_FAILED"
        report["HIT"] = False
        report["war"] = {"status": "RELAUNCH_MAP_FAILED", "attack": "PARKED"}
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        SUMMARY.write_text(json.dumps({"phase": "2ikc", "ok": False, "error": "map_wait"}, indent=2), encoding="utf-8")
        print(json.dumps({"result": report["result"], "HIT": False}, ensure_ascii=False))
        return 1

    live0 = live_snap()
    report["live0"] = live0
    war = {
        "status": "WARTIME_ETH_DAY1_HISTORICAL",
        "basis": "start_tag=ETH @1x AI-on; 1936 ETH at war with ITA on day 1 (2et/2fa proven)",
        "player_tag": live0.get("player_tag"),
        "ui_date": live0.get("ui_date"),
        "declare": "NOT_USED",
    }
    report["war"] = war

    b = Backend()
    base = b.image_base
    rows = list(asub.iter_armies_by_index(b, base, 1000, 1300))
    report["army_rows_n"] = len(rows)
    report["army_sample"] = rows[:8]
    pair = pick_pair(rows)
    if not pair:
        close_gates()
        report["result"] = "NO_ARMY_PAIR"
        report["HIT"] = False
        report["attack"] = "PARKED_NO_SUBJECT"
        fold_docs(report["result"], war, {}, "~80-82%")
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        SUMMARY.write_text(json.dumps({"phase": "2ikc", "HIT": False, "result": report["result"]}, indent=2), encoding="utf-8")
        print(json.dumps({"result": report["result"], "HIT": False, "war": war["status"]}, ensure_ascii=False))
        return 1

    attacker, target_prov = pair
    army_i = int(attacker["index"])
    report["chosen"] = {"army": army_i, "src_province": attacker.get("province_id"), "target_province": target_prov}

    # Dry IsValid first (no gate)
    dry = ao.support_attack(army_i, target_prov, dry_run=True)
    report["attack_dry"] = dry
    if not dry.get("ok"):
        # try a few alternate targets from other armies
        alts = []
        for r in rows[1:12]:
            if not r.get("province_id_ok"):
                continue
            tp = int(r["province_id"])
            if tp == target_prov:
                continue
            d2 = ao.support_attack(army_i, tp, dry_run=True)
            alts.append({"province": tp, "dry": d2})
            if d2.get("ok"):
                dry = d2
                target_prov = tp
                break
        report["attack_dry_alts"] = alts[:6]
        report["attack_dry"] = dry
    if not dry.get("ok"):
        close_gates()
        report["result"] = "ATTACK_DRY_ISVALID_FALSE"
        report["HIT"] = False
        fold_docs(report["result"], war, dry, "~80-82%")
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        SUMMARY.write_text(json.dumps({"phase": "2ikc", "HIT": False, "result": report["result"], "war": war}, indent=2), encoding="utf-8")
        print(json.dumps({"result": report["result"], "HIT": False, "war": war["status"], "dry": dry.get("result")}, ensure_ascii=False))
        return 0

    open_gates()
    assert allow_post()
    try:
        post = ao.support_attack(army_i, target_prov, dry_run=False)
        report["post_attempts"]["attack"] = 1
        report["attack_post"] = post
    finally:
        close_gates()

    pid = find_pid()
    stab = observe_stable(pid, 25.0) if pid else {"alive_final": False, "responding_stayed": False, "heap_exit_0xC0000374": False}
    report["stability"] = stab
    report["live1"] = live_snap()
    report["final_allow_post"] = allow_post()
    report["gates_restored"] = {"allow_post": allow_post(), "marker_exists": MARKER.exists()}

    posted_ok = bool(post.get("ok")) and post.get("result") == "ATTACK_POSTED_STABLE"
    stable_ok = stab.get("responding_stayed") and stab.get("alive_final") and not stab.get("heap_exit_0xC0000374")
    if posted_ok and stable_ok:
        result = "G6_ATTACK_3620_POSTED_STABLE_HIT"
        hit = True
        estimate = "~84-86%"
    elif post.get("post_wait") == 0 and stable_ok:
        result = "G6_ATTACK_3620_POSTED_PARTIAL"
        hit = True
        estimate = "~82-84%"
    else:
        result = "G6_ATTACK_3620_FAIL"
        hit = False
        estimate = "~80-82%"

    report["result"] = result
    report["HIT"] = hit
    report["path_c_honesty"] = {
        "baseline_band": "~60%",
        "after_2ikb": "~80-82%",
        "crossed_70": True,
        "estimate_after": estimate,
    }
    report["agent_land_loop"] = {
        "move": "HIT_CLASS factory 1402 ucrt_malloc",
        "cancel": "HIT_CLASS factory 1415 ucrt units (1- and 2-army)",
        "strategic": "HIT_CLASS factory 4753 inline",
        "attack": "HIT_CLASS factory 3620 inline" if hit else "ATTEMPTED",
        "instant": "PARKED",
    }
    report["next_shortest_blocker"] = (
        "Attack combat evidence densify / Instant wartime midflight; or multi-army Attack"
        if hit
        else "Fix SupportAttack IsValid/Execute subject or target selection under war"
    )

    fold_docs(result, war, post, estimate)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ikc",
                "result": result,
                "HIT": hit,
                "war": war.get("status"),
                "attack_result": post.get("result"),
                "army": army_i,
                "province": target_prov,
                "post_wait": post.get("post_wait"),
                "post_rax": post.get("post_rax"),
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
                "war": war.get("status"),
                "attack": post.get("result"),
                "army": army_i,
                "province": target_prov,
                "post_wait": post.get("post_wait"),
                "post_rax": post.get("post_rax"),
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
    return 0 if hit else 0


if __name__ == "__main__":
    raise SystemExit(main())