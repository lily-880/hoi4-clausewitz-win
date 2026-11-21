import sys,re,json,struct,bisect,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

# search disp32 0x2e8:  81 / 8B / 83 / 89 / 8B  with +0x2e8
# encodings: 48 8B 81 e8 02 00 00  mov rax,[rcx+0x2e8]
# 48 8B 89 e8 02 00 00
# 48 8B 99 ... rbx
# 48 89 81 ... store
# 4C 8B 81 ...
pat=re.compile(rb"[\x48\x4c][\x89\x8b][\x80-\xbf]\xe8\x02\x00\x00")
# also 48 83 b9 e8 02 00 00 00  cmp qword [rcx+0x2e8],0
pat2=re.compile(rb"[\x48\x4c]\x83[\x80-\xbf]\xe8\x02\x00\x00")
# 48 8d 81 e8 02 00 00 lea
pat3=re.compile(rb"[\x48\x4c]\x8d[\x80-\xbf]\xe8\x02\x00\x00")

hits=[]
for name,patx in (("mov/store",pat),("cmp/add",pat2),("lea",pat3)):
    for m in patx.finditer(text_raw):
        rva=text_rva+m.start()
        fo=func_of(rva)
        raw=text_raw[m.start():m.start()+16]
        ins=list(cs.disasm(raw, rva))
        line=f"0x{ins[0].address:x}  {ins[0].mnemonic} {ins[0].op_str}" if ins else raw.hex()
        hits.append((name, hex(rva), hex(fo[0]) if fo else None, line))

print("===== +0x2e8 accesses n=%d ====="%len(hits))
# group by function
by=collections.defaultdict(list)
for h in hits:
    by[h[2]].append(h)
for f,hs in list(by.items())[:40]:
    print("func", f, "n", len(hs))
    for h in hs[:6]:
        print(" ", h[0], h[3])

# CGameDate rtti / vtable
# live vtable was 0x7ff724236400 — need RVA. We'll get from name
patn=re.compile(rb"\.\?AVCGameDate@@")
print("\n===== CGameDate =====")
# vtables
def vtables_for(name):
    patb=name.encode()
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        off=0
        while True:
            i=blob.find(patb, off)
            if i<0: break
            tdescs.append(s.virtual_address+i-0x10)
            off=i+1
    vts=set()
    for tdesc in tdescs:
        col_imm=struct.pack("<I", tdesc)
        for s in pe.sections:
            blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
            for m in re.finditer(re.escape(col_imm), blob):
                col_rva=s.virtual_address+m.start()-0x0C
                raw=pe.read_rva(col_rva, 4)
                if raw and struct.unpack("<I", raw)[0] in (0,1):
                    need=struct.pack("<Q", IMAGE+col_rva)
                    for s2 in pe.sections:
                        blob2=pe.data[s2.raw_ptr:s2.raw_ptr+s2.raw_size]
                        for m2 in re.finditer(re.escape(need), blob2):
                            vt=s2.virtual_address+m2.start()+8
                            if _rtti_name_from_vtable(pe, vt)==name:
                                vts.add(vt)
    return sorted(vts)

vts=vtables_for(".?AVCGameDate@@")
print("vtables", [hex(v) for v in vts])
for vt in vts:
    raw=pe.read_rva(vt, 0x40) or b""
    fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if IMAGE<=struct.unpack_from("<Q", raw, i)[0]<IMAGE+0x4000000]
    print(hex(vt), fns[:10])

# also search date token writers for CGameDate
print("\n===== war_relation token already known; search CRelationStatus +2e8 in 0xd8f5c0? =====")
text=Path("research/_t186_clip_relationstatus_writer_0xd8f5c0.txt").read_text(encoding="utf-8")
print("2e8" in text, "380a" in text, "war_relation" in text)
