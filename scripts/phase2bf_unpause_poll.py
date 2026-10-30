"""Phase 2bf: force-focus HOI4, Space to 1x, RO poll for HourlyTick / Move; re-pause.

Never posts. Never 5x (minus x4 after unpause). 
"""
from __future__ import annotations
import json, struct, sys, time, ctypes, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bf_unpause_poll.json"

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
    user32.SetActiveWindow(hwnd)
    user32.SetFocus(hwnd)
    user32.AttachThreadInput(tid_me, tid_fg, False)
    user32.AttachThreadInput(tid_me, tid_tg, False)
    # also AppActivate via COM
    try:
        import subprocess
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(New-Object -ComObject WScript.Shell).AppActivate('Hearts of Iron IV') | Out-Null",
            ],
            timeout=5,
            check=False,
        )
    except Exception:
        pass
    time.sleep(0.4)
    return int(user32.GetForegroundWindow()) == int(hwnd)


def key(vk):
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, 2, 0)


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
    return pt.x, pt.y


def classify(p, base, addr):
    if not addr or addr < 0x10000:
        return None
    try:
        vt = u64(p, addr) - base
    except Exception:
        return None
    return {"addr": hex(addr), "vt": hex(vt), "name": VT.get(vt, "?")}


def main():
    hold_s = 3.0
    for a in sys.argv[1:]:
        if a.replace(".", "", 1).isdigit():
            hold_s = float(a)

    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    base = p.base
    idler = u64(p, base + OV["G_IDLER"])
    session = u64(p, u64(p, idler + 0x530) + 0x380)
    server = u64(p, session + 0x40)

    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "Hearts of Iron IV (DirectX 11)")
    if not hwnd:
        hwnd = user32.FindWindowW(None, "Hearts of Iron IV")
    report = {
        "phase": "2bf",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "hwnd": int(hwnd) if hwnd else None,
        "hold_s": hold_s,
    }
    report["before"] = {
        "drain": u32(p, session + 0x60),
        "exec": u32(p, session + 0x6C8),
        "seq": u32(p, server + 0xD0),
        "fg": int(user32.GetForegroundWindow()),
    }

    focused = force_focus(hwnd) if hwnd else False
    report["focused"] = focused
    report["fg_after_focus"] = int(user32.GetForegroundWindow())

    # dump sticky postexec sample (known CStartGame)
    pe = u64(p, session + 0xF8)
    cmd = u64(p, pe) if pe else 0
    report["postexec_sticky"] = classify(p, base, cmd)

    captures = []
    seen = {}
    stop = False

    def poller():
        while not stop:
            try:
                # pending as node list: node[0]=cmd
                for label, head in (
                    ("pending", u64(p, server + 0x58)),
                    ("execlist", u64(p, server + 0x40)),
                ):
                    node, g = head, 0
                    while node and g < 32:
                        g += 1
                        try:
                            c = classify(p, base, u64(p, node))
                            if c:
                                seen[c["name"]] = seen.get(c["name"], 0) + 1
                                if c["name"] != "?":
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
                # postexec node
                pe2 = u64(p, session + 0xF8)
                if pe2:
                    c = classify(p, base, u64(p, pe2))
                    if c and c["name"] != "?":
                        seen["postexec:" + c["name"]] = seen.get("postexec:" + c["name"], 0) + 1
            except Exception:
                pass
            time.sleep(0.001)

    th = threading.Thread(target=poller, daemon=True)
    th.start()

    # Unpause
    key(0x20)
    time.sleep(0.25)
    for _ in range(5):
        key(0xBD)  # minus toward 1x
        time.sleep(0.05)
    report["steps"] = ["space_unpause", "minus_x5"]

    # brief army click attempt mid-hold
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]

    rc = RECT()
    if hwnd:
        user32.GetClientRect(hwnd, ctypes.byref(rc))
        # bottom-left army bar region + map center
        spots = [
            (int(rc.r * 0.15), int(rc.b * 0.88)),
            (int(rc.r * 0.25), int(rc.b * 0.88)),
            (int(rc.r * 0.50), int(rc.b * 0.50)),
            (int(rc.r * 0.48), int(rc.b * 0.48)),
        ]
        t_mid = time.time() + hold_s * 0.4
        while time.time() < t_mid:
            time.sleep(0.05)
        for i, (x, y) in enumerate(spots):
            click_client(hwnd, x, y, right=False)
            report["steps"].append(f"lclick:{x},{y}")
            time.sleep(0.1)
        click_client(hwnd, int(rc.r * 0.55), int(rc.b * 0.55), right=True)
        report["steps"].append("rclick_dest")
        key(0x42)
        report["steps"].append("key_B")
        click_client(hwnd, int(rc.r * 0.60), int(rc.b * 0.50), right=True)
        report["steps"].append("rclick_b")

    # hold remaining
    time.sleep(max(0.5, hold_s * 0.5))

    # re-pause
    key(0x20)
    report["steps"].append("space_pause")
    time.sleep(0.4)
    stop = True
    th.join(timeout=2)

    report["after"] = {
        "drain": u32(p, session + 0x60),
        "exec": u32(p, session + 0x6C8),
        "seq": u32(p, server + 0xD0),
        "fg": int(user32.GetForegroundWindow()),
    }
    report["delta"] = {
        "drain": report["after"]["drain"] - report["before"]["drain"],
        "exec": report["after"]["exec"] - report["before"]["exec"],
        "seq": report["after"]["seq"] - report["before"]["seq"],
    }
    report["seen"] = seen
    # unique captures by name
    uniq = {}
    for c in captures:
        uniq.setdefault(c["name"], c)
    report["captures_unique"] = list(uniq.values())
    report["captures_n"] = len(captures)
    report["unpaused_likely"] = report["delta"]["seq"] > 0 or report["delta"]["exec"] > 0
    report["caught_hourly"] = "CHourlyTickCommand" in seen
    report["caught_move_cmd"] = "CMoveCommand" in seen
    report["caught_move_action"] = "CUnitMoveAction" in seen
    report["caught_strategic"] = any(
        k in seen for k in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction")
    )


    # inline small scan for move VTs only, writable,  first 2GB worth or until hit
    if True:
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
        for m in p.regions(writable=True, min_size=0x1000):
            start, end = m["start"], m["end"]
            if base <= start < base + getattr(p, "image_size", 0x4000000):
                continue
            pos = start
            while pos < end and scanned < (3 << 30):
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
                                if len(samples[k]) < 3:
                                    samples[k].append(hex(pos + i))
                            off = i + 8
                pos += n
            if any(counts[k] for k in ("CMoveCommand", "CUnitMoveAction", "CStrategicRedeploymentCommand", "CUnitStrategicMoveAction")):
                # keep scanning a bit more for samples then stop early
                if sum(counts[k] for k in counts) > 5:
                    break
        report["heap"] = {
            "scanned_mb": scanned >> 20,
            "counts": {k: v for k, v in counts.items() if v},
            "samples": {k: v for k, v in samples.items() if v},
        }
        report["caught_move_cmd"] = report["caught_move_cmd"] or counts.get("CMoveCommand", 0) > 0
        report["caught_move_action"] = report["caught_move_action"] or counts.get("CUnitMoveAction", 0) > 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:14000])
    print("wrote", OUT)
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
