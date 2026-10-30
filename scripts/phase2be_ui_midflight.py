"""Phase 2be: RO mid-flight capture via UI order + concurrent list poll + fast writable heap.

Never posts / never WriteProcessMemory. pause or 1x only (never 5x).
"""
from __future__ import annotations
import json, struct, sys, time, threading, ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2be_ui_midflight.json"

TARGETS = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A85468: "COrderExecuteCommand",
    0x2A27F28: "CChatCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A1F7E8: "CUnitStrategicMoveAction",
}


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def classify(p, base, cmd):
    if not cmd or cmd < 0x10000:
        return None
    try:
        vt = u64(p, cmd) - base
    except Exception:
        return None
    name = TARGETS.get(vt)
    if not name:
        return {"cmd": hex(cmd), "vt": hex(vt), "name": "?"}
    return {"cmd": hex(cmd), "vt": hex(vt), "name": name}


class Poller:
    def __init__(self, p, base, session, server):
        self.p = p
        self.base = base
        self.session = session
        self.server = server
        self.stop = False
        self.captures = []
        self.seen = {}
        self.iters = 0
        self.max_ring = 0
        self.lock = threading.Lock()

    def run(self):
        p, base, session, server = self.p, self.base, self.session, self.server
        while not self.stop:
            self.iters += 1
            try:
                cnt = u64(p, server + 0xC8)
                if cnt and cnt < 256:
                    self.max_ring = max(self.max_ring, int(cnt))
                    buf = u64(p, server + 0xB0)
                    for j in range(int(cnt)):
                        for stride in (8, 16, 24):
                            try:
                                c = classify(p, base, u64(p, buf + j * stride))
                                if c and c.get("name") not in (None, "?"):
                                    with self.lock:
                                        self.seen[c["name"]] = self.seen.get(c["name"], 0) + 1
                                        self.captures.append({"src": f"ring{stride}", **c, "i": self.iters})
                                    break
                            except Exception:
                                pass
                for label, head_off, is_session in (
                    ("pending", 0x58, False),
                    ("execlist", 0x40, False),
                    ("postexec", 0xF8, True),
                ):
                    head = u64(p, (session if is_session else server) + head_off)
                    node, g = head, 0
                    while node and g < 24:
                        g += 1
                        try:
                            # try both: node is cmd, or node[0]=cmd
                            c1 = classify(p, base, node)
                            c2 = classify(p, base, u64(p, node))
                            for c, how in ((c1, "as_obj"), (c2, "as_node")):
                                if c and c.get("name") not in (None, "?"):
                                    with self.lock:
                                        self.seen[c["name"]] = self.seen.get(c["name"], 0) + 1
                                        self.captures.append({"src": label + "/" + how, **c, "i": self.iters})
                            node = u64(p, node + 0x10)
                        except Exception:
                            break
                sc = u32(p, session + 0x54)
                if sc and sc < 64:
                    data = u64(p, session + 0x48)
                    for j in range(sc):
                        c = classify(p, base, u64(p, data + j * 8))
                        if c and c.get("name") not in (None, "?"):
                            with self.lock:
                                self.seen[c["name"]] = self.seen.get(c["name"], 0) + 1
                                self.captures.append({"src": "stage", **c, "i": self.iters})
            except Exception:
                pass
            time.sleep(0.001)


def dump_move_action(p, base, addr):
    try:
        arr = u64(p, addr + 0x18)
        psz = u32(p, addr + 0x24)
        p0 = u32(p, arr) if arr and psz else None
    except Exception:
        p0, psz = None, None
    return {
        "unit_handle": [u32(p, addr + 0x10), u32(p, addr + 0x14)],
        "province_size": psz,
        "province0": p0,
        "path_size": u32(p, addr + 0x3C),
        "clear": p.read(addr + 0x50, 1)[0],
        "safe": p.read(addr + 0x51, 1)[0],
        "move_priority": u32(p, addr + 0x58),
    }


def dump_move_cmd(p, base, addr):
    act = addr + 0x28
    out = dump_move_action(p, base, act)
    out["action_vt"] = hex(u64(p, act) - base)
    out["word18"] = u32(p, addr + 0x18)
    out["word1c"] = u32(p, addr + 0x1C)
    return out


