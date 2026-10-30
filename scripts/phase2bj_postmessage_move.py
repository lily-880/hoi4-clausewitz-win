"""Phase 2bj: PostMessage mouse to HOI4 client (DX11 often ignores SendInput).

Stay paused. Right-click another Haiti province (intra-tag move).
Never posts from tooling. RO observe seq/heap.
"""
from __future__ import annotations
import json, struct, sys, time, ctypes, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bj_postmessage_move.json"

VT = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A5F448: "CStartGameCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A1F7E8: "CUnitStrategicMoveAction",
}


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def dump_move(p, base, addr, kind):
    act = addr + 0x28 if kind == "CMoveCommand" else addr
    if kind in ("CUnitStrategicMoveAction",):
        return {
            "army_handle": [u32(p, addr + 0x10), u32(p, addr + 0x14)],
            "province": u32(p, addr + 0x18),
            "clear": p.read(addr + 0x1C, 1)[0],
            "move_priority": u32(p, addr + 0x20),
        }
    try:
        arr = u64(p, act + 0x18)
        psz = u32(p, act + 0x24)
        p0 = u32(p, arr) if arr and psz else None
    except Exception:
        p0, psz = None, None
    return {
        "unit_handle": [u32(p, act + 0x10), u32(p, act + 0x14)],
        "province_size": psz, "province0": p0,
        "path_size": u32(p, act + 0x3C),
        "clear": p.read(act + 0x50, 1)[0], "safe": p.read(act + 0x51, 1)[0],
        "move_priority": u32(p, act + 0x58),
    }


class Mouse:
    WM_MOUSEMOVE = 0x0200
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONDOWN = 0x0204
    WM_RBUTTONUP = 0x0205
    WM_MOUSEACTIVATE = 0x0021
    WM_ACTIVATE = 0x0006
    WM_SETFOCUS = 0x0007
    MK_LBUTTON = 0x0001
    MK_RBUTTON = 0x0002

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.user32 = ctypes.windll.user32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]

        self.POINT = POINT
        self.RECT = RECT
        # window/client geometry
        wr, cr = RECT(), RECT()
        self.user32.GetWindowRect(hwnd, ctypes.byref(wr))
        self.user32.GetClientRect(hwnd, ctypes.byref(cr))
        self.win = (wr.l, wr.t, wr.r, wr.b)
        self.client = (cr.l, cr.t, cr.r, cr.b)
        # client origin in screen
        pt = POINT(0, 0)
        self.user32.ClientToScreen(hwnd, ctypes.byref(pt))
        self.origin = (pt.x, pt.y)

    def screen_to_client(self, sx, sy):
        pt = self.POINT(sx, sy)
        self.user32.ScreenToClient(self.hwnd, ctypes.byref(pt))
        return pt.x, pt.y

    def lp(self, cx, cy):
        return (cy << 16) | (cx & 0xFFFF)

    def activate(self):
        self.user32.ShowWindow(self.hwnd, 9)
        self.user32.SetForegroundWindow(self.hwnd)
        self.user32.PostMessageW(self.hwnd, self.WM_ACTIVATE, 1, 0)
        self.user32.PostMessageW(self.hwnd, self.WM_SETFOCUS, 0, 0)
        time.sleep(0.2)

    def click_client(self, cx, cy, right=False, use_send=True):
        msg_down = self.WM_RBUTTONDOWN if right else self.WM_LBUTTONDOWN
        msg_up = self.WM_RBUTTONUP if right else self.WM_LBUTTONUP
        mk = self.MK_RBUTTON if right else self.MK_LBUTTON
        lp = self.lp(cx, cy)
        fn = self.user32.SendMessageW if use_send else self.user32.PostMessageW
        fn(self.hwnd, self.WM_MOUSEMOVE, 0, lp)
        time.sleep(0.02)
        fn(self.hwnd, msg_down, mk, lp)
        time.sleep(0.04)
        fn(self.hwnd, msg_up, 0, lp)
        time.sleep(0.04)

    def click_screen(self, sx, sy, right=False, use_send=True):
        cx, cy = self.screen_to_client(sx, sy)
        self.click_client(cx, cy, right=right, use_send=use_send)
        return cx, cy


def classify(p, base, addr):
    if not addr or addr < 0x10000:
        return None
    try:
        vt = u64(p, addr) - base
    except Exception:
        return None
    return {"addr": hex(addr), "vt": hex(vt), "name": VT.get(vt, "?")}


