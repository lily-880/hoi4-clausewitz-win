"""Phase 2bg: Space-only unpause (NO minus — prior bug re-paused), RO midflight poll.

Never posts. Never 5x. Hold ~5s at whatever speed Space resumes (expect 1x from start_speed=0).
"""
from __future__ import annotations
import json, struct, sys, time, ctypes, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bg_space_midflight.json"

VT = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A85468: "COrderExecuteCommand",
    0x2A27F28: "CChatCommand",
    0x2A5F448: "CStartGameCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A1F7E8: "CUnitStrategicMoveAction",
}


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def send_key_scancode(scancode, down=True):
    user32 = ctypes.windll.user32

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

    flags = 0x0008  # KEYEVENTF_SCANCODE
    if not down:
        flags |= 0x0002  # KEYEVENTF_KEYUP
    inp = INPUT(type=1)  # INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(0, scancode, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_space():
    send_key_scancode(0x39, True)
    time.sleep(0.05)
    send_key_scancode(0x39, False)


def tap_plus():
    # OEM_PLUS scancode 0x0D on US; also try VK via keybd_event as backup
    send_key_scancode(0x0D, True)
    time.sleep(0.04)
    send_key_scancode(0x0D, False)
    ctypes.windll.user32.keybd_event(0xBB, 0, 0, 0)  # VK_OEM_PLUS
    time.sleep(0.04)
    ctypes.windll.user32.keybd_event(0xBB, 0, 2, 0)


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
    try:
        import subprocess
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(New-Object -ComObject WScript.Shell).AppActivate('Hearts of Iron IV') | Out-Null"],
            timeout=5, check=False,
        )
    except Exception:
        pass
    time.sleep(0.5)


def click_client(hwnd, cx, cy, right=False):
    user32 = ctypes.windll.user32

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

    pt = POINT(cx, cy)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    ax = int(pt.x * 65535 / max(sw, 1))
    ay = int(pt.y * 65535 / max(sh, 1))
    down = 0x0008 if right else 0x0002
    up = 0x0010 if right else 0x0004
    for fl in (0x8001, down | 0x8000, up | 0x8000):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(ax, ay, 0, fl, 0, None)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.03)


def classify(p, base, addr):
    if not addr or addr < 0x10000:
        return None
    try:
        vt = u64(p, addr) - base
    except Exception:
        return None
    return {"addr": hex(addr), "vt": hex(vt), "name": VT.get(vt, "?")}


def dump_move(p, base, addr, kind):
    if kind == "CMoveCommand":
        act = addr + 0x28
        try:
            arr = u64(p, act + 0x18)
            psz = u32(p, act + 0x24)
            p0 = u32(p, arr) if arr and psz else None
        except Exception:
            p0, psz = None, None
        return {
            "action_vt": hex(u64(p, act) - base),
            "unit_handle": [u32(p, act + 0x10), u32(p, act + 0x14)],
            "province_size": psz, "province0": p0,
            "path_size": u32(p, act + 0x3C),
            "clear": p.read(act + 0x50, 1)[0], "safe": p.read(act + 0x51, 1)[0],
            "move_priority": u32(p, act + 0x58),
            "word18": u32(p, addr + 0x18), "word1c": u32(p, addr + 0x1C),
        }
    if kind == "CUnitMoveAction":
        try:
            arr = u64(p, addr + 0x18)
            psz = u32(p, addr + 0x24)
            p0 = u32(p, arr) if arr and psz else None
        except Exception:
            p0, psz = None, None
        return {
            "unit_handle": [u32(p, addr + 0x10), u32(p, addr + 0x14)],
            "province_size": psz, "province0": p0,
            "path_size": u32(p, addr + 0x3C),
            "clear": p.read(addr + 0x50, 1)[0], "safe": p.read(addr + 0x51, 1)[0],
            "move_priority": u32(p, addr + 0x58),
        }
    return {}


