import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

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

# CTheatre writer
lines=clip(0xf81510, 0xf81940, "research/_t184_clip_theatre_writer_0xf81510.txt")
print("===== CTheatre 0xf81510 tokens/mem =====")
for ln in lines:
    if "TOKEN" in ln or re.search(r"\[rbp \+", ln) or re.search(r"\[r1[0-5] \+", ln) or "lea r8" in ln or "call 0x254" in ln:
        print(ln)

# unknown tokens
for tok in (0x2b95, 0x29e0, 0x346d, 0x28a3, 0x12, 0x10):
    print("tok", hex(tok), id2name.get(tok))

# Find CTheatre / group vtables in rdata
IMAGE=pe.image_base
# From t165, CTheatre vtable 0x29f22b8, functions include 0xf81510, 0xf6a7d0, 0xf7d200, 0xf776d0, 0x2283ef0
print("\nCTheatre vtable 0x29f22b8 rtti", _rtti_name_from_vtable(pe, 0x29f22b8))

# locate vtables for CArmyGroup / CTheaterGroup / likely COrdersGroup by searching RTTI names
# then first few vtable functions
def find_rtti(name):
    pat=name.encode()
    hits=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(pat), blob):
            hits.append(s.virtual_address+m.start())
    return hits

# MSVC: type_descriptor has name at +0x10; COL points at it; vtable-8 points at COL
# Easier path: we have type desc RVAs from t183:
# CArmyGroup 0x32d5040, CTheaterGroup 0x3327e78, CTheatre 0x32ed860, CLandCombat 0x316f1b8, CCommand 0x31e74b8
# Those were name string RVAs (with .?AV prefix at that address-ish)

def vtables_for_type_name(name):
    # find name in data, then find pointers to type descriptor (name-0x10)
    hits=find_rtti(name.encode() if isinstance(name,str) else name)
    vts=[]
    for nrva in hits:
        tdesc=nrva-0x10
        # COL has type desc rva at +0x0C as u32 (RVA)
        col_imm=struct.pack("<I", tdesc)
        cols=[]
        for s in pe.sections:
            blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
            for m in re.finditer(re.escape(col_imm), blob):
                col_rva=s.virtual_address+m.start()-0x0C
                # verify COL signature 1 at +0
                raw=pe.read_rva(col_rva, 4)
                if raw and struct.unpack("<I", raw)[0] in (0,1):
                    cols.append(col_rva)
        # vtable-8 holds VA of COL
        for col in cols:
            need=struct.pack("<Q", IMAGE+col)
            for s in pe.sections:
                blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
                for m in re.finditer(re.escape(need), blob):
                    vt=s.virtual_address+m.start()+8
                    vts.append(vt)
    return sorted(set(vts))

for nm in [b".?AVCTheatre@@", b".?AVCArmyGroup@@", b".?AVCTheaterGroup@@", b".?AVCOrdersGroup@@", b".?AVCOrderGroup@@", b".?AVCFront@@", b".?AVCCommandGroup@@", b".?AVCArmyTheatre@@", b".?AVCUnitGroup@@", b".?AVCLandCombat@@", b".?AVCCommand@@", b".?AVCUnitCommand@@", b".?AVCMoveCommand@@", b".?AVCCombat@@"]:
    vts=vtables_for_type_name(nm)
    print(nm.decode(), "vtables", [hex(v) for v in vts[:6]], "n", len(vts))
    for vt in vts[:2]:
        # first 10 functions as RVA
        raw=pe.read_rva(vt, 80) or b""
        fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if struct.unpack_from("<Q", raw, i)[0]>=IMAGE]
        print("  ", hex(vt), fns[:10], "rtti", _rtti_name_from_vtable(pe, vt))
