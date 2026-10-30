"""Phase 2bd: RO full-heap scan for CMoveCommand / MoveAction VTs + optional UI move.

Never posts. Never writes game memory. pause/1x only.
"""
from __future__ import annotations
import json, struct, sys, time, ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid  # noqa: E402

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bd_heap_move.json"

TARGETS = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A1F7E8: "CUnitStrategicMoveAction",
    0x2A85468: "COrderExecuteCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def rtti(b, base, obj):
    try:
        vt = u64(b, obj)
        col = u64(b, vt - 8)
        td = u64(b, col + 0x10)
        return b.read(td + 0x10, 80).split(b"\0", 1)[0].decode("latin1", "replace")
    except Exception:
        return None


def dump_move_cmd(b, base, p):
    # action embed @ +0x28 per cmd_layout
    act = p + 0x28
    try:
        arr = u64(b, act + 0x18)
        psz = u32(b, act + 0x24)
        p0 = u32(b, arr) if arr and psz else None
    except Exception:
        p0, psz = None, None
    return {
        "unit_handle": [u32(b, act + 0x10), u32(b, act + 0x14)],
        "province_size": psz,
        "province0": p0,
        "path_size": u32(b, act + 0x3C),
        "clear": u8(b, act + 0x50),
        "safe": u8(b, act + 0x51),
        "move_priority": u32(b, act + 0x58),
        "word18": u32(b, p + 0x18),
        "word1c": u32(b, p + 0x1C),
        "action_vt_rva": hex(u64(b, act) - base) if True else None,
        "rtti": rtti(b, base, p),
    }


def dump_move_action(b, base, p):
    try:
        arr = u64(b, p + 0x18)
        psz = u32(b, p + 0x24)
        p0 = u32(b, arr) if arr and psz else None
    except Exception:
        p0, psz = None, None
    return {
        "unit_handle": [u32(b, p + 0x10), u32(b, p + 0x14)],
        "province_size": psz,
        "province0": p0,
        "path_size": u32(b, p + 0x3C),
        "clear": u8(b, p + 0x50),
        "safe": u8(b, p + 0x51),
        "move_priority": u32(b, p + 0x58),
        "rtti": rtti(b, base, p),
    }


def dump_strat_action(b, base, p):
    return {
        "army_handle": [u32(b, p + 0x10), u32(b, p + 0x14)],
        "province": u32(b, p + 0x18),
        "clear": u8(b, p + 0x1C),
        "move_priority": u32(b, p + 0x20),
        "rtti": rtti(b, base, p),
    }


def scan_heap(b, base, max_hits=60):
    """Scan rw private/mapped regions for target VTs as object headers."""
    image_lo, image_hi = base, base + int(getattr(b, "image_size", 0x4000000) or 0x4000000)
    needles = {name: struct.pack("<Q", base + rva) for rva, name in TARGETS.items()}
    hits = []
    scanned = 0
    nreg = 0
    for m in b.maps:
        perms = m.get("perms", "")
        if "r" not in perms:
            continue
        # skip pure image for speed (vtable definitions live there — noise)
        typ = m.get("type", 0)
        start, end = m["start"], m["end"]
        if start >= image_lo and end <= image_hi:
            continue
        # prefer writable heap
        if "w" not in perms and typ == 0x1000000:
            continue
        size = end - start
        if size <= 0 or size > 256 * 1024 * 1024:
            continue
        nreg += 1
        # chunk
        chunk = 4 * 1024 * 1024
        for off0 in range(0, size, chunk):
            if len(hits) >= max_hits:
                break
            cs = start + off0
            cl = min(chunk, size - off0)
            try:
                blob = b.read(cs, cl)
            except Exception:
                continue
            scanned += cl
            for rva, name in TARGETS.items():
                needle = needles[name]
                off = 0
                while True:
                    i = blob.find(needle, off)
                    if i < 0:
                        break
                    if i % 8 == 0:
                        p = cs + i
                        entry = {"addr": hex(p), "name": name, "vt_rva": hex(rva)}
                        try:
                            if name == "CMoveCommand":
                                entry["fields"] = dump_move_cmd(b, base, p)
                            elif name == "CUnitMoveAction":
                                entry["fields"] = dump_move_action(b, base, p)
                            elif name == "CUnitStrategicMoveAction":
                                entry["fields"] = dump_strat_action(b, base, p)
                            elif name == "CStrategicRedeploymentCommand":
                                act = p + 0x28
                                entry["fields"] = {
                                    "action_vt": hex(u64(b, act) - base),
                                    **dump_strat_action(b, base, act),
                                    "rtti_cmd": rtti(b, base, p),
                                }
                            else:
                                entry["rtti"] = rtti(b, base, p)
                        except Exception as e:
                            entry["err"] = str(e)
                        hits.append(entry)
                        if len(hits) >= max_hits:
                            break
                    off = i + 8
            if len(hits) >= max_hits:
                break
        if len(hits) >= max_hits:
            break
    return hits, scanned, nreg


