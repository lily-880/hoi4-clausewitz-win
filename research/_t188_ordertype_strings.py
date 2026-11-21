import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
# dump strings around 0x2aa1598
def cstr(va, n=64):
    b=pe.read_rva(va, n) or b""
    if b"\x00" in b: b=b.split(b"\x00",1)[0]
    return b.decode("latin1","replace")

print("=== nearby strings around frontline 0x2aa1598 ===")
# walk back and forward for packed cstrings
blob=pe.read_rva(0x2aa1400, 0x800) or b""
off=0
base=0x2aa1400
while off < len(blob):
    if blob[off]==0:
        off+=1; continue
    if 32<=blob[off]<127:
        a=off
        while off<len(blob) and 32<=blob[off]<127:
            off+=1
        s=blob[a:off].decode("latin1")
        if len(s)>=3:
            print(f"  0x{base+a:x} {s}")
    else:
        off+=1

# ORDER_ strings more complete
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
print("\n=== ORDER_ / FrontLine / Offensive type strings ===")
for m in re.finditer(rb"ORDER_[A-Z0-9_]+", rblob):
    s=m.group().decode()
    va=rdata.virtual_address+m.start()
    # expand
    a=m.start()
    while a>0 and 32<=rblob[a-1]<127: a-=1
    b=m.end()
    while b<len(rblob) and 32<=rblob[b]<127: b+=1
    full=rblob[a:b].decode("latin1")
    if any(k in full.upper() for k in ("FRONT","OFFENS","FALLBACK","GARRIS","AREA","INVAS","PARA","MOVE","ATTACK","SPEAR","DEFEN")):
        print(f"  0x{rdata.virtual_address+a:x} {full[:200]}")

print("\n=== GetOrderType nearby asserts / names ===")
# already have 0x2a86ef0
for va in (0x2a86ef0, 0x2a03830):
    print(va, cstr(va, 200))