def fast_writable_scan(p, base, max_hits=40):
    """Use mem.Proc.regions(writable=True) like phase2ap."""
    needles = {name: struct.pack("<Q", base + rva) for rva, name in TARGETS.items()}
    # skip hourly/chat for heap focus
    focus = ("CMoveCommand", "CCancelMovement", "CStrategicRedeploymentCommand",
             "CUnitMoveAction", "CUnitStrategicMoveAction", "COrderExecuteCommand")
    counts = {k: 0 for k in focus}
    samples = {k: [] for k in focus}
    scanned = 0
    chunk = 4 << 20
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        if base <= start < base + getattr(p, "image_size", 0x4000000):
            continue
        pos = start
        while pos < end:
            n = min(chunk, end - pos)
            data = p.try_read(pos, n)
            scanned += n
            if data:
                for k in focus:
                    needle = needles[k]
                    off = 0
                    while True:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            counts[k] += 1
                            if len(samples[k]) < 6:
                                addr = pos + i
                                entry = {"addr": hex(addr)}
                                try:
                                    if k == "CMoveCommand":
                                        entry["fields"] = dump_move_cmd(p, base, addr)
                                    elif k == "CUnitMoveAction":
                                        entry["fields"] = dump_move_action(p, base, addr)
                                    elif k == "CUnitStrategicMoveAction":
                                        entry["fields"] = {
                                            "army_handle": [u32(p, addr + 0x10), u32(p, addr + 0x14)],
                                            "province": u32(p, addr + 0x18),
                                            "clear": p.read(addr + 0x1C, 1)[0],
                                            "move_priority": u32(p, addr + 0x20),
                                        }
                                    elif k == "CStrategicRedeploymentCommand":
                                        entry["fields"] = {
                                            "action_vt": hex(u64(p, addr + 0x28) - base),
                                            "army_handle": [u32(p, addr + 0x38), u32(p, addr + 0x3C)],
                                            "province": u32(p, addr + 0x40),
                                        }
                                except Exception as e:
                                    entry["err"] = str(e)
                                samples[k].append(entry)
                        off = i + 8
            pos += n
    return {"scanned_mb": scanned >> 20, "counts": {k: v for k, v in counts.items() if v}, "samples": {k: v for k, v in samples.items() if v}}


def ui_sequence():
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_cb(h, _):
        if user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(h, buf, 512)
            t = buf.value or ""
            if "Heart" in t or "hoi4" in t.lower():
                found.append((int(h), t))
        return True

    user32.EnumWindows(enum_cb, 0)
    hwnd = user32.FindWindowW(None, "Hearts of Iron IV")
    if not hwnd and found:
        hwnd = found[0][0]
    info = {"hwnd": int(hwnd) if hwnd else None, "windows": found[:6], "steps": []}
    if not hwnd:
        return info

    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)

    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    rc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    # home camera: press Home? HOI4 uses numpad / - ; try 'f' find? Use H? Actually backspace centers?
    # Press Home key often used; also try Ctrl+Home. We'll click geometric grid.

    def key(vk):
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(vk, 0, 2, 0)

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

    def click(cx, cy, right=False):
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

    # Space -> unpause (expect resume at 1x from prior / start_speed handling)
    key(0x20)
    info["steps"].append("space_unpause")
    time.sleep(0.4)

    # Ensure speed not high: tap comma (speed down) a few times — HOI4 uses +/- or keypad
    # Plus=0xBB Minus=0xBD; also OEM. Safer: press '1' does nothing for speed.
    # Documented: + / - keys. Press minus 4 times to force toward 1x/pause-adjacent.
    for _ in range(4):
        key(0xBD)  # VK_OEM_MINUS
        time.sleep(0.05)
    info["steps"].append("minus_x4_toward_1x")
    time.sleep(0.2)

    w, h = rc.r, rc.b
    grid = [
        (int(w * 0.50), int(h * 0.50)),
        (int(w * 0.48), int(h * 0.48)),
        (int(w * 0.52), int(h * 0.52)),
        (int(w * 0.45), int(h * 0.55)),
        (int(w * 0.55), int(h * 0.45)),
        (int(w * 0.40), int(h * 0.50)),
        (int(w * 0.60), int(h * 0.50)),
    ]
    for i, (x, y) in enumerate(grid):
        sx, sy = click(x, y, right=False)
        info["steps"].append(f"lclick_{i}:{sx},{sy}")
        time.sleep(0.12)

    # Try strategic redeploy hotkey then right-click destination
    key(0x42)  # 'B'
    info["steps"].append("key_B_strategic")
    time.sleep(0.15)

    dx, dy = int(w * 0.58), int(h * 0.58)
    sx, sy = click(dx, dy, right=True)
    info["steps"].append(f"rclick_dest:{sx},{sy}")
    time.sleep(0.35)

    # second right-click alternate dest (normal move if B cancelled)
    sx, sy = click(int(w * 0.42), int(h * 0.42), right=True)
    info["steps"].append(f"rclick_alt:{sx},{sy}")
    time.sleep(0.5)

    # re-pause
    key(0x20)
    info["steps"].append("space_pause")
    time.sleep(0.3)
    info["client"] = {"w": w, "h": h}
    return info


