import sys,re,json,struct,bisect
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

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

for rva in (0xc4cfa0, 0xc4d030, 0x16d9e10, 0x134d5e0, 0x134d5f0, 0x22858a0, 0x25458c0, 0x22857c0):
    fo=func_of(rva)
    print(hex(rva), "pdata", hex(fo[0]) if fo else None, "end", hex(fo[1]) if fo else None, "sz", hex(fo[1]-fo[0]) if fo else None)

# rewrite armygroup clip to pdata only, and landcombat 0x134d5e0
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

fo=func_of(0xc4cfa0)
lines=clip(fo[0], fo[1], "research/_t184_clip_armygroup_writer_0xc4cfa0.txt")
print("\n===== CArmyGroup ONLY =====")
print("\n".join(lines))

fo=func_of(0x134d5e0)
if fo:
    lines=clip(fo[0], min(fo[1], fo[0]+0x600), "research/_t184_clip_landcombat_writer_0x134d5e0.txt")
    print("\n===== CLandCombat writer tokens =====")
    for ln in lines:
        if "TOKEN" in ln or re.search(r"\[r(bx|si|di|bp|1[0-5]|cx) \+", ln) or "lea r8" in ln:
            print(ln)
else:
    lines=clip(0x134d5e0, 0x134d5e0+0x400, "research/_t184_clip_landcombat_writer_0x134d5e0.txt")
    print("no pdata, dumped 0x400, toks", [ln for ln in lines if "TOKEN" in ln])
