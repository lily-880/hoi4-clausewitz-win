import os, sys, struct, time, json
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])

def f32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<f", b, 0)[0] if b else None
def u32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<I", b, 0)[0] if b else None
def i32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<i", b, 0)[0] if b else None

# reinterpret saved words
def fu(u):
    return struct.unpack("<f", struct.pack("<I", u))[0]

saved = {
    "after1_u32": 1052877882,
    "after2_u32": 1061667257,
}
s1, s2 = fu(1052877882), fu(1061667257)
v1 = f32(gs + 0x4B8)
t1 = u32(gs + 0x468)
sp = i32(gs + 0x4BC)
time.sleep(1.0)
v2 = f32(gs + 0x4B8)
t2 = u32(gs + 0x468)
sp2 = i32(gs + 0x4BC)
out = {
    "saved_after1_f32": s1,
    "saved_after2_f32": s2,
    "saved_delta_0.8s": s2 - s1,
    "saved_per_sec": (s2 - s1) / 0.8,
    "live1_f32": v1,
    "live2_f32_after_1.0s": v2,
    "live_delta_1s": None if v1 is None or v2 is None else v2 - v1,
    "speed_index": sp,
    "speed_index2": sp2,
    "hour_tick1": t1,
    "hour_tick2": t2,
}
print(json.dumps(out, indent=2))
p.close()
