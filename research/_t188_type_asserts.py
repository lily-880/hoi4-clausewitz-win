import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
print("=== GetOrderType strings ===")
for m in re.finditer(rb"GetOrderType\(\)[^\x00]{0,80}", rblob):
    va=rdata.virtual_address+m.start()
    print(f"  0x{va:x} {m.group().decode('latin1')}")

# also EOrder / ORDER_MOVE as standalone
print("=== standalone ORDER_* identifiers (short) ===")
for m in re.finditer(rb"\x00(ORDER_[A-Z0-9_]+)\x00", rblob):
    s=m.group(1).decode()
    if s.startswith("ORDER_") and "TOOLTIP" not in s and "MAX_" not in s and "SMOOTH" not in s and "CONFIRM" not in s and "GARRISON_ORDER" not in s:
        print(f"  0x{rdata.virtual_address+m.start()+1:x} {s}")

def clip(start, n=0x60):
    raw=pe.read_rva(start, n) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if i.mnemonic=="ret" and i.address>start+4:
            break
        if len(lines)>25:
            break
    return lines

print("\n======= cmp 2 @ 0x10b2f86 context =====")
print("\n".join(clip(0x10b2f50, 0x80)))
print("\n======= cmp 5 @ 0x10bc7d8 context =====")
print("\n".join(clip(0x10bc7b0, 0x80)))
print("\n======= cmp 4 @ 0x10bc966 context =====")
print("\n".join(clip(0x10bc940, 0x80)))
print("\n======= cmp 2 @ 0x10bb020 context =====")
print("\n".join(clip(0x10bb000, 0x80)))
