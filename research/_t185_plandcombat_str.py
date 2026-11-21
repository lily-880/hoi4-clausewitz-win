import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def dump_cstr(rva, before=80, after=200):
    # find start of string
    raw=pe.read_rva(rva-before, before+after) or b""
    # locate the needle offset
    # expand to surrounding C string
    mid=before
    s=max(0, raw.rfind(b"\x00", 0, mid)+1)
    e=raw.find(b"\x00", mid)
    if e<0: e=len(raw)
    return raw[s:e].decode("ascii","replace"), rva-before+s

needles=[b"pLandCombat", b"pMovingTo", b"How can we be moving", b"GetSize()", b"isolated", b"in_supply"]
print("===== exact / nearby strings =====")
found_rvas=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for n in needles:
        for m in re.finditer(re.escape(n), blob):
            rva=s.virtual_address+m.start()
            try:
                txt, start=dump_cstr(rva, 120, 300)
            except Exception as e:
                txt=str(e); start=rva
            print(f"\n{s.name} hit {hex(rva)} start {hex(start)}")
            print("  ", txt[:400])
            found_rvas.append((n.decode(), start, rva, txt[:200]))

# RIP lea/lea-mem xrefs: 48 8D ?? rel32 or 4C 8D, also 48 8B 0D (mov rcx,[rip]), 48 8D 15
def lea_xrefs(rva, limit=30):
    hits=[]
    # any instruction with rel32 to this rva: look at 7-byte lea (48/4C 8D xx rel32)
    for m in re.finditer(b"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x2d\x35\x3d]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+3)[0]
        dest=text_rva+at+7+rel
        if dest==rva:
            fo=func_of(text_rva+at)
            hits.append((hex(text_rva+at), hex(fo[0]) if fo else None))
            if len(hits)>=limit: break
    return hits

# also  lea rdx, [rip+disp] encodings already covered
# some compilers use lea r8, [rip+str]

print("\n===== xrefs to unique string starts =====")
seen=set()
for name, start, hit, txt in found_rvas:
    if start in seen: continue
    seen.add(start)
    xs=lea_xrefs(start)
    print(f"start {hex(start)} n={len(xs)} first={txt[:80]!r}")
    for x in xs[:15]:
        print("  ", x)

# Also xref the pLandCombat string itself at 0x2a04720 and nearby starts
for rva in (0x2a04720, 0x2a04708, 0x2a046f0, 0x2a04714):
    # try dump
    try:
        txt, start=dump_cstr(rva, 8, 80)
        xs=lea_xrefs(rva)
        print(f"probe {hex(rva)} str={txt[:60]!r} xrefs {xs[:8]}")
    except Exception:
        pass
