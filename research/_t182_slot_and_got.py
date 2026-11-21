import sys, struct, re, json, os, bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

# disassemble 0xefd1b region by scanning back to a 7-byte lea r8
print("===== raw around 0xefd1b =====")
off=0xefd1b-text_rva
# print hex 64 bytes before
chunk=text_raw[off-48:off+32]
print(chunk.hex())
# try disasm from several starts
for start in range(0xefd1b-48, 0xefd1b):
    ins=list(cs.disasm(text_raw[start-text_rva:start-text_rva+80], start))
    if any(i.address==0xefd1b and i.mnemonic=="lea" for i in ins):
        print("aligned at", hex(start))
        for i in ins:
            if 0xefcf0 <= i.address <= 0xefd50:
                print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        break

# more GetOrderType strings
print("===== all GetOrderType strings =====")
db=pe.data
for m in re.finditer(rb"GetOrderType\(\)[^\x00]{0,80}", db):
    print(m.group())
