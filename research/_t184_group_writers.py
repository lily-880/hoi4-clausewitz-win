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

def dump_writer(rva, path, maxsz=0x800):
    fo=func_of(rva)
    start=fo[0] if fo else rva
    end=min((fo[1] if fo else rva+maxsz), start+maxsz)
    if end-start < 0x80:
        end=start+maxsz
    lines=clip(start, end, path)
    toks=[ln for ln in lines if "TOKEN" in ln]
    print(f"\n==== {path} start {hex(start)} size {end-start:#x} toks {len(toks)} ====")
    for ln in toks:
        print(ln)
    return lines

# group writers (vtable slot 2)
dump_writer(0xc4d030, "research/_t184_clip_ordersgroup_writer_0xc4d030.txt")
dump_writer(0xc4cfa0, "research/_t184_clip_armygroup_writer_0xc4cfa0.txt")
dump_writer(0x16d9e10, "research/_t184_clip_theatergroup_writer_0x16d9e10.txt")
dump_writer(0xf809b0, "research/_t184_clip_front_writer_0xf809b0.txt")
dump_writer(0x134d5f0, "research/_t184_clip_landcombatant_writer_0x134d5f0.txt")

# CLandCombat alt vtable
IMAGE=pe.image_base
for vt in (0x2a237b8, 0x2a23898):
    raw=pe.read_rva(vt, 0x80) or b""
    fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if struct.unpack_from("<Q", raw, i)[0]>=IMAGE]
    print("CLandCombat vt", hex(vt), "rtti", _rtti_name_from_vtable(pe, vt), "fns", fns)

# try serialize-looking functions on CLandCombat: 0x133a840 ctor? 0x133e5e0?
dump_writer(0x133e5e0, "research/_t184_clip_landcombat_0x133e5e0.txt", 0x400)
# CLandCombatant already dumping

# CMoveCommand vtable if we can find quickly from previous json interesting list
# search rtti name
