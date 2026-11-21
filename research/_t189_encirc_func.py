import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)

# pdata lookup for function containing 0x1572c4a
pdata=[s for s in pe.sections if s.name==".pdata"][0]
pblob=pe.read_rva(pdata.virtual_address, pdata.virtual_size) or b""
# RUNTIME_FUNCTION: BeginAddress, EndAddress, UnwindInfo dword each
hit=None
for i in range(0, len(pblob)-12, 12):
    begin,end,unw=struct.unpack_from("<III", pblob, i)
    if begin <= 0x1572c4a < end:
        hit=(begin,end,unw)
        break
print("pdata", tuple(hex(x) for x in hit) if hit else None)

# also scan nearby pdata if mid-function issue
near=[]
for i in range(0, len(pblob)-12, 12):
    begin,end,unw=struct.unpack_from("<III", pblob, i)
    if 0x1572000 <= begin <= 0x1574000:
        near.append((begin,end))
print("near funcs", [(hex(a),hex(b)) for a,b in near[:20]], "n", len(near))

start = hit[0] if hit else 0x1572800
raw=pe.read_rva(start, 0x200) or b""
print(f"\n======= func start 0x{start:x} first 40 =====")
n=0
for i in cs.disasm(raw, start):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    n+=1
    if n>=45: break

# string at 0x1221ad3 + 0x1572c43 lea rdx? 0x1572c43 lea rdx, [rip+0x1221ad3] -> file/assert name
# compute
# 0x1572c43 lea rdx, [rip+0x1221ad3]; next is 0x1572c4a, rip=0x1572c4a, tgt=0x1572c4a+0x1221ad3=0x2794471d too big
# wait capstone: lea rdx, [rip + 0x1221ad3] at 0x1572c43, insn 7 bytes? 48 8D 15 disp, end 0x1572c4a
# target = 0x1572c4a + 0x1221ad3 = 0x2794471d not in image...
# Maybe I should just print the two lea strings from the assert.

def lea_target(addr):
    raw=pe.read_rva(addr, 8) or b""
    # find lea
    for i in cs.disasm(raw, addr):
        if i.mnemonic=="lea":
            # parse
            return i.op_str
    return None
print("lea rdx", lea_target(0x1572c43))
print("lea rcx", lea_target(0x1572c4a))

# read cstring at computed targets more carefully
raw=pe.read_rva(0x1572c43, 16) or b""
print("bytes", raw.hex())
for i in cs.disasm(raw, 0x1572c43):
    print(i.address, i.mnemonic, i.op_str, "bytes", i.bytes.hex())
    if "rip" in i.op_str:
        # disp is last 4
        disp=struct.unpack_from("<i", i.bytes, len(i.bytes)-4)[0]
        tgt=i.address+len(i.bytes)+disp
        b=pe.read_rva(tgt, 80) or b""
        s=b.split(b"\x00",1)[0].decode("latin1","replace")
        print("  tgt", hex(tgt), s)
