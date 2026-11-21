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

SLOT=0x346D188  # river_crossing token slot from lea rcx at 0xab28e

def rip_xrefs(dest, limit=100):
    hits=[]
    data=text_raw
    # scan all 4-byte aligned and unaligned rel32 that could be rip-rel
    # Too many FPs if we do every offset. Use capstone-like opcode prefixes.
    # Pattern: optional rex, opcode, modrm with mod=00 rm=101 (rip), rel32
    i=0
    n=len(data)
    while i < n-6:
        b0=data[i]
        rex=None
        opoff=i
        if 0x40<=b0<=0x4f:
            rex=b0
            opoff=i+1
            if opoff>=n: break
        op=data[opoff]
        # skip likely not
        if opoff+1>=n:
            i+=1; continue
        modrm=data[opoff+1]
        if (modrm & 0xC7)==0x05:  # mod=00, rm=101 RIP
            rel_at=opoff+2
            if rel_at+4<=n:
                rel=struct.unpack_from("<i", data, rel_at)[0]
                at=text_rva+i
                end=text_rva+rel_at+4
                tgt=end+rel
                if tgt==dest:
                    fo=func_of(at)
                    # disasm one ins
                    raw=data[i:i+15]
                    ins=next(cs.disasm(raw, at), None)
                    hits.append({
                        "at":hex(at),
                        "func":hex(fo[0]) if fo else None,
                        "end":hex(fo[1]) if fo else None,
                        "asm": (ins.mnemonic+" "+ins.op_str) if ins else None,
                    })
                    if len(hits)>=limit:
                        break
        i+=1
    return hits

print("scanning slot xrefs...")
hits=rip_xrefs(SLOT)
print("slot 0x346D188 xrefs", len(hits))
for h in hits:
    print(" ", h)

# also try slot as dword in .data? maybe the registrar writes a CStringId at slot
# crossing_river context
def rva_str(rva, before=32, after=80):
    # find section
    for s in pe.sections:
        if s.virtual_address <= rva < s.virtual_address+s.virtual_size:
            off=s.raw_ptr+(rva-s.virtual_address)
            chunk=pe.data[max(0,off-before):off+after]
            # printable around
            return chunk
    return b""

chunk=rva_str(0x29d1ed2, 48, 80)
print("crossing_river context:", chunk)

# find xref to 0x29d1ed2 by also scanning for the pointer as qword in rdata (not just lea)
PTR=struct.pack("<Q", 0x140000000+0x29d1ed2)
# and 32-bit RVA pointer
PTR32=struct.pack("<I", 0x29d1ed2)
print("qword ptr count", pe.data.count(PTR), "rva32 count", pe.data.count(PTR32))

# CROSSING_RIVERS 0x29a298c
PTRC=struct.pack("<Q", 0x140000000+0x29a298c)
print("CROSSING_RIVERS qword", pe.data.count(PTRC), "rva32", pe.data.count(struct.pack("<I", 0x29a298c)))

Path("research/t181_token_slot_xrefs.json").write_text(json.dumps({"slot":hex(SLOT),"xrefs":hits}, indent=2)+"\n", encoding="utf-8")
