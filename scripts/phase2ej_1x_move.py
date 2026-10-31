"""Phase 2ej: 1x without Post; try land MOVE without Post; RO midflight.

1) Focus+Space SendInput (expect fail on DX11 like 2bf/2bg)
2) If still paused: relaunch -start_tag=HAI -start_speed=1 -noai
3) RO prove clock via date_aux / HourlyTick / DummyServer counters
4) Cheap synthetic RMB move attempt; document Post blocker
NEVER: ALLOW_POST / Post / GameSpeed Post / HourlyTick Post / 5x / guess writes.
"""
from __future__ import annotations
import json, struct, sys, time, ctypes, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid
import post_abi

OUT = ROOT / "reports" / "phase2ej_1x_move.json"
CAPTURE = ROOT / "reports" / "midflight_cmove_capture.json"
HB = ROOT / "reports" / "midflight_watcher_heartbeat.json"

WATCH = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A85468: "COrderExecuteCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A1F7E8: "CUnitStrategicMoveAction",
}


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def try_u64(p, a):
    try:
        return u64(p, a)
    except Exception:
        return None


def send_key_scancode(scancode, down=True):
    user32 = ctypes.windll.user32

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

    flags = 0x0008 | (0x0002 if not down else 0)
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(0, scancode, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_space():
    send_key_scancode(0x39, True)
    time.sleep(0.05)
    send_key_scancode(0x39, False)


def force_focus(hwnd):
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    fg = user32.GetForegroundWindow()
    pid = ctypes.c_ulong()
    tid_fg = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    tid_tg = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    tid_me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(tid_me, tid_fg, True)
    user32.AttachThreadInput(tid_me, tid_tg, True)
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(tid_me, tid_fg, False)
    user32.AttachThreadInput(tid_me, tid_tg, False)
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(New-Object -ComObject WScript.Shell).AppActivate('Hearts of Iron IV') | Out-Null"],
        timeout=5, check=False, capture_output=True,
    )


def find_hwnd(pid):
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        p = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def snap(p):
    base = p.base
    sess = u64(p, base + post_abi.G_SESSION)
    server = u64(p, sess + post_abi.CSession_SERVER)
    return {
        "pid": p.pid,
        "sess": hex(sess),
        "server": hex(server),
        "date_year": u32(p, sess + 0x478),
        "date_aux": u32(p, sess + 0x47c),
        "drain": u32(p, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(p, sess + post_abi.CSession_EXEC_COUNTER),
        "stage_count": u32(p, sess + post_abi.CSession_STAGE_COUNT),
        "seq": u32(p, server + 0xD0),
        "pending_h": hex(try_u64(p, server + post_abi.CDummyServer_PENDING) or 0),
    }


def walk_pending_names(p, head, limit=48):
    names = []
    cur = head
    seen = set()
    base = p.base
    for _ in range(limit):
        if not cur or cur in seen:
            break
        seen.add(cur)
        vt = try_u64(p, cur)
        if vt is None:
            break
        rva = vt - base
        name = WATCH.get(rva, f"vt_{rva:#x}")
        names.append(name)
        nxt = try_u64(p, cur + 8)
        if nxt == cur:
            break
        cur = nxt
    return names


def poll_activity(p, seconds=8.0, interval=0.05):
    t0 = time.time()
    seen_names = {}
    s0 = snap(p)
    while time.time() - t0 < seconds:
        s = snap(p)
        head = int(s["pending_h"], 16)
        for n in walk_pending_names(p, head):
            seen_names[n] = seen_names.get(n, 0) + 1
        try:
            sess = int(s["sess"], 16)
            stage = try_u64(p, sess + post_abi.CSession_STAGE_ARRAY) or 0
            sc = s["stage_count"]
            if stage and 0 < sc < 64:
                for i in range(sc):
                    ptr = try_u64(p, stage + i * 8)
                    if not ptr:
                        continue
                    vt = try_u64(p, ptr)
                    if vt is None:
                        continue
                    name = WATCH.get(vt - p.base, None)
                    if name:
                        seen_names[f"stage:{name}"] = seen_names.get(f"stage:{name}", 0) + 1
        except Exception:
            pass
        time.sleep(interval)
    s1 = snap(p)
    return {
        "s0": s0, "s1": s1,
        "seen_names": seen_names,
        "drain_delta": s1["drain"] - s0["drain"],
        "exec_delta": s1["exec"] - s0["exec"],
        "aux_delta": s1["date_aux"] - s0["date_aux"],
        "year_delta": s1["date_year"] - s0["date_year"],
        "hourly": any("HourlyTick" in k for k in seen_names),
        "cmove": any("CMoveCommand" in k or "UnitMove" in k for k in seen_names),
    }


def status_snip():
    r = subprocess.run(
        [sys.executable, str(ROOT / "clausewitz_win.py"), "status"],
        capture_output=True, text=True, timeout=90, cwd=str(ROOT),
    )
    out = r.stdout or ""
    keys = []
    for line in out.splitlines():
        if any(k in line for k in (
            "date_", "idler", "CInGame", "armies_count", "allow", "command_queue",
            "player_tag", "drain", "exec", "G_CONSOLE",
        )):
            keys.append(line.strip())
    return {"rc": r.returncode, "keys": keys[-40:], "len": len(out)}


def stop_midflight_watchers():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -match 'phase2bm_midflight' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
         "'ok'"],
        capture_output=True, text=True, timeout=30,
    )