def focus_and_click_move():
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_cb(h, _):
        if user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            t = buf.value
            if t and ("Heart" in t or "hoi4" in t.lower() or "Clausewitz" in t):
                found.append((h, t))
        return True

    user32.EnumWindows(enum_cb, 0)
    hwnd = user32.FindWindowW(None, "Hearts of Iron IV")
    title = "Hearts of Iron IV"
    if not hwnd and found:
        hwnd, title = found[0]
    info = {"hwnd": int(hwnd) if hwnd else None, "title": title if hwnd else None, "found": found[:5], "steps": []}
    if not hwnd:
        return info

    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)

    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    rc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    # try several map points — Haiti islands are small; click mid-client variants
    pts_client = [
        (rc.r // 2, rc.b // 2),
        (rc.r // 2 - 60, rc.b // 2 - 40),
        (rc.r // 2 + 30, rc.b // 2 + 20),
        (int(rc.r * 0.45), int(rc.b * 0.55)),
    ]
    screen_pts = []
    for x, y in pts_client:
        pt = POINT(x, y)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        screen_pts.append((pt.x, pt.y))
    info["client"] = {"w": rc.r, "h": rc.b, "screen_pts": screen_pts}

    INPUT_MOUSE = 0

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

    def click(x, y, right=False):
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        ax = int(x * 65535 / max(sw, 1))
        ay = int(y * 65535 / max(sh, 1))
        down = 0x0008 if right else 0x0002
        up = 0x0010 if right else 0x0004
        for fl in (0x0001 | 0x8000, down | 0x8000, up | 0x8000):
            inp = INPUT(type=INPUT_MOUSE)
            inp.mi = MOUSEINPUT(ax, ay, 0, fl, 0, None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.04)

    # Space unpause
    user32.keybd_event(0x20, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x20, 0, 2, 0)
    info["steps"].append("space_unpause")
    time.sleep(0.35)

    # left-click several spots to select a unit, then right-click a neighbor
    for i, (x, y) in enumerate(screen_pts[:3]):
        click(x, y, right=False)
        info["steps"].append(f"lclick_{i}:{x},{y}")
        time.sleep(0.15)
    rx, ry = screen_pts[-1][0] + 90, screen_pts[-1][1] + 50
    click(rx, ry, right=True)
    info["steps"].append(f"rclick:{rx},{ry}")
    time.sleep(0.6)

    # re-pause
    user32.keybd_event(0x20, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x20, 0, 2, 0)
    info["steps"].append("space_pause")
    return info


def poll_lists(b, base, session, server, rounds=300, sleep_s=0.004):
    captures, seen = [], {}
    for i in range(rounds):
        for label, head in (
            ("pending", u64(b, server + 0x58)),
            ("execlist", u64(b, server + 0x40)),
            ("postexec", u64(b, session + 0xF8)),
        ):
            node, guard = head, 0
            while node and guard < 16:
                guard += 1
                try:
                    cmd = u64(b, node)
                    vt = u64(b, cmd) - base
                    name = TARGETS.get(vt, "?")
                    seen[name] = seen.get(name, 0) + 1
                    if name != "?":
                        captures.append({"src": label, "i": i, "cmd": hex(cmd), "name": name})
                    node = u64(b, node + 0x10)
                except Exception:
                    break
        sc = u32(b, session + 0x54)
        if sc:
            data = u64(b, session + 0x48)
            for j in range(min(sc, 16)):
                try:
                    cmd = u64(b, data + j * 8)
                    vt = u64(b, cmd) - base
                    name = TARGETS.get(vt, "?")
                    seen[name] = seen.get(name, 0) + 1
                    if name != "?":
                        captures.append({"src": "stage", "i": i, "cmd": hex(cmd), "name": name})
                except Exception:
                    pass
        try:
            cnt = u64(b, server + 0xC8)
            if cnt and cnt < 64:
                seen["ring_nonzero"] = seen.get("ring_nonzero", 0) + 1
                buf = u64(b, server + 0xB0)
                for j in range(int(cnt)):
                    for stride in (8, 16):
                        try:
                            p = u64(b, buf + j * stride)
                            vt = u64(b, p) - base
                            name = TARGETS.get(vt)
                            if name:
                                captures.append({"src": f"ring_s{stride}", "i": i, "cmd": hex(p), "name": name})
                                break
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(sleep_s)
    return captures, seen


def main():
    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    idler = u64(b, base + OV["G_IDLER"])
    session = u64(b, u64(b, idler + 0x530) + 0x380)
    server = u64(b, session + 0x40)

    report = {
        "phase": "2bd",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": b.pid,
    }

    print("heap scan before...", flush=True)
    t0 = time.time()
    before, scanned, nreg = scan_heap(b, base, max_hits=80)
    report["heap_before"] = {
        "hits": before,
        "scanned_bytes": scanned,
        "regions": nreg,
        "elapsed_s": round(time.time() - t0, 2),
        "by_name": {},
    }
    for h in before:
        report["heap_before"]["by_name"][h["name"]] = report["heap_before"]["by_name"].get(h["name"], 0) + 1
    print("before", report["heap_before"]["by_name"], "scanned", scanned, "regs", nreg, flush=True)

    do_ui = "--ui" in sys.argv
    if do_ui:
        print("UI move attempt...", flush=True)
        report["ui"] = focus_and_click_move()
        caps, seen = poll_lists(b, base, session, server, rounds=250)
        report["poll_after_ui"] = {"captures": caps[:40], "seen": seen, "n": len(caps)}
    else:
        report["ui"] = {"skipped": True}

    print("heap scan after...", flush=True)
    t1 = time.time()
    after, scanned2, nreg2 = scan_heap(b, base, max_hits=80)
    report["heap_after"] = {
        "hits": after,
        "scanned_bytes": scanned2,
        "regions": nreg2,
        "elapsed_s": round(time.time() - t1, 2),
        "by_name": {},
    }
    for h in after:
        report["heap_after"]["by_name"][h["name"]] = report["heap_after"]["by_name"].get(h["name"], 0) + 1

    report["caught_move_cmd"] = any(h["name"] == "CMoveCommand" for h in before + after)
    report["caught_move_action"] = any(h["name"] == "CUnitMoveAction" for h in before + after)
    report["caught_strategic"] = any(
        h["name"] in ("CStrategicRedeploymentCommand", "CUnitStrategicMoveAction") for h in before + after
    )
    report["final"] = {
        "drain": u32(b, session + 0x60),
        "exec": u32(b, session + 0x6C8),
        "seq": u32(b, server + 0xD0),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    slim = {k: report[k] for k in report if k not in ("heap_before", "heap_after")}
    slim["heap_before_by_name"] = report["heap_before"]["by_name"]
    slim["heap_after_by_name"] = report["heap_after"]["by_name"]
    slim["heap_before_meta"] = {k: report["heap_before"][k] for k in ("scanned_bytes", "regions", "elapsed_s")}
    slim["heap_after_meta"] = {k: report["heap_after"][k] for k in ("scanned_bytes", "regions", "elapsed_s")}
    slim["heap_before_sample"] = report["heap_before"]["hits"][:10]
    slim["heap_after_sample"] = report["heap_after"]["hits"][:10]
    print(json.dumps(slim, indent=2)[:16000])
    print("wrote", OUT)
    b.close()


if __name__ == "__main__":
    main()
