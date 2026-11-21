from __future__ import annotations
import struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe=PE(EXE)
cs=Cs(CS_ARCH_X86, CS_MODE_64)

def read_rva(rva,n):
    return pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n]

def find_fn(rva):
    pdata=next(s for s in pe.sections if s.name.startswith(".pdata"))
    raw=pe.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size]
    n=len(raw)//12
    lo,hi=0,n-1
    while lo<=hi:
        mid=(lo+hi)//2
        b,e,u=struct.unpack_from("<III", raw, mid*12)
        if rva<b: hi=mid-1
        elif rva>=e: lo=mid+1
        else: return b,e
    return None

fn=find_fn(0xc402a0)
print("c402a0 pdata", None if not fn else (hex(fn[0]), hex(fn[1]), fn[1]-fn[0]))
start,end = (fn[0], fn[1]) if fn else (0xc402a0, 0xc402a0+0x200)
lines=[]
for i in cs.disasm(read_rva(start, end-start), start):
    lines.append(f"{hex(i.address)}  {i.mnemonic} {i.op_str}")
Path("research/_t193_clip_c402a0.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("ins", len(lines))
for l in lines[:120]:
    print(l)

# also bind NewRoot factory 4096 quickly from table in comments; disasm later if needed
print("\n===== search attach in army_subjects / docs =====")