def relaunch_1x():
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "launch_into_map.py"), "--speed", "1"],
        capture_output=True, text=True, timeout=30, cwd=str(ROOT),
    )


def wait_ingame(timeout=220):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        try:
            pid = find_pid("hoi4.exe")
            p = Proc(pid)
            s = snap(p)
            last = s
            if find_hwnd(pid) and s.get("date_year") == 1936 and s.get("sess") != "0x0":
                st = status_snip()
                joined = " ".join(st.get("keys") or [])
                if "CInGameIdler" in joined:
                    return {"ok": True, "pid": pid, "snap": s, "status_keys": st["keys"],
                            "elapsed": round(time.time() - t0, 1)}
        except Exception as e:
            last = {"err": str(e)}
        time.sleep(6)
    return {"ok": False, "last": last, "elapsed": round(time.time() - t0, 1)}


def rearm_watcher():
    log_out = ROOT / "reports" / "_midflight_ready_stdout.txt"
    log_err = ROOT / "reports" / "_midflight_ready_stderr.txt"
    py = sys.executable
    script = str(ROOT / "scripts" / "phase2bm_midflight_ready.py")
    arglist = "'{0}' --seconds 86400 --interval 0.05 --heap-every 0".format(script)
    ps = (
        "$p = Start-Process -FilePath '{py}' -ArgumentList {args} "
        "-WorkingDirectory '{wd}' -WindowStyle Hidden "
        "-RedirectStandardOutput '{o}' -RedirectStandardError '{e}' "
        "-PassThru; $p.Id"
    ).format(py=py, args=arglist, wd=str(ROOT), o=str(log_out), e=str(log_err))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=30)
    return {"rc": r.returncode, "pid": (r.stdout or "").strip(), "err": (r.stderr or "").strip()}


