import sys, struct, json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)

def cstr_at(rva, maxlen=200):
    for s in pe.sections:
        if s.virtual_address <= rva < s.virtual_address + max(s.virtual_size, s.raw_size):
            off=s.raw_ptr+(rva-s.virtual_address)
            if off<0 or off>=len(pe.data):
                return None
            end=pe.data.find(b"\x00", off, off+maxlen)
            raw=pe.data[off:end if end!=-1 else off+maxlen]
            try:
                return raw.decode("utf-8")
            except:
                return raw.decode("latin1", "replace")
    return None

def target(addr, disp, inst_len):
    return addr+inst_len+disp

# resolve key rip strings in 0x12971a0
needles = [
    (0x12971e0, 0x2145f4a, 7),
    (0x12971ed, 0x2145f3c, 7),
    (0x1297235, 0x14fd4e1, 7),
    (0x129723c, 0x14fd5f5, 7),
    (0x12972b0, 0x14fd466, 7),
    (0x12972b7, 0x14fd5a2, 7),
    (0x129739e, 0x14fd378, 7),
    (0x12973a5, 0x14fd48c, 7),
    (0x12974ab, 0x14fd26b, 7),
    (0x12974b2, 0x150a4b7, 7),
    (0x1297677, 0x14fd09f, 7),
    (0x129767e, 0x17409fb, 7),
    (0x1297932, 0x14fcde4, 7),
    (0x1297939, 0x1787e38, 7),
    (0x1297c8d, 0x14fca89, 7),
    (0x1297c94, 0x1787af5, 7),
    (0x1297bc7, 0x2149c6a, 7),  # cost global
    (0x1297351, 0x1e65ca8, 7),
]
# Better: parse actual instruction lengths from capstone for these addresses
raw=pe.read_rva(0x12971a0, 0x1297f08-0x12971a0) or b""
ins_map={}
for i in cs.disasm(raw, 0x12971a0):
    ins_map[i.address]=i

print("===== resolved strings / globals =====")
resolved=[]
for addr, disp, _ in needles:
    i=ins_map.get(addr)
    if not i:
        print("missing", hex(addr)); continue
    tgt=i.address+i.size+disp if "rip" in i.op_str else None
    # capstone already gives the computed address in op_str sometimes as [rip + x] only disp
    # parse from bytes
    # rip-rel is last 4 bytes of instruction
    rel=struct.unpack_from("<i", i.bytes, i.size-4)[0]
    tgt=i.address+i.size+rel
    s=cstr_at(tgt)
    print(f"0x{addr:x} {i.mnemonic} {i.op_str} -> {hex(tgt)} {s!r}")
    resolved.append({"at":hex(addr),"asm":f"{i.mnemonic} {i.op_str}","target":hex(tgt),"str":s})

# caller 0x12ae4e5 window strings
fo_start, fo_end = 0x12ae4e5, 0x12ae8f5
raw=pe.read_rva(fo_start, fo_end-fo_start) or b""
print("===== caller 0x12ae4e5 rip strings =====")
for i in cs.disasm(raw, fo_start):
    if "rip" in i.op_str and i.mnemonic=="lea":
        rel=struct.unpack_from("<i", i.bytes, i.size-4)[0]
        tgt=i.address+i.size+rel
        s=cstr_at(tgt)
        if s and any(c.isalpha() for c in s[:40]):
            print(f"0x{i.address:x} -> {hex(tgt)} {s[:120]!r}")

# 11105b0 around type 4 / cmp 2,3
print("===== 0x11105b0 around type uses =====")
raw=pe.read_rva(0x11106e0, 0x200) or b""
# actually around 0x111072e and 0x11115e1
for start,n in [(0x11106f0, 0x120), (0x1111580, 0x200)]:
    raw=pe.read_rva(start, n) or b""
    print(f"--- {hex(start)} ---")
    for i in cs.disasm(raw, start):
        print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")

# 10b6800 around cmp byte [rcx+r14], 2
print("===== 0x10b6800 around type cmp =====")
raw=pe.read_rva(0x10b6ba0, 0x220) or b""
for i in cs.disasm(raw, 0x10b6ba0):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")

Path("research/t181_family_strings.json").write_text(json.dumps(resolved, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
