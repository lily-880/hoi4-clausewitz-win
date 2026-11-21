from __future__ import annotations
import struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)

def read_rva(rva, n):
    off = pe.rva_to_off(rva)
    return pe.data[off:off+n]

# Execute continues past pdata end; dump a window
start, n = 0x18d6560, 0x200
code = [{"rva": hex(i.address), "asm": i.mnemonic+" "+i.op_str} for i in cs.disasm(read_rva(start, n), start)]
Path("research/_t192_clip_COrderGroupCommand_execute_full.txt").write_text(
    "\n".join(f"{c['rva']}  {c['asm']}" for c in code)+"\n", encoding="utf-8")
print("EXECUTE WINDOW")
for c in code:
    print(f"{c['rva']}  {c['asm']}")
    if c["asm"].strip() in ("ret", "int3", "int 3") and int(c["rva"],16) > 0x18d65d4:
        # keep going a bit more after first ret of success path
        if int(c["rva"],16) > 0x18d66c0:
            break

print("\n======= 0x10f1480 (theatre handle gate) =====")
g = 0x10f1480
# find a reasonable size
blob = read_rva(g, 0x80)
code2 = [{"rva": hex(i.address), "asm": i.mnemonic+" "+i.op_str} for i in cs.disasm(blob, g)]
for c in code2:
    print(f"{c['rva']}  {c['asm']}")
    if c["asm"].startswith("ret"):
        break
