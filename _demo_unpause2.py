import ctypes, time, json, struct, sys
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

user32 = ctypes.windll.user32
VK_SPACE = 0x20
KEYEVENTF_KEYUP = 0x0002

pid = find_pid("hoi4.exe")
hwnd = user32.FindWindowW(None, "Hearts of Iron IV (DirectX 11)")
print("fg_before", int(user32.GetForegroundWindow()), "hwnd", int(hwnd))

# force foreground more aggressively
user32.ShowWindow(hwnd, 9)  # SW_RESTORE
user32.BringWindowToTop(hwnd)
# AllowSetForegroundWindow
try:
    ctypes.windll.user32.AllowSetForegroundWindow(pid)
except Exception:
    pass
user32.SetForegroundWindow(hwnd)
time.sleep(0.4)
print("fg_mid", int(user32.GetForegroundWindow()))

# click client center to ensure map has focus (dismiss popups)
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
rect = ctypes.wintypes.RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
pt = POINT((rect.right)//2, (rect.bottom)//2)
user32.ClientToScreen(hwnd, ctypes.byref(pt))
user32.SetCursorPos(pt.x, pt.y)
user32.mouse_event(0x0002, 0, 0, 0, 0)  # left down
time.sleep(0.05)
user32.mouse_event(0x0004, 0, 0, 0, 0)  # left up
time.sleep(0.3)

# Space while focused
user32.keybd_event(VK_SPACE, 0, 0, 0)
time.sleep(0.08)
user32.keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, 0)
print("SPACE sent; fg", int(user32.GetForegroundWindow()))

p = Proc(pid)
OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
base = p.base
gs = struct.unpack("<Q", p.read(base + (OV["G_GAMESTATE"] if isinstance(OV["G_GAMESTATE"], int) else OV["G_GAMESTATE"]["rva"]), 8))[0]

def readdate():
    return (
        struct.unpack("<I", p.read(gs + 0x478, 4))[0],
        struct.unpack("<I", p.read(gs + 0x484, 4))[0],
        struct.unpack("<I", p.read(gs + 0x518, 4))[0],
    )

# also scan nearby for changing counters over 6s (pause/speed candidates)
y1,d1,t1 = readdate()
print("start", y1,d1,"tag",t1)
# sample a few known-ish fields
samples = {}
for off in range(0x450, 0x520, 4):
    samples[off] = struct.unpack("<I", p.read(gs + off, 4))[0]
time.sleep(6)
y2,d2,t2 = readdate()
changed = []
for off in range(0x450, 0x520, 4):
    v = struct.unpack("<I", p.read(gs + off, 4))[0]
    if v != samples[off]:
        changed.append((hex(off), samples[off], v))
print("after6s", y2,d2, "moved", (y2,d2)!=(y1,d1), "changed_fields", changed[:20])
