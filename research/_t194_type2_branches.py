from __future__ import annotations
import struct, sys, re, json
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE

pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs = Cs(CS_ARCH_X86, CS_MODE_64)

def find_fn(rva):
    pdata=next(s for s in pe.sections if s.name.startswith(".pdata"))
    praw=pe.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size]
    n=len(praw)//12
    lo,hi=0,n-1
    while lo<=hi:
        mid=(lo+hi)//2
        b,e,u=struct.unpack_from("<III", praw, mid*12)
        if rva<b: hi=mid-1
        elif rva>=e: lo=mid+1
        else: return b,e
    return None

def disasm(rva, n):
    return list(cs.disasm(pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n], rva))

def cstr(rva, n=80):
    b = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n]
    if b"\x00" in b:
        b=b.split(b"\x00",1)[0]
    try:
        return b.decode("latin1")
    except Exception:
        return None

def rip_strings_from_ins(ins):
    out=[]
    for i in ins:
        if i.mnemonic in ("lea","mov") and "rip" in i.op_str:
            m=re.search(r"rip ([\+\-]) 0x([0-9a-f]+)", i.op_str)
            if not m: continue
            disp=int(m.group(2),16)
            tgt=i.address+i.size+(disp if m.group(1)=="+" else -disp)
            try:
                s=cstr(tgt)
            except Exception:
                continue
            if s and len(s)>=3 and all(32<=ord(c)<127 or c in "\t\n\r" for c in s):
                out.append((hex(i.address), hex(tgt), s))
    return out

fn=find_fn(0xfcc818)
print("fn", hex(fn[0]), hex(fn[1]), fn[1]-fn[0])

# Only disasm a window just before the table and the switch
# Look for lea/jmp involving the table first by scanning 0x200 bytes before 0xfcc818
print("\n======= window 0xfcc600-0xfcc900 =======")
for i in disasm(0xfcc600, 0x300):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")

print("\n======= type2 mode branches (strings + head) =======")
for label,rva in [("mode0",0xfca5dc),("mode1",0xfca472),("mode2",0xfca232)]:
    ins=disasm(rva, 0x180)
    strs=rip_strings_from_ins(ins)
    print(f"\n--- {label} {hex(rva)} ---")
    for s in strs:
        print(" STR", s)
    for i in ins[:18]:
        print(f"  0x{i.address:x}  {i.mnemonic} {i.op_str}")

# Also find where type is loaded for this switch: search backwards from first use of table
# We'll also look at function start for GetOrderType / [reg+0x30]
print("\n======= function start =======")
for i in disasm(fn[0], 0x80):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
