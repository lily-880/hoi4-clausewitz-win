#!/usr/bin/env python3
"""Run commander ticks until the stage goal is met (or a stop condition).

  python -I scripts/commander_loop.py --decider decide_llm --hours 12 --max-ticks 200

Stage goal (records/claude_c05): Poland stops resisting. Detected when the
target controls no provinces any more, or is no longer at war with us. The
first game date this is observed is the score.

Safety:
  * every tick ends paused (live_trial.tick -> run_hours finally);
  * a separate watchdog process presses pause if the game stays unpaused for
    more than WATCHDOG_S seconds (covers this process dying mid-run); it exits
    once this loop is gone and the game is paused;
  * create research/claude_live/STOP to end the loop after the current tick.

Progress: research/claude_live/loop_progress.jsonl (one line per tick) and
research/claude_live/loop_status.json (latest; read by humans and resumes).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))

OUT = ROOT / "research" / "claude_live"
PROGRESS = OUT / "loop_progress.jsonl"
STATUS = OUT / "loop_status.json"
STOP = OUT / "STOP"
WATCHDOG_S = 240


def watchdog(parent_pid: int) -> int:
    import live_trial as lt

    unpaused_since = None
    while True:
        try:
            parent_alive = lt.process_health(parent_pid)["alive"]
            clk = lt.Session(check_sha=False).clock()
        except SystemExit:
            return 0  # game gone
        except Exception:
            time.sleep(5)
            continue
        if clk["pause"] == 0:
            unpaused_since = unpaused_since or time.time()
            if time.time() - unpaused_since > WATCHDOG_S:
                lt.set_clock(False)
                with (OUT / "watchdog.log").open("a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} paused game left running "
                            f"(unpaused > {WATCHDOG_S}s) at {clk}\n")
                unpaused_since = None
        else:
            unpaused_since = None
            if not parent_alive:
                return 0
        time.sleep(5)


KEY_MOMENTS = OUT / "key_moments.jsonl"


def key_moments(prev: dict | None, ext: dict, targets: set[str]) -> list[dict]:
    """Typical turning points worth saving as practice starts.
    prev/ext: commander_ext of the previous and current tick."""
    if not ext:
        return []
    top = ext.get("topology") or {}
    out = []
    ptop = (prev or {}).get("topology") or {}
    prev_pockets = {tuple(x["sample"][:3]) for x in ptop.get("enemy_pockets", [])}
    for pk in top.get("enemy_pockets", []):
        if pk["owner"] in targets and tuple(pk["sample"][:3]) not in prev_pockets:
            out.append({"kind": "包围圈形成", "detail": f"{pk['owner']} 有 {pk['provinces']} 个省被我方切断（例如 {pk['sample'][:4]}）"})
    pn = {x["province_id"] for x in ptop.get("near_closed", [])}
    new_close = [x for x in top.get("near_closed", []) if x["owner"] in targets and x["province_id"] not in pn]
    if len(new_close) >= 2:
        out.append({"kind": "口袋即将合拢", "detail": "敌方省份大部分邻省已在我方手中：" +
                    "、".join(f"{x['province_id']}({x['ours']}/{x['neighbors']})" for x in new_close[:6])})
    if prev:
        for tag in targets:
            a_ = (prev.get("enemy_controlled_provinces") or {}).get(tag)
            b_ = (ext.get("enemy_controlled_provinces") or {}).get(tag)
            if a_ and b_ is not None and a_ - b_ >= 4 and b_ > 0:
                out.append({"kind": "敌方前线被撕开", "detail": f"{tag} 一拍丢失 {a_ - b_} 个省（{a_}→{b_}）"})
        def best(tp):
            kt = [k for k in tp.get("key_targets", []) if k["owner"] in targets]
            return min((k["hops_from_our_land"] for k in kt if k["victory_points"] >= 20), default=None)
        hb, ha = best(ptop), best(top)
        if hb is not None and ha is not None and hb - ha >= 2:
            out.append({"kind": "逼近要地", "detail": f"离高价值胜利点的最短距离 {hb}→{ha} 个省"})
        if len(top.get("own_region_sizes", [])) > len(ptop.get("own_region_sizes", [])):
            out.append({"kind": "我方部队被围", "detail": f"我方陆地块由 {len(ptop.get('own_region_sizes', []))} 块变为 {len(top.get('own_region_sizes', []))} 块"})
    return out


def target_state(targets: set[str]) -> dict:
    import live_trial as lt

    s = lt.Session(check_sha=False)
    out = {}
    for i in range(len(s.countries())):
        tag = s.tag(i)
        if tag in targets:
            out[tag] = {"index": i, "at_war": s.at_war_with(i)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decider", default="decide_llm")
    ap.add_argument("--hours", type=int, default=12)
    ap.add_argument("--max-ticks", type=int, default=200)
    ap.add_argument("--targets", default="POL")
    ap.add_argument("--key-moments", action="store_true",
                    help="stop (paused) at typical turning points so the user can save a practice start")
    ap.add_argument("--watchdog", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--parent", type=int, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.watchdog:
        return watchdog(a.parent)

    targets = set(a.targets.split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    if STOP.exists():
        STOP.unlink()
    dog = subprocess.Popen([sys.executable, "-I", __file__, "--watchdog", "--parent", str(os.getpid())],
                           cwd=str(ROOT), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    score = None
    prev_ext = None
    try:
        done_before = sum(1 for x in PROGRESS.read_text(encoding="utf-8").splitlines() if x.strip())             if PROGRESS.exists() else 0
        for n in range(done_before + 1, done_before + a.max_ticks + 1):
            t0 = time.time()
            proc = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "live_trial.py"), "tick",
                                   "--decider", a.decider, "--allow-write", "--hours", str(a.hours)],
                                  cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
            try:
                tick = json.loads(proc.stdout)
            except ValueError:
                tick = {"error": (proc.stderr or proc.stdout)[-600:]}
            ext = {}
            try:
                # newest by write time: a name sort put an old "tick_..._practice_0826" file last forever,
                # so the score and key moments read stale data for a whole mock exam
                cap = max(OUT.glob("tick_*_capture.json"), key=lambda p: p.stat().st_mtime)
                ext = json.loads(cap.read_text(encoding="utf-8")).get("commander_ext") or {}
            except (IndexError, ValueError, OSError):
                pass
            counts = {k: v for k, v in (ext.get("enemy_controlled_provinces") or {}).items() if k in targets}
            moments = key_moments(prev_ext, ext, targets) if a.key_moments else []
            prev_ext = ext or prev_ext
            war = target_state(targets)
            clock = ((tick.get("clock") or {}).get("end")) or {}
            executed = tick.get("executed") or []
            row = {"tick": n, "at": datetime.now().isoformat(timespec="seconds"),
                   "game": f"{clock.get('ui_date')} {clock.get('ui_hour')}h", "pause": clock.get("pause"),
                   "target_provinces": counts, "target_war": war,
                   "orders_ok": sum(1 for e in executed if e.get("ok")),
                   "orders_refused": sum(1 for e in executed if not e.get("ok")),
                   "halted": tick.get("halted"), "error": tick.get("error") or tick.get("stop"),
                   "seconds": round(time.time() - t0), "summary": (tick.get("brief_summary") or "")[:300],
                   "key_moments": moments}
            with PROGRESS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            done = [t for t in targets
                    if (t in counts and counts[t] == 0) or (t in war and war[t]["at_war"] is False)]
            STATUS.write_text(json.dumps({"last": row, "score": score, "done": done},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
            if done:
                score = row["game"]
                STATUS.write_text(json.dumps({"last": row, "score": score, "done": done,
                                              "note": "target stopped resisting: no provinces or not at war"},
                                             ensure_ascii=False, indent=2), encoding="utf-8")
                break
            if moments and clock.get("pause") == 1:
                with KEY_MOMENTS.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"tick": n, "game": row["game"], "moments": moments,
                                        "suggested_save": "practice_" + row["game"].replace("-", "_").replace(" ", "_").replace("h", "")},
                                       ensure_ascii=False) + chr(10))
                STATUS.write_text(json.dumps({"last": row, "score": score, "paused_for_key_moment": moments},
                                             ensure_ascii=False, indent=2), encoding="utf-8")
                break  # game stays paused so the user can save this position
            if row["error"] or row["halted"] or clock.get("pause") != 1:
                break  # anything unexpected: stop and let a human/Claude look
            if STOP.exists():
                break
    finally:
        # the tick already paused; make sure, then let the watchdog finish
        try:
            import live_trial as lt
            lt.set_clock(False)
        except BaseException:
            pass
    print(json.dumps({"score": score}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
