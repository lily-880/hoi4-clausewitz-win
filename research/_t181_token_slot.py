import sys, struct, re, json, bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def lea_xrefs(dest, limit=80):
    hits=[]
    data=text_raw
    for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", data):
        if m.start()+7>len(data): continue
        at=text_rva+m.start()
        rel=struct.unpack_from("<i", data, m.start()+3)[0]
        if at+7+rel==dest:
            fo=func_of(at)
            hits.append({"at":hex(at),"func":hex(fo[0]) if fo else None,"end":hex(fo[1]) if fo else None})
            if len(hits)>=limit: break
    return hits

# More general RIP-relative refs (modrm 05) for a dest:  rip-rel 32
def rip_xrefs(dest, limit=80):
    hits=[]
    data=text_raw
    # any instruction with rel32 at +3 after a 7-byte? Better scan all positions: opcode patterns vary.
    # Scan 4-byte rel32 such that addr+4+rel == dest or addr+5+rel, addr+6, addr+7 (common instr lengths after opcode)
    # More reliable: use capstone on windows around candidates.
    # Fast path: for i in range, if struct unpacked as rel32 from i, for disp in (i+4,) ... too slow.
    # Use regex for common:  rex? (8b/89/3b/39/81/83/ff/8d) /5  rel32
    # Also 8b 0d, 8b 15, 3b 05, cmp dword ptr [rip+x]
    for m in re.finditer(rb"(?:[\x48\x4c\x40-\x4f])?[\x89\x8b\x39\x3b\x8d\x85\x81\x83\xff\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", data):
        # this may have false start; compute end of opcode+modrm then rel32
        # If first byte is rex, instr is rex op modrm rel32 (7 bytes); else op modrm rel32 (6 bytes)
        pos=m.start()
        b=data[pos]
        if 0x40<=b<=0x4f:
            if pos+7>len(data): continue
            # verify second is opcode and third is modrm
            at=text_rva+pos
            rel=struct.unpack_from("<i", data, pos+3)[0]
            tgt=at+7+rel
            if tgt==dest:
                fo=func_of(at)
                hits.append({"at":hex(at),"func":hex(fo[0]) if fo else None,"kind":"rex+rip"})
        else:
            if pos+6>len(data): continue
            at=text_rva+pos
            rel=struct.unpack_from("<i", data, pos+2)[0]
            tgt=at+6+rel
            if tgt==dest:
                fo=func_of(at)
                hits.append({"at":hex(at),"func":hex(fo[0]) if fo else None,"kind":"rip"})
        if len(hits)>=limit:
            break
    return hits

# Disasm around 0xab285 in 0x83760 to get token slot
def disasm_range(start, end, max_ins=80):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if len(lines)>=max_ins: break
    return lines

print("===== around river_crossing lea 0xab285 =====")
# show 0xab250 to 0xab2e0
lines=disasm_range(0xab250, 0xab2e0, 40)
print("\n".join(lines))

# Also crossing_river and CROSSING_RIVERS
for name,dest in [("crossing_river",0x29d1ed2),("CROSSING_RIVERS",0x29a298c),("NSupply CROSSING_RIVERS name",0x29a2a0d)]:
    xs=lea_xrefs(dest)
    print(name, "lea", xs)

# Find token slot by parsing the register call pattern near 0xab285
# Expected: lea r8, [rip+river_crossing]; ... lea rcx, [rip+SLOT]; call 0x2547630
print("===== slot hunt =====")
