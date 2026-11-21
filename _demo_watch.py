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
user32.SetForegroundWindow(hwnd)
time.sleep(0.25)
# ensure unpaused: send Space once
user32.keybd_event(VK_SPACE, 0, 0, 0); time.sleep(0.08); user32.keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, 0)
print("SPACE for unpause")
p = Proc(pid)
OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
base = p.base
gs = struct.unpack("<Q", p.read(base + (OV["G_GAMESTATE"] if isinstance(OV["G_GAMESTATE"], int) else OV["G_GAMESTATE"]["rva"]), 8))[0]
def snap():
    year = struct.unpack("<I", p.read(gs + 0x478, 4))[0]
    aux = struct.unpack("<I", p.read(gs + 0x47c, 4))[0]
    hour = struct.unpack("<I", p.read(gs + 0x480, 4))[0]
    day = struct.unpack("<I", p.read(gs + 0x484, 4))[0]
    tag = struct.unpack("<I", p.read(gs + 0x518, 4))[0]
    return dict(year=year, aux=aux, hour=hour, day=day, tag=tag)
s0 = snap(); print("t0", s0)
time.sleep(8)
s1 = snap(); print("t8", s1, "changed", s1!=s0)
