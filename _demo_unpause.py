import ctypes, time, json, struct, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent if False else Path(".").resolve()
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid

user32 = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK_SPACE = 0x20

pid = find_pid("hoi4.exe")
titles = []
@ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
def enum_cb(h, lp):
    p = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(h, ctypes.byref(p))
    if p.value == pid and user32.IsWindowVisible(h):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(h, buf, 512)
        titles.append((int(h), buf.value))
    return True
user32.EnumWindows(enum_cb, 0)
hwnd = user32.FindWindowW(None, "Hearts of Iron IV (DirectX 11)") or user32.FindWindowW(None, "Hearts of Iron IV")
print("pid", pid, "hwnd", int(hwnd) if hwnd else None, "windows", titles)

def send_vk(h, vk):
    scan = user32.MapVirtualKeyW(vk, 0)
    lp = 1 | (scan << 16)
    user32.PostMessageW(h, WM_KEYDOWN, vk, lp)
    time.sleep(0.05)
    user32.PostMessageW(h, WM_KEYUP, vk, lp | (1 << 30) | (1 << 31))

targets = []
if hwnd:
    targets.append(int(hwnd))
for h, _ in titles:
    if h not in targets:
        targets.append(h)
for h in targets:
    print("PostMessage SPACE", h)
    send_vk(h, VK_SPACE)

# COM activate + SendKeys space
ps = r"""
$w = New-Object -ComObject WScript.Shell
$null = $w.AppActivate('Hearts of Iron IV')
Start-Sleep -Milliseconds 500
$w.SendKeys(' ')
"""
subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=10)
time.sleep(2)

p = Proc(pid)
OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
base = p.base
gs_rva = OV["G_GAMESTATE"] if isinstance(OV["G_GAMESTATE"], int) else OV["G_GAMESTATE"]["rva"]
gs = struct.unpack("<Q", p.read(base + gs_rva, 8))[0]

def readdate():
    year = struct.unpack("<I", p.read(gs + 0x478, 4))[0]
    day = struct.unpack("<I", p.read(gs + 0x484, 4))[0]
    tag = struct.unpack("<I", p.read(gs + 0x518, 4))[0]
    return year, day, tag

y1, d1, t1 = readdate()
print("date1", y1, d1, "tag", t1, "HAI" if t1 == 15 else t1)
time.sleep(5)
y2, d2, t2 = readdate()
print("date2", y2, d2, "moved", (y2, d2) != (y1, d1), "fg", int(user32.GetForegroundWindow()))
