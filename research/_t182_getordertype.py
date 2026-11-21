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

def clip(start, end, path=None, maxn=200000):
    raw=pe.read_rva(start, min(end-start, maxn)) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

def cstr_at(rva, maxlen=180):
    for s in pe.sections:
        if s.virtual_address <= rva < s.virtual_address + max(s.virtual_size, s.raw_size):
            off=s.raw_ptr+(rva-s.virtual_address)
            end=pe.data.find(b"\x00", off, off+maxlen)
            raw=pe.data[off:end if end!=-1 else off+maxlen]
            try: return raw.decode("utf-8")
            except: return raw.decode("latin1","replace")
    return None

# token slot for land_combat_id at lea 0xefd1b
print("===== around land_combat_id lea 0xefd1b =====")
# start a bit earlier, aligned
lines=clip(0xefce0, 0xefd60)
# may start mid-ins; print from a clean lea
print("\n".join(lines))

# GetOrderType functions - full small ones
for t in (0x10b2c60, 0x10b0370, 0x10cbcf0, 0x10b4570, 0x10cd220):
    fo=func_of(t)
    print(f"\n======= {hex(t)} window {fo} size {fo[1]-fo[0] if fo else '?'} =====")
    if fo and fo[1]-fo[0] <= 0x400:
        ls=clip(fo[0], fo[1], f"research/_t182_clip_GetOrderType_{hex(t)}.txt")
        print("\n".join(ls))
    else:
        # around the xref
        pass