def main():
    hold_s = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    do_plus = "--plus" in sys.argv
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    base = p.base
    idler = u64(p, base + OV["G_IDLER"])
    session = u64(p, u64(p, idler + 0x530) + 0x380)
    server = u64(p, session + 0x40)
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "Hearts of Iron IV (DirectX 11)") or user32.FindWindowW(None, "Hearts of Iron IV")

    report = {
        "phase": "2bg",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "note": "NO minus after Space (2bf bug: minus re-paused)",
        "pid": pid,
        "hold_s": hold_s,
        "do_plus": do_plus,
        "before": {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)},
        "postexec_sticky": classify(p, base, u64(p, u64(p, session + 0xF8))),
    }

    force_focus(hwnd)
    captures, seen = [], {}
    stop = False

    def poller():
        while not stop:
            try:
                for label, head in (("pending", u64(p, server + 0x58)), ("execlist", u64(p, server + 0x40))):
                    node, g = head, 0
                    while node and g < 32:
                        g += 1
                        try:
                            c = classify(p, base, u64(p, node))
                            if c:
                                seen[c["name"]] = seen.get(c["name"], 0) + 1
                                if c["name"] not in ("?",):
                                    if c["name"] in ("CMoveCommand", "CUnitMoveAction", "CStrategicRedeploymentCommand", "CUnitStrategicMoveAction"):
                                        try:
                                            c["fields"] = dump_move(p, base, int(c["addr"], 16), c["name"])
                                        except Exception as e:
                                            c["fields_err"] = str(e)
                                    captures.append({"src": label, **c})
                            node = u64(p, node + 0x10)
                        except Exception:
                            break
                sc = u32(p, session + 0x54)
                if sc and sc < 128:
                    data = u64(p, session + 0x48)
                    for j in range(sc):
                        c = classify(p, base, u64(p, data + j * 8))
                        if c:
                            seen[c["name"]] = seen.get(c["name"], 0) + 1
                            if c["name"] != "?":
                                captures.append({"src": "stage", **c})
                cnt = u64(p, server + 0xC8)
                if cnt and cnt < 64:
                    buf = u64(p, server + 0xB0)
                    seen["ring_max"] = max(seen.get("ring_max", 0), int(cnt))
                    for j in range(int(cnt)):
                        for stride in (8, 16):
                            try:
                                c = classify(p, base, u64(p, buf + j * stride))
                                if c and c["name"] != "?":
                                    seen[c["name"]] = seen.get(c["name"], 0) + 1
                                    captures.append({"src": f"ring{stride}", **c})
                                    break
                            except Exception:
                                pass
                pe = u64(p, session + 0xF8)
                if pe:
                    c = classify(p, base, u64(p, pe))
                    if c and c["name"] != "?":
                        seen["postexec:" + c["name"]] = seen.get("postexec:" + c["name"], 0) + 1
            except Exception:
                pass
            time.sleep(0.001)

    th = threading.Thread(target=poller, daemon=True)
    th.start()

    steps = []
    tap_space()
    steps.append("space_unpause_scancode")
    time.sleep(0.3)
    if do_plus:
        tap_plus()
        steps.append("plus_once_toward_1x")
        time.sleep(0.2)

    # army bar + map clicks during hold
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]

    rc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    t_end = time.time() + hold_s
    clicked = False
    while time.time() < t_end:
        if not clicked and time.time() > t_end - hold_s + 1.5:
            for x, y in (
                (int(rc.r * 0.12), int(rc.b * 0.90)),
                (int(rc.r * 0.20), int(rc.b * 0.90)),
                (int(rc.r * 0.50), int(rc.b * 0.50)),
            ):
                click_client(hwnd, x, y, False)
                steps.append(f"lclick:{x},{y}")
                time.sleep(0.08)
            click_client(hwnd, int(rc.r * 0.56), int(rc.b * 0.52), True)
            steps.append("rclick")
            clicked = True
        time.sleep(0.05)

    tap_space()
    steps.append("space_pause")
    time.sleep(0.5)
    stop = True
    th.join(timeout=2)

    report["steps"] = steps
    report["after"] = {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)}
    report["delta"] = {k: report["after"][k] - report["before"][k] for k in ("drain", "exec", "seq")}
    report["seen"] = seen
    uniq = {}
    for c in captures:
        uniq.setdefault(c["name"] + "@" + c.get("src", ""), c)
    report["captures_unique"] = list(uniq.values())[:40]
    report["captures_n"] = len(captures)
    report["unpaused_likely"] = report["delta"]["seq"] > 0 or report["delta"]["exec"] > 0
    report["caught_hourly"] = "CHourlyTickCommand" in seen
    report["caught_move_cmd"] = "CMoveCommand" in seen
    report["caught_move_action"] = "CUnitMoveAction" in seen
    report["caught_strategic"] = any(
        k in seen for k in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction")
    )

    # heap only if unpaused — look for lingering MoveAction after orders
    needles = {
        "CMoveCommand": struct.pack("<Q", base + 0x2A2C790),
        "CUnitMoveAction": struct.pack("<Q", base + 0x2A1F648),
        "CStrategicRedeploymentCommand": struct.pack("<Q", base + 0x2A2D818),
        "CUnitStrategicMoveAction": struct.pack("<Q", base + 0x2A1F7E8),
        "CHourlyTickCommand": struct.pack("<Q", base + 0x29F3710),
    }
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    t0 = time.time()
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        if base <= start < base + getattr(p, "image_size", 0x4000000):
            continue
        pos = start
        while pos < end and scanned < (2 << 30):
            n = min(4 << 20, end - pos)
            data = p.try_read(pos, n)
            scanned += n
            if data:
                for k, needle in needles.items():
                    off = 0
                    while True:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            counts[k] += 1
                            if len(samples[k]) < 4:
                                addr = pos + i
                                entry = {"addr": hex(addr)}
                                if k in ("CMoveCommand", "CUnitMoveAction"):
                                    try:
                                        entry["fields"] = dump_move(p, base, addr, k)
                                    except Exception as e:
                                        entry["err"] = str(e)
                                samples[k].append(entry)
                        off = i + 8
            pos += n
        if counts.get("CMoveCommand") or counts.get("CUnitMoveAction"):
            if sum(counts.values()) >= 3:
                break
    report["heap"] = {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 2),
        "counts": {k: v for k, v in counts.items() if v},
        "samples": {k: v for k, v in samples.items() if v},
    }
    report["caught_move_cmd"] = report["caught_move_cmd"] or counts.get("CMoveCommand", 0) > 0
    report["caught_move_action"] = report["caught_move_action"] or counts.get("CUnitMoveAction", 0) > 0
    report["caught_hourly"] = report["caught_hourly"] or counts.get("CHourlyTickCommand", 0) > 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:16000])
    print("wrote", OUT)
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
