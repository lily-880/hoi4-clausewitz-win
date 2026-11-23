#!/usr/bin/env python3
"""Minimal UI control of the HOI4 window only (user delegated, 2026-11-23).

  shot [--out PATH] [--scale S]   capture ONLY the game window's client area
  click X Y [--right]             click at client coordinates (as in a shot at scale 1)
  key NAME                        press a key in the game window (space, esc, enter, f1...)
  launch [--save NAME]            start the game to the main menu, or straight into a save

Used for things outside the commander's own command path: choosing the 1939
bookmark, the one declare-war click, saving/loading the benchmark start.
Screenshots use PrintWindow on the game window itself (never a screen region);
input is refused unless the game window is really in front.
"""
from __future__ import annotations

import argparse
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "claude_live" / "ui"
EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"

user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
except OSError:
    user32.SetProcessDPIAware()


def find_window() -> int:
    import subprocess as sp
    pid = None
    out = sp.run(["tasklist", "/FI", "IMAGENAME eq hoi4.exe", "/FO", "CSV", "/NH"],
                 capture_output=True, text=True).stdout.strip().splitlines()
    for line in out:
        parts = [p.strip('"') for p in line.split('","')]
        if parts and parts[0].lower() == "hoi4.exe":
            pid = int(parts[1])
    if not pid:
        raise SystemExit("HOI4 is not running")
    found = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        owner = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            r = wt.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(r))
            found.append((r.right * r.bottom, hwnd))
        return True

    user32.EnumWindows(proc(cb), 0)
    if not found:
        raise SystemExit("no visible HOI4 window")
    return max(found)[1]


def client_rect(hwnd: int) -> tuple[int, int, int, int]:
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    pt = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, pt.x + r.right, pt.y + r.bottom


def focus(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)


def _window_image(hwnd: int):
    """The game window's OWN pixels via PrintWindow (PW_RENDERFULLCONTENT), never
    the screen region: a covering window can never end up in the picture."""
    from PIL import Image

    gdi32 = ctypes.WinDLL("gdi32")
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    hdc = user32.GetDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    ok = user32.PrintWindow(hwnd, mem, 0x1 | 0x2)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                    ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                    ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]

    bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    if not ok:
        raise SystemExit("PrintWindow failed; refusing to fall back to a screen grab")
    return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")


def _require_foreground(hwnd: int) -> None:
    focus(hwnd)
    if user32.GetForegroundWindow() != hwnd:
        raise SystemExit("game window is not in front; refusing to send input")


def shot(out: Path | None = None, scale: float = 0.5) -> Path:
    hwnd = find_window()
    img = _window_image(hwnd)
    if scale != 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    OUT.mkdir(parents=True, exist_ok=True)
    out = out or OUT / time.strftime("shot_%H%M%S.png")
    img.save(out)
    print(f"{out}  size={img.width}x{img.height}  scale={scale}")
    return out


class _MI(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _KI(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", _MI), ("ki", _KI), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def _send(inp: _INPUT) -> None:
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def click(x: int, y: int, right: bool = False) -> None:
    hwnd = find_window()
    _require_foreground(hwnd)
    left, top, _, _ = client_rect(hwnd)
    user32.SetCursorPos(left + int(x), top + int(y))
    time.sleep(0.15)
    down, up = (0x0008, 0x0010) if right else (0x0002, 0x0004)
    for flag in (down, up):
        i = _INPUT(type=0)
        i.mi = _MI(0, 0, 0, flag, 0, 0)
        _send(i)
        time.sleep(0.08)


SCANS = {"space": 0x39, "esc": 0x01, "enter": 0x1C, "f1": 0x3B, "f2": 0x3C, "tab": 0x0F,
         "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "q": 0x10, "w": 0x11}


def key(name: str) -> None:
    hwnd = find_window()
    _require_foreground(hwnd)
    scan = SCANS[name.lower()]
    for flags in (0x0008, 0x0008 | 0x0002):
        i = _INPUT(type=1)
        i.ki = _KI(0, scan, flags, 0, 0)
        _send(i)
        time.sleep(0.08)


def launch(save: str | None = None) -> None:
    subprocess.run(["taskkill", "/F", "/IM", "hoi4.exe"], capture_output=True)
    time.sleep(3)
    argv = [EXE, "-gdpr-compliant"]
    if save:
        argv.append(f"-start_save={save}")
    subprocess.Popen(argv, cwd=str(Path(EXE).parent), close_fds=True)
    print("launched:", " ".join(argv[1:]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shot")
    s.add_argument("--out", type=Path)
    s.add_argument("--scale", type=float, default=0.5)
    c = sub.add_parser("click")
    c.add_argument("x", type=float)
    c.add_argument("y", type=float)
    c.add_argument("--right", action="store_true")
    k = sub.add_parser("key")
    k.add_argument("name")
    l = sub.add_parser("launch")
    l.add_argument("--save")
    a = ap.parse_args(argv)
    if a.cmd == "shot":
        shot(a.out, a.scale)
    elif a.cmd == "click":
        click(a.x, a.y, a.right)
    elif a.cmd == "key":
        key(a.name)
    else:
        launch(a.save)
    return 0


if __name__ == "__main__":
    sys.exit(main())