def main():
    from mem import Proc, find_pid

    pid = find_pid("hoi4.exe")
    if not pid:
        print("no hoi4", file=sys.stderr)
        return 2
    p = Proc(pid)
    base = p.base
    idler = u64(p, base + OV["G_IDLER"])
    session = u64(p, u64(p, idler + 0x530) + 0x380)
    server = u64(p, session + 0x40)

    report = {
        "phase": "2be",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "before": {
            "drain": u32(p, session + 0x60),
            "exec": u32(p, session + 0x6C8),
            "seq": u32(p, server + 0xD0),
        },
    }

    poller = Poller(p, base, session, server)
    th = threading.Thread(target=poller.run, daemon=True)
    th.start()
    time.sleep(0.05)

    print("UI sequence...", flush=True)
    report["ui"] = ui_sequence()

    # keep polling a bit after pause for lingering stage/actions
    time.sleep(0.8)
    poller.stop = True
    th.join(timeout=2.0)

    with poller.lock:
        caps = list(poller.captures)
        seen = dict(poller.seen)

    report["poll"] = {
        "iters": poller.iters,
        "max_ring": poller.max_ring,
        "seen": seen,
        "captures_n": len(caps),
        "captures": caps[:50],
        "interesting": [c for c in caps if c.get("name") not in ("CHourlyTickCommand", "?")][:30],
    }

    print("fast writable heap...", flush=True)
    t0 = time.time()
    report["heap"] = fast_writable_scan(p, base)
    report["heap"]["elapsed_s"] = round(time.time() - t0, 2)

    report["after"] = {
        "drain": u32(p, session + 0x60),
        "exec": u32(p, session + 0x6C8),
        "seq": u32(p, server + 0xD0),
        "pending": hex(u64(p, server + 0x58)),
        "stage_count": u32(p, session + 0x54),
    }
    report["delta_drain"] = report["after"]["drain"] - report["before"]["drain"]
    report["delta_exec"] = report["after"]["exec"] - report["before"]["exec"]
    report["delta_seq"] = report["after"]["seq"] - report["before"]["seq"]

    report["caught_move_cmd"] = (
        any(c.get("name") == "CMoveCommand" for c in caps)
        or report["heap"]["counts"].get("CMoveCommand", 0) > 0
    )
    report["caught_move_action"] = report["heap"]["counts"].get("CUnitMoveAction", 0) > 0
    report["caught_strategic"] = (
        any(c.get("name") in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction") for c in caps)
        or report["heap"]["counts"].get("CStrategicRedeploymentCommand", 0) > 0
        or report["heap"]["counts"].get("CUnitStrategicMoveAction", 0) > 0
    )
    report["caught_any_army_cmd"] = report["caught_move_cmd"] or report["caught_strategic"] or report["caught_move_action"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:16000])
    print("wrote", OUT)
    p.close()
    return 0 if report["caught_any_army_cmd"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
