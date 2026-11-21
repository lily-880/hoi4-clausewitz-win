from __future__ import annotations
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import struct, sys
sys.path.insert(0, "calling")
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail = False

def read_rva(rva, n):
    off = pe.rva_to_off(rva)
    return pe.data[off:off+n]

# parse pdata (exception dir)
# IMAGE_DIRECTORY_ENTRY_EXCEPTION = 3
# PE already may have it; scan .pdata section
pdata = None
for s in pe.sections:
    if s.name.startswith(".pdata") or "pdata" in s.name:
        pdata = s
        print("pdata section", s.name, hex(s.virtual_address), s.virtual_size)
if pdata is None:
    # dump section names
    print("sections", [(s.name, hex(s.virtual_address), s.virtual_size) for s in pe.sections])

def find_fn(rva):
    if pdata is None:
        return None
    raw = pe.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size]
    # RUNTIME_FUNCTION: begin, end, unwind (3 dwords)
    n = len(raw)//12
    # binary search
    lo, hi = 0, n-1
    while lo <= hi:
        mid = (lo+hi)//2
        b,e,u = struct.unpack_from("<III", raw, mid*12)
        if rva < b:
            hi = mid-1
        elif rva >= e:
            lo = mid+1
        else:
            return b,e,u
    return None

for rva in (0xC7E8C0, 0xC4D030, 0x18DB330, 0xC417A0):
    fn = find_fn(rva)
    print("FN", hex(rva), "pdata", None if not fn else (hex(fn[0]), hex(fn[1]), fn[1]-fn[0]))

# full CArmyLeader writer
fn = find_fn(0xC7E8C0)
start, end = (fn[0], fn[1]) if fn else (0xC7E8C0, 0xC7E8C0+0x800)
n = end-start
full = [f"{hex(i.address)}  {i.mnemonic} {i.op_str}" for i in cs.disasm(read_rva(start, n), start)]
Path("research/_t192_clip_CArmyLeader_writer_full.txt").write_text("\n".join(full)+"\n", encoding="utf-8")
print("leader writer ins", len(full), "bytes", n)
# hits for 1048/handle/token
for ln in full:
    if any(s in ln.lower() for s in ["0x1048", "0x1068", "0x1058", "0x1040", "0x41c7", "0x385b", "0x30ae", "lea r8", "mov edx"]):
        print("LH", ln)

# COrdersGroup member loop window
print("\n======= COrdersGroup members/leader window =====")
window = [f"{hex(i.address)}  {i.mnemonic} {i.op_str}" for i in cs.disasm(read_rva(0xC4D270, 0x200), 0xC4D270)]
Path("research/_t192_clip_COrdersGroup_members.txt").write_text("\n".join(window)+"\n", encoding="utf-8")
for ln in window:
    print(ln)
