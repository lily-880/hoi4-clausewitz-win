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

def clip(start, end, path=None):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

def e8_callers(dest, limit=30):
    hits=[]
    for m in re.finditer(rb"\xe8", text_raw):
        if m.start()+5>len(text_raw): continue
        at=text_rva+m.start()
        rel=struct.unpack_from("<i", text_raw, m.start()+1)[0]
        if at+5+rel==dest:
            fo=func_of(at)
            hits.append({"at":hex(at),"func":hex(fo[0]) if fo else None,"end":hex(fo[1]) if fo else None})
            if len(hits)>=limit: break
    return hits

targets = [0x13e0c40, 0x12971a0, 0x1297f10, 0x1298c80, 0x12999f0, 0x129a760, 0x10b6800, 0x11105b0, 0x1394d30, 0xfd7980]
# first: small predicate and one family member full, others just head+callers
out={"callers":{}}
for t in targets:
    fo=func_of(t) or (t, t+0x200)
    callers=e8_callers(t)
    out["callers"][hex(t)]={"window":[hex(fo[0]),hex(fo[1])],"size":fo[1]-fo[0],"callers":callers}
    print(hex(t), "size", fo[1]-fo[0], "callers", callers)

# full clips for the small one and first family + 10b6800 type cmp region
for t,name in [(0x13e0c40,"predicate_0x13e0c40"),(0x12971a0,"family_0x12971a0")]:
    fo=func_of(t)
    lines=clip(fo[0], fo[1], f"research/_t181_clip_{name}.txt")
    print("wrote", name, "ins", len(lines))

# region around type uses for 10b6800, 11105b0, 1394d30
def around(addr, before=80, after=80):
    fo=func_of(addr)
    start=max(fo[0] if fo else addr-before, addr-before)
    raw=pe.read_rva(start, before+after+16) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        if addr-before <= i.address <= addr+after:
            lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    return lines

print("===== 13e0c40 full =====")
print(Path("research/_t181_clip_predicate_0x13e0c40.txt").read_text(encoding="utf-8"))

Path("research/t181_type_consumers_callers.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
