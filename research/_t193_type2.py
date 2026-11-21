from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import struct, sys
sys.path.insert(0,"calling")
from pe import PE

# writer clip tokens
p=Path("research/_t188_clip_orderinstance_writer_0x10d1450.txt")
if p.exists():
    lines=p.read_text(encoding="utf-8").splitlines()
    print("writer clip lines", len(lines))
    for l in lines:
        if any(s in l.lower() for s in ("0xe1","0x30af","0x174","0x2e3b","0x30b2","0x258","0x70","0xe0","midpoint","edx, 0x","0x268")):
            print(l)
else:
    print("missing writer clip")

# search .text for cmp [r?x+0x30], 2 around 0x10b0000-0x10d0000? too broad
# search bytes: 83 7? 30 02  (cmp dword [reg+0x30], 2)
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
text=next(s for s in pe.sections if s.name.startswith(".text"))
chunk=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
# cmp dword ptr [reg+0x30], 2 encodings: 83 78 30 02, 83 79 30 02, 83 7a 30 02, 83 7b 30 02, 83 7e 30 02, 83 7f 30 02, 83 7d 30 02
pats=[bytes([0x83, r, 0x30, 0x02]) for r in (0x78,0x79,0x7a,0x7b,0x7d,0x7e,0x7f)]
# also 83 b8/b9/... 30 00 00 00 02
hits=[]
for pat in pats:
    start=0
    while True:
        i=chunk.find(pat, start)
        if i<0: break
        rva=text.virtual_address+i
        hits.append(rva)
        start=i+1
print("cmp +0x30,2 count", len(hits), "first", [hex(h) for h in hits[:20]])

# disasm 16 bytes around first 12 in 0x10xxxx range (order code)
orderish=[h for h in hits if 0x1000000 <= h <= 0x1200000]
print("in 0x10-0x12M", len(orderish), [hex(h) for h in orderish[:25]])
for h in orderish[:15]:
    blob=pe.data[pe.rva_to_off(h-8):pe.rva_to_off(h)+24]
    ins=list(cs.disasm(blob, h-8))
    print("---", hex(h))
    for i in ins:
        print(f"  {hex(i.address)}  {i.mnemonic} {i.op_str}")
