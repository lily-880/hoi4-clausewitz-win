"""Phase 2bi: issue move WHILE PAUSED (HOI4 allows orders when paused).

Unit already selected (Garde d'Haiti). Right-click Dominican province.
Also try strategic-redeploy button then destination.
Never unpause to 5x. Never Post from tooling. RO observe.
"""
from __future__ import annotations
import json, struct, sys, time, ctypes, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bi_paused_move.json"

VT = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A85468: "COrderExecuteCommand",
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
    user32.AttachThreadInput(tid_me, tid_fg, False)
    user32.AttachThreadInput(tid_me, tid_tg, False)
    time.sleep(0.25)


def click_screen(sx, sy, right=False):
    """Click absolute SCREEN coords (screenshot space = primary screen)."""
    user32 = ctypes.windll.user32

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
    ax = int(sx * 65535 / max(sw, 1))
    ay = int(sy * 65535 / max(sh, 1))
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
    act = addr + 0x28 if kind == "CMoveCommand" else addr
    if kind == "CUnitStrategicMoveAction":
        return {
            "army_handle": [u32(p, addr + 0x10), u32(p, addr + 0x14)],
            "province": u32(p, addr + 0x18),
            "clear": p.read(addr + 0x1C, 1)[0],
            "move_priority": u32(p, addr + 0x20),
        }
    if kind == "CStrategicRedeploymentCommand":
        return dump_move(p, base, addr + 0x28, "CUnitStrategicMoveAction")
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
        "action_vt": hex(u64(p, act) - base) if kind == "CMoveCommand" else None,
        "word18": u32(p, addr + 0x18) if kind == "CMoveCommand" else None,
        "word1c": u32(p, addr + 0x1C) if kind == "CMoveCommand" else None,
    }


def main():
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    base = p.base
    idler = u64(p, base + OV["G_IDLER"])
    session = u64(p, u64(p, idler + 0x530) + 0x380)
    server = u64(p, session + 0x40)
    user32 = ctypes.windll.user32
    # enum windows for exact title
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_cb(h, _):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(h, buf, 512)
        if buf.value and "Heart" in buf.value:
            found.append((int(h), buf.value))
        return True

    user32.EnumWindows(enum_cb, 0)
    hwnd = found[0][0] if found else 0

    report = {
        "phase": "2bi",
        "posting": "DISABLED",
        "speed_rule": "stay paused; never 5x",
        "pid": pid,
        "hwnd": hwnd,
        "windows": found[:5],
        "before": {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)},
        "note": "screenshot showed Garde d'Haiti selected; right-click DOM province while paused",
    }

    if hwnd:
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
                                if c["name"] not in ("?", "CStartGameCommand"):
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
                            if c["name"] not in ("?", "CStartGameCommand"):
                                captures.append({"src": "stage", **c})
                cnt = u64(p, server + 0xC8)
                if cnt and cnt < 64:
                    seen["ring_max"] = max(seen.get("ring_max", 0), int(cnt))
                    buf = u64(p, server + 0xB0)
                    for j in range(int(cnt)):
                        for stride in (8, 16):
                            try:
                                c = classify(p, base, u64(p, buf + j * stride))
                                if c and c["name"] not in ("?", "CStartGameCommand"):
                                    seen[c["name"]] = seen.get(c["name"], 0) + 1
                                    captures.append({"src": f"ring{stride}", **c})
                                    break
                            except Exception:
                                pass
            except Exception:
                pass
            time.sleep(0.0005)

    th = threading.Thread(target=poller, daemon=True)
    th.start()
    time.sleep(0.05)

    steps = []
    # 1) re-select unit on map near Port-au-Prince (~847, 620)
    for pos in ((820, 610), (847, 630), (800, 600)):
        click_screen(*pos, right=False)
        steps.append(f"lclick_unit:{pos}")
        time.sleep(0.12)

    # 2) normal move: right-click Dominican east of Haiti (~960, 600)
    for pos in ((960, 600), (980, 610), (940, 580), (1000, 620)):
        click_screen(*pos, right=True)
        steps.append(f"rclick_move:{pos}")
        time.sleep(0.15)
        # check counters
        if u32(p, server + 0xD0) != report["before"]["seq"] or u32(p, session + 0x6C8) != report["before"]["exec"]:
            steps.append("counter_moved_after_rclick")
            break

    time.sleep(0.3)

    # 3) strategic redeploy button in unit panel (~240, 125) then dest
    click_screen(240, 125, right=False)
    steps.append("lclick_rail_btn:240,125")
    time.sleep(0.15)
    click_screen(250, 130, right=False)
    steps.append("lclick_rail_btn:250,130")
    time.sleep(0.15)
    click_screen(970, 605, right=True)
    steps.append("rclick_strat:970,605")
    time.sleep(0.4)

    # 4) also try left-click rail then left-click destination (some HOI4 modes)
    click_screen(255, 128, right=False)
    time.sleep(0.1)
    click_screen(990, 615, right=False)
    steps.append("lclick_strat_dest:990,615")
    time.sleep(0.5)

    stop = True
    th.join(timeout=2)

    report["steps"] = steps
    report["after"] = {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)}
    report["delta"] = {k: report["after"][k] - report["before"][k] for k in ("drain", "exec", "seq")}
    report["seen"] = seen
    uniq = {}
    for c in captures:
        uniq.setdefault(c["name"], c)
    report["captures_unique"] = list(uniq.values())[:40]
    report["captures_n"] = len(captures)
    report["caught_move_cmd"] = "CMoveCommand" in seen
    report["caught_move_action"] = "CUnitMoveAction" in seen
    report["caught_strategic"] = any(k in seen for k in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction"))

    # heap scan for lingering actions (orders persist on unit after execute)
    needles = {
        "CMoveCommand": struct.pack("<Q", base + 0x2A2C790),
        "CUnitMoveAction": struct.pack("<Q", base + 0x2A1F648),
        "CStrategicRedeploymentCommand": struct.pack("<Q", base + 0x2A2D818),
        "CUnitStrategicMoveAction": struct.pack("<Q", base + 0x2A1F7E8),
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
        while pos < end and scanned < (4 << 30):
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
                            if len(samples[k]) < 5:
                                addr = pos + i
                                entry = {"addr": hex(addr)}
                                try:
                                    entry["fields"] = dump_move(p, base, addr, k)
                                except Exception as e:
                                    entry["err"] = str(e)
                                samples[k].append(entry)
                        off = i + 8
            pos += n
        if any(counts[k] for k in counts):
            # continue a bit for more samples then can break if enough
            if sum(counts.values()) >= 2:
                # finish current region then stop
                pass
        if sum(counts.values()) >= 4:
            break
    report["heap"] = {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 2),
        "counts": {k: v for k, v in counts.items() if v},
        "samples": {k: v for k, v in samples.items() if v},
    }
    report["caught_move_cmd"] = report["caught_move_cmd"] or counts.get("CMoveCommand", 0) > 0
    report["caught_move_action"] = report["caught_move_action"] or counts.get("CUnitMoveAction", 0) > 0
    report["caught_strategic"] = report["caught_strategic"] or any(
        counts.get(k, 0) > 0 for k in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction")
    )
    report["caught_any"] = report["caught_move_cmd"] or report["caught_move_action"] or report["caught_strategic"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:16000])
    print("wrote", OUT)
    p.close()
    return 0 if report["caught_any"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
