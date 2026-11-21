from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import sys
sys.path.insert(0,"calling")
from pe import PE
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)

def dump(rva, n, title):
    print("\n=======", title, hex(rva), "=======")
    blob=pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n]
    for i in cs.disasm(blob, rva):
        print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if i.mnemonic=="ret" and i.address>rva+0x10:
            break

dump(0x18decf0, 0x30, "Assign IsValid tail 0x18decfe")
# Assign execute
dump(0x18d4220, 0x120, "Assign Execute")
# 0x10cd510 execute-instance
dump(0x10cd510, 0x180, "instance execute 0x10cd510")
# pause setter head
dump(0xe487f0, 0x80, "idler setpause 0xe487f0")
