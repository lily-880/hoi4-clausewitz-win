from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import sys
sys.path.insert(0,"calling")
from pe import PE
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
# disasm a solid window ending at the switch
start=0xfca100
blob=pe.data[pe.rva_to_off(start):pe.rva_to_off(0xfca1b0)]
for i in cs.disasm(blob, start):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
