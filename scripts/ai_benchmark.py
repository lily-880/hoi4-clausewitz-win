#!/usr/bin/env python3
"""Benchmark: let the game's own AI play Germany (console `human_ai`) from the
war-start save and record when Poland stops resisting.

  python -I scripts/ai_benchmark.py launch          # reload CC_GER_1939_08_14_base (kills the game)
  python -I scripts/ai_benchmark.py console human_ai  # type a console command (waits for user idle)
  python -I scripts/ai_benchmark.py run --hours 12 --max-ticks 140

`run` only advances the clock (space key, 1x, ends paused every tick) and reads
memory; it posts no commands. Progress: research/claude_live/ai_bench/progress.jsonl.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))

import game_ui as gu  # noqa: E402

OUT = ROOT / "research" / "claude_live" / "ai_bench"
SAVE = "CC_GER_1939_08_14_base"

# scan codes (US layout); "_" = shift + minus
SC = {**{c: s for c, s in zip("1234567890", range(0x02, 0x0C))},
      "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15, "u": 0x16, "i": 0x17, "o": 0x18,
      "p": 0x19, "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22, "h": 0x23, "j": 0x24, "k": 0x25,
      "l": 0x26, "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31, "m": 0x32,
      " ": 0x39, "-": 0x0C}
GRAVE, ENTER, SHIFT = 0x29, 0x1C, 0x2A


def _scan(code: int, up: bool) -> None:
    i = gu._INPUT(type=1)
    i.ki = gu._KI(0, code, 0x0008 | (0x0002 if up else 0), 0, 0)
    gu._send(i)
    time.sleep(0.05)


def _tap(code: int, shift: bool = False) -> None:
    if shift:
        _scan(SHIFT, False)
    _scan(code, False)
    _scan(code, True)
    if shift:
        _scan(SHIFT, True)
    time.sleep(0.04)


def wait_idle(min_idle: float = gu.MIN_IDLE, max_wait: float = 3 * 3600) -> None:
    t0 = time.time()
    while gu.idle_seconds() < min_idle:
        if time.time() - t0 > max_wait:
            raise SystemExit("user stayed active; console command not typed")
        time.sleep(10)


def console(cmd: str) -> Path:
    """Open the console, type cmd, Enter, screenshot, close the console."""
    wait_idle()
    hwnd = gu.find_window()
    gu._require_foreground(hwnd)
    _tap(GRAVE)
    time.sleep(0.6)
    for _ in range(40):  # clear any leftover text in the input line
        _tap(0x0E)
    for ch in cmd.lower():
        if ch == "_":
            _tap(SC["-"], shift=True)
        else:
            _tap(SC[ch])
    time.sleep(0.6)
    _scan(ENTER, False)
    time.sleep(0.15)
    _scan(ENTER, True)
    time.sleep(2.5)
    OUT.mkdir(parents=True, exist_ok=True)
    p = gu.shot(OUT / f"console_{cmd}_{time.strftime('%H%M%S')}.png", scale=0.6)
    _tap(GRAVE)
    return p


def console_bg(cmd: str) -> Path:
    """Same as console(), but posted to the game window without bringing it to
    the front (the user may be working in other windows)."""
    # Verified 2026-11-25: letters/digits must be posted as WM_KEYDOWN (a bare WM_CHAR
    # is ignored); "_" cannot get Shift in the background, so it goes as WM_CHAR, which
    # the console accepts after a key-down stream. Leaving the console open swallows
    # every later key (space no longer pauses), so the close is checked by the caller.
    hwnd = gu.find_window()
    _post_key(hwnd, 0xC0, GRAVE)  # open console
    time.sleep(0.8)
    for _ in range(40):
        _post_key(hwnd, 0x08, 0x0E)  # backspace: clear leftovers
    for ch in cmd.lower():
        if ch in SC and ch not in "-":
            _post_key(hwnd, 0x20 if ch == " " else ord(ch.upper()), SC[ch])
        else:
            ctypes.windll.user32.PostMessageW(hwnd, 0x0102, ord(ch), 1)
            time.sleep(0.08)
    time.sleep(0.4)
    _post_key(hwnd, 0x0D, ENTER)
    time.sleep(2.5)
    OUT.mkdir(parents=True, exist_ok=True)
    p = gu.shot(OUT / f"console_bg_{cmd.split()[0]}_{time.strftime('%H%M%S')}.png", scale=0.6)
    _post_key(hwnd, 0xC0, GRAVE)  # close console
    time.sleep(0.8)
    return p


def _post_key(hwnd: int, vk: int, scan: int) -> None:
    u = ctypes.windll.user32
    u.PostMessageW(hwnd, 0x0100, vk, 1 | (scan << 16))
    time.sleep(0.05)
    u.PostMessageW(hwnd, 0x0101, vk, 1 | (scan << 16) | (0xC0 << 24))
    time.sleep(0.08)


def clock_bg(want_run: bool, tries: int = 3) -> dict:
    """Pause/unpause with a space key posted in the background only. Never brings
    the game to the front (live_trial.set_clock falls back to SetForegroundWindow)."""
    import live_trial as lt
    target = 0 if want_run else 1
    c = lt.Session(check_sha=False).clock()
    if c["speed_slot"] != 0:
        return {"result": "SPEED_NOT_1X_REFUSED", "clock": c}
    if c["pause"] == target:
        return {"result": "ALREADY", "clock": c}
    hwnd = gu.find_window()
    for _ in range(tries):
        _post_key(hwnd, 0x20, 0x39)
        for _ in range(10):
            time.sleep(0.2)
            c = lt.Session(check_sha=False).clock()
            if c["pause"] == target:
                return {"result": "OK", "clock": c}
    return {"result": "FAILED", "clock": c}


def run_hours_bg(hours: int, timeout_s: float = 600) -> dict:
    import live_trial as lt
    start = lt.Session(check_sha=False).clock()
    res = {"start": start}
    run = clock_bg(True)
    res["run"] = run["result"]
    t0 = time.time()
    try:
        if run["result"] != "OK":
            return res
        while time.time() - t0 < timeout_s:
            c = lt.Session(check_sha=False).clock()
            if c["hour_tick"] is not None and c["hour_tick"] - start["hour_tick"] >= hours:
                break
            time.sleep(0.4)
    finally:
        res["pause"] = clock_bg(False, tries=6)["result"]
        res["end"] = lt.Session(check_sha=False).clock()
    return res


def poland_state() -> dict:
    """Province counts by controller, read province by province (Session.controller_of).
    The full capture() failed for ten game days in a row once the AI started
    reshuffling leaders ("assigned_to handle did not resolve"); this does not touch leaders."""
    import live_trial as lt
    from collections import Counter
    try:
        s = lt.Session(check_sha=False)
        idx = {s.tag(i): i for i in range(len(s.countries()))}
        want = {idx[t]: t for t in ("GER", "POL", "FRA") if t in idx}
        c = Counter()
        for pid in range(1, 13500):
            try:
                v = s.controller_of(pid)
            except Exception:
                continue
            if v in want:
                c[want[v]] += 1
        return {"enemy": {"POL": c["POL"], "FRA": c["FRA"]}, "own": c["GER"]}
    except Exception as e:
        return {"enemy": {}, "own": None, "read_error": f"{type(e).__name__}: {e}"[:200]}


def run(hours: int, max_ticks: int) -> int:
    import live_trial as lt
    OUT.mkdir(parents=True, exist_ok=True)
    prog = OUT / "progress.jsonl"
    score = None
    for n in range(1, max_ticks + 1):
        t0 = time.time()
        r = run_hours_bg(hours)
        end = r.get("end") or {}
        st = poland_state()
        row = {"tick": n, "at": datetime.now().isoformat(timespec="seconds"),
               "game": f"{end.get('ui_date')} {end.get('ui_hour')}h", "pause": end.get("pause"),
               "run": r.get("run"), "pause_result": r.get("pause"), **st,
               "seconds": round(time.time() - t0)}
        with prog.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if st["enemy"].get("POL", 1) == 0:
            score = row["game"]
            break
        if r.get("run") != "OK" or end.get("pause") != 1:
            break
        if (OUT / "STOP").exists():
            break
    (OUT / "status.json").write_text(json.dumps({"score": score, "last": row}, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    try:
        clock_bg(False, tries=6)
    except BaseException:
        pass
    if score:  # keep the end state as a save for the user (prefix CC_ = Claude's saves)
        try:
            console_bg("savegame")
        except BaseException:
            pass
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("launch")
    c = sub.add_parser("console")
    c.add_argument("text")
    c.add_argument("--bg", action="store_true", help="post to the window in the background")
    r = sub.add_parser("run")
    r.add_argument("--hours", type=int, default=12)
    r.add_argument("--max-ticks", type=int, default=140)
    a = ap.parse_args(argv)
    if a.cmd == "launch":
        gu.launch(SAVE)
    elif a.cmd == "console":
        print(console_bg(a.text) if a.bg else console(a.text))
    else:
        return run(a.hours, a.max_ticks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
