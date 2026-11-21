import struct, json
from pathlib import Path
import sys
sys.path.insert(0, "calling")
import offsets as O

OUT = Path("research")
base = {n: (OUT / f"_t137_pause_baseline_{n}.bin").read_bytes() for n in ("gamestate","idler","session","app")}
a1 = {n: (OUT / f"_t138_unpause_{n}.bin").read_bytes() for n in ("gamestate","idler","session","app")}
a2 = {n: (OUT / f"_t138_unpause2_{n}.bin").read_bytes() for n in ("gamestate","idler","session","app")}

def u32(b,o):
    return struct.unpack_from("<I", b, o)[0] if o+4<=len(b) else None
def u64(b,o):
    return struct.unpack_from("<Q", b, o)[0] if o+8<=len(b) else None
def i32(b,o):
    return struct.unpack_from("<i", b, o)[0] if o+4<=len(b) else None

print("=== ticking after1 -> after2 ===")
for name in base:
    for off in range(0, min(len(a1[name]), len(a2[name]))-3, 4):
        if a1[name][off:off+4] != a2[name][off:off+4]:
            print(f"  {name}+{hex(off)} {u32(a1[name],off)} -> {u32(a2[name],off)}  i32 {i32(a1[name],off)}->{i32(a2[name],off)}  u64 {u64(a1[name],off)}->{u64(a2[name],off)}")

print("\n=== GS known offsets near diffs ===")
known = {v:k for k,v in O.HYPOTHESIS_STRUCT.items() if isinstance(v,int)}
for off in (0x260,0x268,0x270,0x274,0x278,0x280,0x41c,0x468,0x4bc,0x620,0x748,0x74c,0x878,0x9b8,0xa00):
    kn = known.get(off, "")
    print(f"  GS+{hex(off)} {kn:30s} base={u32(base['gamestate'],off)} after={u32(a1['gamestate'],off)}")

print("\n=== idler+0x6c0 bytes / flags ===")
for label,b in (("base",base["idler"]),("a1",a1["idler"]),("a2",a2["idler"])):
    off=0x6c0
    print(f"  {label} u32={u32(b,off):#010x} u64={u64(b,off):#018x} bytes={b[off:off+8].hex()}")

print("\n=== byte-level one-shot that are 00<->01 only (single byte) ===")
for name in base:
    n=min(len(base[name]), len(a1[name]), len(a2[name]))
    for off in range(n):
        if base[name][off] != a1[name][off] and a1[name][off] == a2[name][off]:
            if {base[name][off], a1[name][off]} <= {0,1}:
                # check surrounding word
                woff = off & ~3
                print(f"  {name}+{hex(off)} {base[name][off]}->{a1[name][off]}  word@{hex(woff)} {u32(base[name],woff):#x}->{u32(a1[name],woff):#x}")

print("\n=== GS window 0x868-0x890 and 0x9a8-0x9c8 and 0x738-0x760 ===")
for window in (range(0x868,0x890,4), range(0x9a8,0x9c8,4), range(0x738,0x760,4), range(0x610,0x630,4)):
    print(" window", hex(window.start))
    for off in window:
        b,a=u32(base["gamestate"],off),u32(a1["gamestate"],off)
        mark=" <<<" if b!=a else ""
        print(f"   {hex(off)} {b} -> {a}{mark}")
