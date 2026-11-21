import struct, json
from pathlib import Path
import sys
sys.path.insert(0, "calling")
import offsets as O

base = Path("research/_t133_speed_baseline_gamestate.bin").read_bytes()
aft = Path("research/_t134_speed_after_gamestate.bin").read_bytes()

def row(off):
    return {
        "off": hex(off),
        "base_i32": struct.unpack_from("<i", base, off)[0],
        "after_i32": struct.unpack_from("<i", aft, off)[0],
        "base_u32": struct.unpack_from("<I", base, off)[0],
        "after_u32": struct.unpack_from("<I", aft, off)[0],
        "base_f32": struct.unpack_from("<f", base, off)[0],
        "after_f32": struct.unpack_from("<f", aft, off)[0],
    }

# neighbors around 0x4bc, and all known GS offsets
known = {v: k for k, v in O.HYPOTHESIS_STRUCT.items() if isinstance(v, int) and 0x400 <= v <= 0x550}
print("KNOWN NEAR 0x400-0x550:")
for off, name in sorted(known.items()):
    print(f"  {name} = {hex(off)}")

print("\nWINDOW 0x490-0x4E0:")
for off in range(0x490, 0x4E0, 4):
    r = row(off)
    mark = " <<<" if r["base_i32"] != r["after_i32"] else ""
    kn = known.get(off, "")
    print(f"  {r['off']} {kn:30s} i32 {r['base_i32']} -> {r['after_i32']}  u32 {r['base_u32']} -> {r['after_u32']}{mark}")

# also list HYPOTHESIS keys containing SPEED/PAUSE/DATE
print("\nSPEED/PAUSE/DATE KEYS:")
for k, v in O.HYPOTHESIS_STRUCT.items():
    if any(s in k.upper() for s in ("SPEED", "PAUSE", "DATE", "HOUR", "TIME", "TICK")):
        print(f"  {k}={v if not isinstance(v,int) else hex(v)}")
