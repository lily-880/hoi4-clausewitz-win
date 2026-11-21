import sys
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
raw=pe.read_rva(0xcc6480, 0x40) or b""
lines=[]
for i in cs.disasm(raw, 0xcc6480):
    lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if i.mnemonic=="ret":
        break
Path("research/_t190_clip_cc6480.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
