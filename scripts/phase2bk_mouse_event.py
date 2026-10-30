"""Phase 2bk: SetCursorPos + mouse_event (legacy) for DX11 HOI4. Stay paused. RO observe."""
from __future__ import annotations
import json, struct, sys, time, ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bk_mouse_event.json"


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def main():
    user32 = ctypes.windll.user32
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    base = p.base
    idler = u64(p, base + OV["G_IDLER"])
    session = u64(p, u64(p, idler + 0x530) + 0x380)
    server = u64(p, session + 0x40)
    hwnd = user32.FindWindowW(None, "Hearts of Iron IV (DirectX 11)")
    before = {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)}
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)

    def click(x, y, right=False):
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)
        if right:
            user32.mouse_event(0x0008, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(0x0010, 0, 0, 0, 0)
        else:
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.12)

    steps = []
    for x, y in ((847, 630), (820, 610), (800, 600)):
        click(x, y, False)
        steps.append(f"L:{x},{y}")
    for x, y in ((760, 590), (780, 600), (900, 630), (770, 580)):
        click(x, y, True)
        steps.append(f"R:{x},{y}")
        if u32(p, server + 0xD0) != before["seq"] or u32(p, session + 0x6C8) != before["exec"]:
            steps.append("counter_changed")
            break
    time.sleep(0.4)
    after = {"drain": u32(p, session + 0x60), "exec": u32(p, session + 0x6C8), "seq": u32(p, server + 0xD0)}

    needles = {
        "CMoveCommand": struct.pack("<Q", base + 0x2A2C790),
        "CUnitMoveAction": struct.pack("<Q", base + 0x2A1F648),
        "CStrategicRedeploymentCommand": struct.pack("<Q", base + 0x2A2D818),
        "CUnitStrategicMoveAction": struct.pack("<Q", base + 0x2A1F7E8),
    }
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
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
                            if len(samples[k]) < 3:
                                samples[k].append(hex(pos + i))
                        off = i + 8
            pos += n
        if sum(counts.values()) >= 1:
            break

    report = {
        "phase": "2bk",
        "posting": "DISABLED",
        "speed_rule": "stay paused; never 5x",
        "pid": pid,
        "before": before,
        "after": after,
        "delta": {k: after[k] - before[k] for k in before},
        "steps": steps,
        "heap": {"scanned_mb": scanned >> 20, "counts": {k: v for k, v in counts.items() if v}, "samples": samples},
        "caught_any": sum(counts.values()) > 0 or after["seq"] != before["seq"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:8000])
    print("wrote", OUT)
    p.close()
    return 0 if report["caught_any"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
