from __future__ import annotations
import struct, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE

pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs = Cs(CS_ARCH_X86, CS_MODE_64)

fn_start, fn_end = 0xfc9880, 0xfcc818
raw = pe.data[pe.rva_to_off(fn_start):pe.rva_to_off(fn_end)]

# find 0xfcc818 as 32-bit immediate / disp
pat = struct.pack("<I", 0xfcc818)
idx = 0
print("immediate 0xfcc818 in function:")
while True:
    j = raw.find(pat, idx)
    if j < 0:
        break
    print("  at", hex(fn_start+j))
    idx = j+1

# also scan lea/rip that land on table: for each 7-byte lea, check target
print("\nlea-rip to table / type loads:")
ins = list(cs.disasm(raw, fn_start))
for i in ins:
    if "0xfcc818" in i.op_str or "0xfcc81" in i.op_str:
        print(f"  HIT 0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if i.mnemonic in ("lea","mov","jmp","call") and "rip" in i.op_str:
        m=re.search(r"rip ([\+\-]) 0x([0-9a-f]+)", i.op_str)
        if m:
            disp=int(m.group(2),16)
            tgt=i.address+i.size+(disp if m.group(1)=="+" else -disp)
            if 0xfcc818 <= tgt <= 0xfcc848:
                print(f"  RIP 0x{i.address:x}  {i.mnemonic} {i.op_str} -> {hex(tgt)}")
    # type-like
    if "+ 0x30]" in i.op_str or "+ 0x30]" in i.op_str:
        # print nearby context later
        if i.mnemonic in ("cmp","mov","movzx") or "0x30" in i.op_str:
            pass

# print all cmp/mov involving 0x30 in this function
print("\ninsns mentioning 0x30 in tooltip fn (filtered):")
for i in ins:
    if "0x30" in i.op_str and i.mnemonic in ("cmp","mov","lea","add","sub","movsxd","movsx","movzx"):
        print(f"  0x{i.address:x}  {i.mnemonic} {i.op_str}")

# find switch: look for jmp rax / jmp qword after movsxd around mid function
print("\nindirect jmps / movsxd:")
for i in ins:
    if i.mnemonic in ("jmp","call") and i.op_str in ("rax","eax","rcx","rdx","r8","r9","r10","r11"):
        print(f"  0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if i.mnemonic in ("movsxd","cdqe") or "rva" in i.op_str:
        print(f"  0x{i.address:x}  {i.mnemonic} {i.op_str}")

# Search WHOLE .text for disp32/imm32 = 0xfcc818 using raw find (fast)
text=next(s for s in pe.sections if s.name.startswith(".text"))
tblob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
print("\nall .text occurrences of dword 0xfcc818:")
idx=0
hits=[]
while len(hits)<20:
    j=tblob.find(pat, idx)
    if j<0: break
    hits.append(text.virtual_address+j)
    idx=j+1
print([hex(h) for h in hits])
# context 16 bytes before each, disasm 8 insns around
for h in hits:
    start=h-16
    blob=pe.data[pe.rva_to_off(start):pe.rva_to_off(h)+16]
    print("---", hex(h))
    for i in cs.disasm(blob, start):
        print(f"  0x{i.address:x}  {i.mnemonic} {i.op_str}")
