#!/usr/bin/env python3
"""Live trial tool for the TEST SAVE only (user authorization 2026-11-23).

Subcommands
  guard                     read-only: process, exe fingerprint, session, pause, speed, clock
  capture                   read-only: production capture() -> decide_v0 -> files + summary
  order --type T --unit U [--dest D]  dry-run (factory + IsValid); --live for ONE gated Post
                            T = move | strategic_redeploy | cancel
  watch --unit U [--dest D] read-only polling while the USER presses space (1x) in game

Rules baked in
  * Never posts pause/speed commands; the user controls the clock with the space key.
  * --live requires: official pause 1, speed slot 0 (1x), known exe SHA, unit idle
    (empty path, empty command list), dest is a land neighbour inside the player's
    own registered areas, dry-run valid. Gate opened only around the one Post.
  * Every action is appended to research/claude_live/ledger.jsonl (the receipt book).
  * Any uncertain result stops; nothing is retried.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALLING = ROOT / "calling"
sys.path.insert(0, str(CALLING))
os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)

OUTDIR = ROOT / "research" / "claude_live"
LEDGER = OUTDIR / "ledger.jsonl"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY_MARKER = ROOT / "research" / "strategic_only_tool_gate.OPEN"
PROFILE = json.loads((CALLING / "tables" / "offsets_input_windows_1.19.5.json")
                     .read_text(encoding="utf-8-sig"))
G_IDLER = 0x33DDB08


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def is_ptr(x) -> bool:
    return type(x) is int and 0x10000 < x < 0x7FFFFFFFFFFF


def ledger(entry: dict) -> dict:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    seq = 1
    if LEDGER.exists():
        seq = sum(1 for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()) + 1
    entry = {"seq": seq, "at": now(), **entry}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    return entry


def emit(obj) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def process_health(pid: int) -> dict:
    import ctypes
    from ctypes import wintypes as wt

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.CloseHandle.argtypes = [wt.HANDLE]
    h = k.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not h:
        return {"alive": False, "exit_code": None}
    try:
        code = wt.DWORD(0)
        k.GetExitCodeProcess(h, ctypes.byref(code))
        return {"alive": code.value == 259, "exit_code": int(code.value)}
    finally:
        k.CloseHandle(h)


# --------------------------------------------------------------------- session
class Session:
    """Read-only bound session. Re-create after any Post or clock change."""

    def __init__(self, check_sha: bool = True):
        from mem import Proc, find_pid
        from pe import PE
        from gamestate import detect_session, resolve_player_country, read_campaign_summary

        self.pid = find_pid("hoi4.exe")
        if not self.pid:
            raise SystemExit("HOI4 is not running")
        self.p = Proc(self.pid)
        self.sha = None
        if check_sha:
            h = hashlib.sha256()
            with open(self.p.image_path, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            self.sha = h.hexdigest().upper()
        self.sha_ok = self.sha is None or self.sha == PROFILE["exe_sha256"].upper()
        self.pe = PE(self.p.image_path)
        sess = detect_session(self.p, self.pe)
        self.in_game = bool(sess.get("in_game"))
        self.gs = int(sess["signals"]["gs_ptr"], 16) if self.in_game else 0
        self.idler = int(sess["signals"].get("idler_ptr") or "0", 16) if self.in_game else 0
        self.player = resolve_player_country(self.p, self.gs) if self.in_game else {}
        self.country = int(self.player["country_ptr"], 16) if self.player.get("ok") else 0
        self._summary = read_campaign_summary if self.in_game else None

    def q(self, a):
        return struct.unpack("<Q", self.p.read(a, 8))[0]

    def u32(self, a):
        return struct.unpack("<I", self.p.read(a, 4))[0]

    def i32(self, a):
        return struct.unpack("<i", self.p.read(a, 4))[0]

    def clock(self) -> dict:
        ver = (self._summary(self.p, self.gs).get("verified") or {}) if self._summary else {}
        date = ver.get("date_full") or ver.get("date") or {}
        return {
            "pause": self.p.read(self.idler + 0x6C1, 1)[0] if self.idler else None,
            "speed_slot": self.i32(self.gs + 0x4BC) if self.gs else None,
            "ui_date": date.get("ui"), "ui_hour": date.get("ui_hour"),
            "hour_tick": date.get("hour_tick"),
        }

    def info(self) -> dict:
        return {
            "pid": self.pid, "base": hex(self.p.base), "health": process_health(self.pid),
            "exe_sha256_ok": self.sha_ok, "in_game": self.in_game,
            "player": {"index": self.player.get("player_index"), "ok": self.player.get("ok")},
            "clock": self.clock() if self.in_game else None,
        }

    # ---- units
    def army(self, unit_id: int) -> int:
        from handle import resolve_handle, HANDLE_TYPE_ARMY
        from process import Backend

        b = Backend()
        return resolve_handle(b, HANDLE_TYPE_ARMY, unit_id, b.image_base) or 0

    def u32_array(self, a, bound=64):
        data, cap, size = struct.unpack("<QII", self.p.read(a, 16))
        if not (0 <= size <= cap <= bound) or (size and not is_ptr(data)):
            return None
        return list(struct.unpack("<" + "I" * size, self.p.read(data, size * 4))) if size else []

    def unit(self, unit_id: int) -> dict | None:
        a = self.army(unit_id)
        if not a or self.q(a) - self.p.base != PROFILE["vtable_rvas"]["CArmy"]:
            return None
        cl = struct.unpack("<QII", self.p.read(a + 0x2C0, 16))
        return {
            "unit_id": self.u32(a + 0x1C), "province_id": self.u32(a + 0x28),
            "path": self.u32_array(a + 0x200), "full_path": self.u32_array(a + 0x220),
            "commandlist_size": cl[2], "movement_progress": self.i32(a + 0x240),
            "retreat": self.p.read(a + 0x24C, 1)[0], "withdraw": self.p.read(a + 0x24D, 1)[0],
            "strategic_redeployment": self.p.read(a + 0x2AF, 1)[0],
        }

    def province_ptr(self, pid_: int) -> int:
        from province import resolve_province

        shim = type("B", (), {"read": self.p.read, "image_base": self.p.base})()
        return resolve_province(shim, pid_, self.p.base, self.gs) or 0

    def land_neighbors(self, province_id: int) -> dict:
        from gamestate import _rtti_name_from_vtable
        from input_loaded_fields import LoadedReader, province_adjacencies

        def cls(a):
            return _rtti_name_from_vtable(self.pe, self.q(a) - self.p.base) if is_ptr(a) else None

        loaded = LoadedReader(self.p.read, cls)
        return province_adjacencies(loaded, self.province_ptr(province_id))

    def own_area(self, province_id: int) -> bool:
        data, cap, size = struct.unpack("<QII", self.p.read(self.country + 0x548, 16))
        if not (0 <= size <= cap <= 4096) or (size and not is_ptr(data)):
            return False
        areas = {self.q(data + 8 * j) for j in range(size)}
        prov = self.province_ptr(province_id)
        return bool(prov) and self.q(prov + 0xD0) in areas


# ------------------------------------------------------------------ commands
def cmd_guard(_args):
    s = Session()
    emit(s.info())


def cmd_capture(_args):
    import input_capture_live
    import decide_v0
    import generalissimo_output as contract

    result = input_capture_live.capture()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cap_path = OUTDIR / f"capture_{stamp}.json"
    cap_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    doc = decide_v0.load_input(cap_path, None, True)
    out = decide_v0.decide(doc)
    errs = contract.validate_output(out, doc)
    dec_path = OUTDIR / f"decide_{stamp}.json"
    dec_path.write_text(json.dumps({"output": out, "validation_errors": errs},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    world = doc.get("world", {})
    emit({
        "capture": str(cap_path.relative_to(ROOT)), "decide": str(dec_path.relative_to(ROOT)),
        "meta": doc.get("meta"), "schema_error_count": result.get("schema_validation", {}).get("error_count"),
        "units": [{k: u.get(k) for k in ("unit_id", "name", "province_id", "organization", "in_combat")}
                  for u in world.get("own_units", [])],
        "brief": out.get("brief"), "alerts": [a["message"] for a in out["alerts"]],
        "decide_valid": not errs,
    })


def _open_gate():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.write_text("claude live_trial: one gated Post on the user's test save (2026-11-23).\n",
                      encoding="utf-8")


def _close_gate():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    for m in (MARKER, LEGACY_MARKER):
        if m.exists():
            m.unlink()


def _executor(kind):
    import move_order as mo
    import strategic_order as so
    import cancel_order as co

    if kind == "move":
        return lambda u, d, dry: mo.move(u, d, dry_run=dry)
    if kind == "strategic_redeploy":
        return lambda u, d, dry: so.strategic_redeploy(u, d, dry_run=dry)
    if kind == "cancel":
        return lambda u, d, dry: co.cancel_movement(u, dry_run=dry)
    raise ValueError(kind)


def run_order(kind: str, unit: int, dest: int | None, live: bool) -> dict:
    """One order with all pre/post checks. Returns the report (report["ok"])."""
    from config import allow_post

    args = argparse.Namespace(type=kind, unit=unit, dest=dest, live=live)
    _close_gate()
    s = Session()
    info = s.info()
    target = [args.dest] if args.dest is not None else []
    report = {"step": "order", "type": kind, "live": args.live, "session": info,
              "unit": args.unit, "dest": args.dest}

    def record(**fields):
        return ledger({"type": kind, "subject": {"unit_ids": [args.unit]},
                       "target_province_ids": target, "live": args.live, **fields})

    def stop(code, **extra):
        report.update({"ok": False, "stop": code, **extra})
        record(result=code, accepted=False, game_clock=info.get("clock"))
        return report

    if not (info["health"]["alive"] and info["in_game"] and info["exe_sha256_ok"]):
        return stop("SESSION_NOT_READY")
    clk = info["clock"]
    if clk["pause"] != 1 or clk["speed_slot"] != 0:
        return stop("NOT_PAUSED_AT_1X", clock=clk)
    before = s.unit(args.unit)
    report["unit_before"] = before
    if not before:
        return stop("UNIT_NOT_FOUND")
    if kind == "cancel":
        if not before["path"]:
            return stop("NOTHING_TO_CANCEL")
    else:
        if args.dest is None:
            return stop("DEST_REQUIRED")
        if before["path"] != [] or before["commandlist_size"] != 0:
            return stop("UNIT_NOT_IDLE")
        if not s.own_area(args.dest):
            return stop("DEST_NOT_OWN_AREA")
        if kind == "move":
            adj = s.land_neighbors(before["province_id"])
            report["neighbors"] = adj.get("neighbors")
            if args.dest not in (adj.get("neighbors") or []):
                return stop("DEST_NOT_LAND_NEIGHBOR")

    run = _executor(kind)
    dry = run(args.unit, args.dest, True)
    report["dry_run"] = dry
    if dry.get("result") != "DRY_RUN_VALID":
        return stop("DRY_RUN_NOT_VALID")
    if not args.live:
        report["ok"] = True
        record(result="DRY_RUN_VALID", accepted=None, game_clock=clk)
        return report

    s2 = Session(check_sha=False)  # recheck pause right before the Post
    clk2 = s2.clock()
    if s2.pid != s.pid or clk2["pause"] != 1 or clk2["speed_slot"] != 0:
        return stop("CLOCK_CHANGED_BEFORE_POST", clock=clk2)
    try:
        _open_gate()
        if not allow_post():
            return stop("GATE_DID_NOT_OPEN")
        posted = run(args.unit, args.dest, False)
    finally:
        _close_gate()
    report["post"] = posted
    time.sleep(1.0)
    health = process_health(s.pid)
    report["health_after"] = health
    if not health["alive"]:
        return stop("PROCESS_DIED_AFTER_POST", post=posted)
    s3 = Session(check_sha=False)
    after = s3.unit(args.unit) or {}
    report["unit_after"] = after
    report["clock_after"] = s3.clock()
    report["gate_closed"] = not allow_post() and not MARKER.exists()
    if kind == "cancel":
        effect_ok = after.get("path") == []
    else:
        effect_ok = args.dest in (after.get("path") or [])
    report["post_effect_visible"] = effect_ok
    report["ok"] = (posted.get("post_wait") == 0 and effect_ok
                    and report["clock_after"]["pause"] == 1)
    entry = record(result=posted.get("result"), post_wait=posted.get("post_wait"),
                   post_rax=posted.get("post_rax"),
                   # cancel is complete once the path is empty while paused;
                   # movement orders are accepted only after arrival is observed
                   accepted=True if (kind == "cancel" and effect_ok) else None,
                   path_after=after.get("path"),
                   strategic_flag=after.get("strategic_redeployment"),
                   game_clock=report["clock_after"])
    report["ledger_seq"] = entry["seq"]
    return report


def cmd_order(args):
    report = run_order(args.type, args.unit, args.dest, args.live)
    emit(report)
    return 0 if report.get("ok") else 2


def cmd_watch(args):
    samples = []
    start = None
    for i in range(args.samples):
        s = Session(check_sha=False)
        u = s.unit(args.unit)
        c = s.clock()
        row = {"i": i, "clock": c, "unit": u}
        samples.append(row)
        if start is None:
            start = row
        arrived = bool(u and args.dest and u["province_id"] == args.dest)
        print(json.dumps({"i": i, "date": f"{c['ui_date']} {c['ui_hour']}h", "pause": c["pause"],
                          "province": u and u["province_id"], "path": u and u["path"],
                          "progress": u and u["movement_progress"]}), flush=True)
        if arrived:
            break
        if i + 1 < args.samples:
            time.sleep(args.interval)
    end = samples[-1]
    result = {"unit": args.unit, "dest": args.dest, "start": start, "end": end,
              "arrived": bool(args.dest and end["unit"] and end["unit"]["province_id"] == args.dest)}
    if args.dest and args.record:
        ticks = None
        if start["clock"]["hour_tick"] is not None and end["clock"]["hour_tick"] is not None:
            ticks = end["clock"]["hour_tick"] - start["clock"]["hour_tick"]
        result["ledger"] = ledger({"type": "observation", "of": "move",
                                   "subject": {"unit_ids": [args.unit]},
                                   "target_province_ids": [args.dest],
                                   "accepted": True if result["arrived"] else None,
                                   "province_now": end["unit"] and end["unit"]["province_id"],
                                   "hours_observed": ticks, "game_clock": end["clock"]})
    emit(result)
    return 0


# ----------------------------------------------------------------------- clock
# The user delegated the space key (2026-11-23). We press space in the game
# window exactly like a player would, then verify the official pause flag.
# No CPauseGame or speed command is ever posted.
def _hwnds(pid: int) -> list[int]:
    import ctypes
    from ctypes import wintypes as wt

    u = ctypes.WinDLL("user32", use_last_error=True)
    found = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        owner = wt.DWORD(0)
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and u.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    u.EnumWindows(proc(cb), 0)
    return found


def _press_space(pid: int, method: str) -> None:
    import ctypes
    from ctypes import wintypes as wt

    u = ctypes.WinDLL("user32", use_last_error=True)
    hwnds = _hwnds(pid)
    if not hwnds:
        raise RuntimeError("no visible HOI4 window")
    hwnd = hwnds[0]
    VK_SPACE, SCAN = 0x20, 0x39
    if method == "post":
        u.PostMessageW(hwnd, 0x0100, VK_SPACE, 1 | (SCAN << 16))
        time.sleep(0.05)
        u.PostMessageW(hwnd, 0x0101, VK_SPACE, 1 | (SCAN << 16) | (0xC0 << 24))
        return
    # foreground + SendInput (scan code, as DirectInput-style games expect)
    u.ShowWindow(hwnd, 9)
    u.SetForegroundWindow(hwnd)
    time.sleep(0.3)

    class KI(ctypes.Structure):
        _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                    ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class INP(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", KI), ("pad", ctypes.c_byte * 32)]
        _anonymous_ = ("u",)
        _fields_ = [("type", wt.DWORD), ("u", _U)]

    def send(flags):
        i = INP(type=1)
        i.ki = KI(0, SCAN, 0x0008 | flags, 0, 0)  # KEYEVENTF_SCANCODE
        u.SendInput(1, ctypes.byref(i), ctypes.sizeof(INP))

    send(0)
    time.sleep(0.06)
    send(0x0002)  # KEYUP


def set_clock(want_run: bool) -> dict:
    """Set pause state via the space key; verify by reading the official flag."""
    s = Session(check_sha=False)
    target = 0 if want_run else 1
    log = {"want": "run" if want_run else "pause", "before": s.clock(), "attempts": []}
    if log["before"]["speed_slot"] != 0:
        log["result"] = "SPEED_NOT_1X_REFUSED"
        return log
    if log["before"]["pause"] == target:
        log["result"] = "ALREADY"
        return log
    # running: one try per method; pausing is the safe direction, allow more tries
    methods = ["post", "input"] if want_run else ["post", "input", "input", "input"]
    for m in methods:
        _press_space(s.pid, m)
        for _ in range(10):
            time.sleep(0.2)
            c = Session(check_sha=False).clock()
            if c["pause"] == target:
                log["attempts"].append({"method": m, "ok": True})
                log["after"] = c
                log["result"] = "OK"
                return log
        log["attempts"].append({"method": m, "ok": False, "clock": c})
    log["after"] = Session(check_sha=False).clock()
    log["result"] = "FAILED"
    return log


def cmd_clock(args):
    res = set_clock(args.state == "run")
    ledger({"type": "clock", "want": args.state, "result": res["result"],
            "methods": res["attempts"], "game_clock": res.get("after") or res["before"]})
    emit(res)
    return 0 if res["result"] in ("OK", "ALREADY") else 2


# ------------------------------------------------------------------ commander tick
SUPPORTED = {"move", "strategic_redeploy", "cancel"}  # verified end to end on 1.19.5


def run_hours(hours: int, timeout_s: float = 400.0) -> dict:
    """Unpause (space key), wait until the hour tick advanced `hours`, pause again."""
    start = Session(check_sha=False).clock()
    res = {"start": start}
    run = set_clock(True)
    res["run"] = run["result"]
    t0 = time.time()
    try:
        if run["result"] != "OK":
            return res
        while time.time() - t0 < timeout_s:
            c = Session(check_sha=False).clock()
            if c["hour_tick"] is not None and c["hour_tick"] - start["hour_tick"] >= hours:
                break
            time.sleep(0.4)
    finally:
        res["pause"] = set_clock(False)["result"]
        res["end"] = Session(check_sha=False).clock()
    return res


def _expand(order: dict) -> list[tuple[str, int, int | None]] | str:
    """Map a contract order onto verified executors, or return a refusal reason."""
    t = order["type"]
    if t not in SUPPORTED:
        return f"UNSUPPORTED_ON_1.19.5:{t}"
    units = order["subject"].get("unit_ids")
    if not units or set(order["subject"]) != {"unit_ids"}:
        return "ONLY_UNIT_SUBJECTS_SUPPORTED"
    if t == "cancel":
        if order.get("cancel_scope") != "current_movement":
            return "ONLY_CANCEL_CURRENT_MOVEMENT_SUPPORTED"
        return [("cancel", u, None) for u in units]
    targets = order["target_province_ids"]
    if len(targets) != 1 or order.get("path_province_ids"):
        return "ONLY_SINGLE_TARGET_SUPPORTED"
    return [(t, u, targets[0]) for u in units]


def cmd_tick(args):
    import importlib
    import decide_v0
    import generalissimo_output as contract
    import input_capture_live

    tick = {"at": now(), "decider": args.decider, "allow_write": args.allow_write}
    s = Session()
    clk = s.clock()
    if not (s.in_game and s.sha_ok and clk["pause"] == 1 and clk["speed_slot"] == 0):
        tick["stop"] = "NOT_READY_OR_NOT_PAUSED_1X"
        tick["clock"] = clk
        emit(tick)
        return 2
    result = input_capture_live.capture()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cap_path = OUTDIR / f"tick_{stamp}_capture.json"
    cap_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    doc = decide_v0.load_input(cap_path, None, True)
    doc.setdefault("meta", {})["allow_write"] = bool(args.allow_write)
    decider = importlib.import_module(args.decider)
    output = decider.decide(doc)
    errors = contract.validate_output(output, doc)
    tick["validation_errors"] = errors
    tick["alerts"] = [a["message"] for a in output.get("alerts", [])]
    tick["brief_summary"] = (output.get("brief") or {}).get("summary")
    executed = []
    if not errors:
        for order in sorted(output.get("orders", []), key=lambda o: o["order_seq"]):
            plan = _expand(order)
            if isinstance(plan, str):
                executed.append({"order_seq": order["order_seq"], "type": order["type"],
                                 "refused": plan})
                ledger({"type": order["type"], "order_seq": order["order_seq"],
                        "result": plan, "accepted": False, "error": plan})
                continue
            halted = False
            for kind, unit, dest in plan:
                rep = run_order(kind, unit, dest, live=True)
                # Refused before any Post (pre-checks / dry run) is a certain "no":
                # record and continue. Anything after the Post that is not confirmed
                # is uncertain: stop the tick, never retry.
                posted_phase = "post" in rep or rep.get("stop") in (
                    "CLOCK_CHANGED_BEFORE_POST", "GATE_DID_NOT_OPEN", "PROCESS_DIED_AFTER_POST")
                executed.append({"order_seq": order["order_seq"], "type": kind, "unit": unit,
                                 "dest": dest, "ok": rep.get("ok"), "stop": rep.get("stop"),
                                 "posted": "post" in rep})
                if not rep.get("ok") and posted_phase:
                    halted = True
                    break
            if halted:
                tick["halted"] = "ORDER_NOT_CONFIRMED_STOPPING_TICK"
                break
    tick["executed"] = executed
    if args.hours and not tick.get("halted"):
        tick["clock"] = run_hours(args.hours)
    (OUTDIR / f"tick_{stamp}_decide.json").write_text(
        json.dumps({"output": output, "tick": tick}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    emit(tick)
    return 0 if not errors and not tick.get("halted") else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("guard")
    sub.add_parser("capture")
    m = sub.add_parser("order")
    m.add_argument("--type", required=True, choices=["move", "strategic_redeploy", "cancel"])
    m.add_argument("--unit", type=int, required=True)
    m.add_argument("--dest", type=int)
    m.add_argument("--live", action="store_true")
    w = sub.add_parser("watch")
    w.add_argument("--unit", type=int, required=True)
    w.add_argument("--dest", type=int)
    w.add_argument("--samples", type=int, default=20)
    w.add_argument("--interval", type=float, default=3.0)
    w.add_argument("--record", action="store_true", help="append observation to the ledger")
    c = sub.add_parser("clock", help="press space in the game window; verify pause flag")
    c.add_argument("state", choices=["run", "pause"])
    k = sub.add_parser("tick", help="one commander beat: capture->decide->execute->run hours")
    k.add_argument("--decider", default="decide_v0", help="module under calling/ with decide()")
    k.add_argument("--allow-write", action="store_true", help="set meta.allow_write=true")
    k.add_argument("--hours", type=int, default=0, help="game hours to run after executing")
    args = ap.parse_args(argv)
    return {"tick": cmd_tick,"guard": cmd_guard, "capture": cmd_capture, "order": cmd_order,
            "watch": cmd_watch, "clock": cmd_clock}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