def ui_try_move(hwnd):
    user32 = ctypes.windll.user32
    force_focus(hwnd)
    time.sleep(0.25)
    rect = ctypes.wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = ctypes.wintypes.POINT(rect.right // 2, int(rect.bottom * 0.55))
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    user32.SetCursorPos(pt.x, pt.y)
    time.sleep(0.05)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.3)
    user32.SetCursorPos(pt.x + 48, pt.y + 24)
    time.sleep(0.05)
    user32.mouse_event(0x0008, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(0x0010, 0, 0, 0, 0)
    return {"lmb": [pt.x, pt.y], "rmb": [pt.x + 48, pt.y + 24]}


def main():
    (ROOT / "reports").mkdir(exist_ok=True)
    report = {
        "phase": "2ej",
        "ts": datetime.now().isoformat(timespec="seconds"),
        "allow_post": False,
        "never_5x": True,
        "paths": [],
        "clock": {},
        "move": {},
        "midflight": {},
        "blocker_move": None,
    }

    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    hwnd = find_hwnd(pid)
    report["baseline"] = {"snap": snap(p), "hwnd": hex(hwnd) if hwnd else None}
    report["baseline"]["status"] = status_snip()

    path_a = {"name": "focus_space"}
    if hwnd:
        force_focus(hwnd)
        time.sleep(0.2)
        for _ in range(3):
            force_focus(hwnd)
            tap_space()
            time.sleep(0.35)
        pol = poll_activity(p, seconds=6.0)
        path_a["poll"] = pol
        path_a["unpaused_likely"] = bool(
            pol["hourly"] or pol["drain_delta"] > 0 or pol["exec_delta"] > 0 or abs(pol["aux_delta"]) > 0
        )
    else:
        path_a["unpaused_likely"] = False
        path_a["error"] = "no hwnd"
    report["paths"].append(path_a)

    used_relaunch = False
    if not path_a.get("unpaused_likely"):
        used_relaunch = True
        path_b = {"name": "relaunch_start_speed_1"}
        stop_midflight_watchers()
        rr = relaunch_1x()
        path_b["relaunch_rc"] = rr.returncode
        path_b["relaunch_out"] = (rr.stdout or "")[-500:]
        wait = wait_ingame(timeout=220)
        path_b["wait"] = wait
        report["paths"].append(path_b)
        if not wait.get("ok"):
            report["clock"]["advanced"] = False
            report["clock"]["error"] = "map wait failed after relaunch"
            OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps({"wrote": str(OUT), "error": "map wait failed"}, indent=2))
            return 2
        pid = find_pid("hoi4.exe")
        p = Proc(pid)
        hwnd = find_hwnd(pid)
        path_b["watcher"] = rearm_watcher()
        time.sleep(1.5)
        pol = poll_activity(p, seconds=22.0, interval=0.08)
        report["clock"]["poll"] = pol
        report["clock"]["advanced"] = bool(
            pol["hourly"] or pol["drain_delta"] > 0 or abs(pol["aux_delta"]) > 0 or pol["year_delta"] != 0
        )
        report["clock"]["proof"] = {
            "hourly": pol["hourly"],
            "drain_delta": pol["drain_delta"],
            "exec_delta": pol["exec_delta"],
            "aux_t0": pol["s0"]["date_aux"],
            "aux_t1": pol["s1"]["date_aux"],
            "year_t0": pol["s0"]["date_year"],
            "year_t1": pol["s1"]["date_year"],
            "exec_t0": pol["s0"]["exec"],
            "exec_t1": pol["s1"]["exec"],
        }
    else:
        pol = poll_activity(p, seconds=15.0, interval=0.08)
        report["clock"]["poll"] = pol
        report["clock"]["advanced"] = bool(
            pol["hourly"] or pol["drain_delta"] > 0 or abs(pol["aux_delta"]) > 0
        )
        report["clock"]["proof"] = {
            "hourly": pol["hourly"],
            "drain_delta": pol["drain_delta"],
            "exec_delta": pol["exec_delta"],
            "aux_t0": pol["s0"]["date_aux"],
            "aux_t1": pol["s1"]["date_aux"],
        }

    move = {"method": "synthetic_lmb_rmb", "post_enabled": False}
    try:
        pid = find_pid("hoi4.exe")
        p = Proc(pid)
        hwnd = find_hwnd(pid)
        if hwnd:
            move["clicks"] = ui_try_move(hwnd)
            pol_m = poll_activity(p, seconds=5.0, interval=0.05)
            move["poll"] = pol_m
            move["cmove_seen"] = pol_m["cmove"]
            if not pol_m["cmove"]:
                report["blocker_move"] = (
                    "No CMoveCommand after synthetic LMB+RMB. "
                    "DX11/RawInput ignores SendInput/mouse_event (same as 2bf/2bg Space). "
                    "Catalogued issue path is DummyServer Post / move_command_recipe — "
                    "requires ALLOW_POST which remains False. "
                    "G_CONSOLE_MANAGER / FN_CONSOLE_EXECUTE unavailable. "
                    "-noai => no autonomous army movement either."
                )
        else:
            move["error"] = "no hwnd"
            report["blocker_move"] = "no hwnd"
    except Exception as e:
        move["error"] = str(e)
        report["blocker_move"] = str(e)
    report["move"] = move

    report["midflight"]["capture_exists"] = CAPTURE.is_file()
    if CAPTURE.is_file():
        try:
            report["midflight"]["capture"] = json.loads(CAPTURE.read_text(encoding="utf-8"))
        except Exception as e:
            report["midflight"]["capture_err"] = str(e)
    if HB.is_file():
        try:
            report["midflight"]["heartbeat"] = json.loads(HB.read_text(encoding="utf-8"))
        except Exception:
            pass

    report["status_final"] = status_snip()
    report["used_relaunch_1x"] = used_relaunch
    report["allow_post_final"] = False
    report["final_snap"] = snap(Proc(find_pid("hoi4.exe")))

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {
        "wrote": str(OUT),
        "clock_advanced": report["clock"].get("advanced"),
        "proof": report["clock"].get("proof"),
        "cmove_seen": move.get("cmove_seen"),
        "relaunch": used_relaunch,
        "allow_post": False,
        "blocker": (report.get("blocker_move") or "")[:240],
        "watcher": (report["paths"][-1].get("watcher") if used_relaunch else None),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())