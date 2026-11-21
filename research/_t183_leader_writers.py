import json,sys,struct,re,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={item["token"]:item["name"] for item in mp}
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

# who has 0x14a8ec0 in a vtable? search .rdata for pointer 0x14014a8ec0 or rva-based
# typically vtable entries are image-base absolute: 0x140000000+0x14a8ec0 = 0x1414a8ec0
IMAGE=0x140000000
need=struct.pack("<Q", IMAGE+0x14a8ec0)
hits=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in re.finditer(re.escape(need), blob):
        rva=s.virtual_address+m.start()
        hits.append({"section":s.name,"rva":hex(rva)})
print("vtable hits for 0x14a8ec0", hits)

# also search 0xc7e8c0, 0xc645e0, 0xc76550, 0xc72db0
for fn in (0xc7e8c0, 0xc645e0, 0xc76550, 0xc72db0, 0xced2e0, 0xc5c0a0):
    need=struct.pack("<Q", IMAGE+fn)
    hs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(need), blob):
            hs.append(hex(s.virtual_address+m.start())+"@"+s.name)
    print("vtable", hex(fn), hs[:8], "n", len(hs))

# tokens in CArmyLeader writers
def clip(start, end, path=None):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

for rva,name in [(0xc7e8c0,"c7e8c0"),(0xc645e0,"c645e0"),(0xc76550,"c76550"),(0xc72db0,"c72db0")]:
    fo=func_of(rva)
    end=(fo[1] if fo else rva+0x800)
    if end-rva>0x1000: end=rva+0x1000
    lines=clip(rva, end, f"research/_t183_clip_leader_writer_0x{rva:x}.txt")
    toks=[ln for ln in lines if "TOKEN" in ln]
    print(f"\n==== {name} size {end-rva:#x} tokens {len(toks)} ====")
    for ln in toks:
        print(ln)
