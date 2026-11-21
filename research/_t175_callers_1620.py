import sys,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name==".pdata")
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III",raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
IMAGE=0x140000000

def pdata(rva):
    if rva>=IMAGE: rva-=IMAGE
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def callers(target, limit=80):
    text=next(s for s in pe.sections if s.name==".text")
    data=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
    va=text.virtual_address
    hits=[]; pos=0
    while True:
        i=data.find(b"\xE8",pos)
        if i<0: break
        if i+5<=len(data):
            rel=struct.unpack_from("<i",data,i+1)[0]
            at=va+i
            dest=(at+5+rel)&0xffffffff
            if dest==target:
                w=pdata(at)
                hits.append((at, w[0] if w else None))
                if len(hits)>=limit: break
        pos=i+1
    return hits

def dump(entry, n=None):
    w=pdata(entry)
    if n is None:
        n=(w[1]-entry) if w else 80
    raw=pe.read_rva(entry,n) or b""
    ins=list(cs.disasm(raw, entry))
    lines=[]
    for i in ins:
        lines.append("%s  %s %s"%(hex(i.address), i.mnemonic, i.op_str))
        if i.mnemonic=="ret":
            break
        if i.mnemonic=="int3" and lines and " ret" in lines[-2] if len(lines)>1 else False:
            break
    return "\n".join(lines), w

for t,name in [(0x15a92c0,"15a92c0"),(0x15a93d0,"15a93d0"),(0x15a16a0,"15a16a0")]:
    cs_list=callers(t)
    funcs=sorted(set(hex(f) for _,f in cs_list if f))
    print(name, "caller_n", len(cs_list), "funcs", funcs)
    print("  sites", [(hex(a),hex(f) if f else None) for a,f in cs_list[:20]])

text,w=dump(0x15a92c0, 0x30)
Path("research/_t175_clip_15a92c0.txt").write_text(text+"\n",encoding="utf-8")
print("===== 15a92c0 =====")
print(text)

text,w=dump(0x717410)
Path("research/_t175_clip_717410.txt").write_text(text+"\n",encoding="utf-8")
print("===== 717410 pdata", None if not w else (hex(w[0]),hex(w[1])), "len", len(text.splitlines()))
for l in text.splitlines():
    if "call " in l or "0xf" in l or l.startswith("0x717410") or "ret" in l:
        print(l)