def main():
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    base = p.base
    idler = u64(p, base + OV["G_IDLER"])
    session = u64(p, u64(p, idler + 0x530) + 0x380)
    server = u64(p, session + 0x40)
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_cb(h, _):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(h, buf, 512)
        if buf.value and "Heart" in buf.value and "Edge" not in buf.value:
            found.append(int(h))
        return True

    user32.EnumWindows(enum_cb, 0)
    hwnd = found[0] if found else 0
    mouse = Mouse(hwnd)

    report = {
        "phase": "2bj",
        "posting": "DISABLED",
        "speed_rule": "stay paused; never 5x",
        "pid": pid,
        "hwnd": hwnd,
        "win": mouse.win,
        "client": mouse.client,
        "origin": mouse.origin,
        "before": {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)},
    }

    mouse.activate()
    captures, seen = [], {}
    stop = False

    def poller():
        while not stop:
            try:
                for label, head in (("pending", u64(p, server + 0x58)), ("execlist", u64(p, server + 0x40))):
                    node, g = head, 0
                    while node and g < 24:
                        g += 1
                        try:
                            c = classify(p, base, u64(p, node))
                            if c:
                                seen[c["name"]] = seen.get(c["name"], 0) + 1
                                if c["name"] not in ("?", "CStartGameCommand"):
                                    captures.append({"src": label, **c})
                            node = u64(p, node + 0x10)
                        except Exception:
                            break
                sc = u32(p, session + 0x54)
                if sc and sc < 64:
                    data = u64(p, session + 0x48)
                    for j in range(sc):
                        c = classify(p, base, u64(p, data + j * 8))
                        if c and c["name"] not in ("?", "CStartGameCommand"):
                            seen[c["name"]] = seen.get(c["name"], 0) + 1
                            captures.append({"src": "stage", **c})
                cnt = u64(p, server + 0xC8)
                if cnt and cnt < 64:
                    seen["ring_max"] = max(seen.get("ring_max", 0), int(cnt))
            except Exception:
                pass
            time.sleep(0.0005)

    th = threading.Thread(target=poller, daemon=True)
    th.start()

    steps = []
    # Select near Port-au-Prince, then right-click western Haiti province (intra-tag)
    targets_select = [(820, 610), (847, 630), (800, 600)]
    targets_move = [(760, 590), (780, 610), (790, 580), (880, 620), (900, 640)]

    for use_send in (True, False):
        tag = "Send" if use_send else "Post"
        for sx, sy in targets_select:
            cx, cy = mouse.click_screen(sx, sy, right=False, use_send=use_send)
            steps.append(f"{tag}_L:{sx},{sy}->c{cx},{cy}")
            time.sleep(0.1)
        for sx, sy in targets_move:
            cx, cy = mouse.click_screen(sx, sy, right=True, use_send=use_send)
            steps.append(f"{tag}_R:{sx},{sy}->c{cx},{cy}")
            time.sleep(0.12)
            if u32(p, server + 0xD0) != report["before"]["seq"] or u32(p, session + 0x6C8) != report["before"]["exec"]:
                steps.append(f"counter_changed_after_{tag}")
                break
        if "counter_changed" in "".join(steps):
            break

    # Also try SendInput once more AFTER a SendMessage click (hybrid focus)
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

    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    for sx, sy, right in ((847, 630, False), (770, 600, True)):
        ax = int(sx * 65535 / max(sw, 1))
        ay = int(sy * 65535 / max(sh, 1))
        down = 0x0008 if right else 0x0002
        up = 0x0010 if right else 0x0004
        for fl in (0x8001, down | 0x8000, up | 0x8000):
            inp = INPUT(type=0)
            inp.mi = MOUSEINPUT(ax, ay, 0, fl, 0, None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.03)
        steps.append(f"SendInput_{'R' if right else 'L'}:{sx},{sy}")
        time.sleep(0.15)

    time.sleep(0.4)
    stop = True
    th.join(timeout=2)

    report["steps"] = steps
    report["after"] = {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)}
    report["delta"] = {k: report["after"][k] - report["before"][k] for k in ("drain", "exec", "seq")}
    report["seen"] = seen
    report["captures_n"] = len(captures)
    report["captures_unique"] = list({c["name"]: c for c in captures}.values())[:20]

    # heap
    needles = {n: struct.pack("<Q", base + r) for r, n in VT.items() if "Move" in n or "Strategic" in n}
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
                            if len(samples[k]) < 4:
                                addr = pos + i
                                entry = {"addr": hex(addr)}
                                try:
                                    entry["fields"] = dump_move(p, base, addr, k)
                                except Exception as e:
                                    entry["err"] = str(e)
                                samples[k].append(entry)
                        off = i + 8
            pos += n
        if sum(counts.values()) >= 2:
            break
    report["heap"] = {
        "scanned_mb": scanned >> 20,
        "counts": {k: v for k, v in counts.items() if v},
        "samples": {k: v for k, v in samples.items() if v},
    }
    report["caught_move_cmd"] = counts.get("CMoveCommand", 0) > 0 or "CMoveCommand" in seen
    report["caught_move_action"] = counts.get("CUnitMoveAction", 0) > 0
    report["caught_strategic"] = any(counts.get(k, 0) > 0 for k in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction"))
    report["caught_any"] = report["caught_move_cmd"] or report["caught_move_action"] or report["caught_strategic"]

    # live sticky StartGame dump as CCommand sample proof
    pe = u64(p, session + 0xF8)
    cmd = u64(p, pe) if pe else 0
    if cmd:
        blob = p.read(cmd, 0x40)
        report["live_CStartGameCommand_sample"] = {
            "addr": hex(cmd),
            "vt": hex(u64(p, cmd) - base),
            "header_u32": [hex(u32(p, cmd + i)) for i in range(0, 0x28, 4)],
            "hex": blob.hex(),
            "note": "sticky postexec live CCommand; Move midflight still needs UI input that reaches DX11",
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:16000])
    print("wrote", OUT)
    p.close()
    return 0 if report["caught_any"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
