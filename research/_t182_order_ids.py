import sys, re, json, struct, bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
db=pe.data
cs=Cs(CS_ARCH_X86, CS_MODE_64)
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

def rva_of(off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def lea_xrefs(dest, limit=40):
    hits=[]
    for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", text_raw):
        if m.start()+7>len(text_raw): continue
        at=text_rva+m.start()
        rel=struct.unpack_from("<i", text_raw, m.start()+3)[0]
        if at+7+rel==dest:
            fo=func_of(at)
            hits.append({"at":hex(at),"func":hex(fo[0]) if fo else None,"end":hex(fo[1]) if fo else None})
            if len(hits)>=limit: break
    return hits

# collect ORDER_* and GetOrderType strings
print("===== ORDER_ / GetOrderType strings =====")
orders=[]
for m in re.finditer(rb"(ORDER_[A-Z0-9_]+|GetOrderType[^\x00]{0,60}|order_type[^\x00]{0,40}|land_combat_id|in_supply|is_isolated|isolated_flag|army_isolated|current_supply|unit_is_in_combat)", db):
    off=m.start()
    # full cstring
    while off>0 and 32<=db[off-1]<127: off-=1
    end=db.find(b"\x00", m.start())
    s=db[off:end].decode("ascii","replace") if end!=-1 else m.group().decode()
    if len(s)>100: continue
    rva=rva_of(off)
    orders.append((rva,s))

# unique
seen=set(); uniq=[]
for rva,s in orders:
    if (rva,s) in seen: continue
    seen.add((rva,s))
    uniq.append((rva,s))

for rva,s in sorted(uniq, key=lambda x: x[1]):
    # filter noise
    if "Error reading" in s or "NDefines" in s or s.startswith(".?"): continue
    if s.startswith("ORDER_") or "GetOrderType" in s or s in ("land_combat_id","in_supply","is_isolated","isolated_flag","army_isolated","current_supply","unit_is_in_combat") or s.startswith("order_"):
        print(hex(rva) if rva else None, repr(s))

# RTTI C*Order not Command
print("===== RTTI *Order* short class names =====")
for m in re.finditer(rb"\.\?AVC[A-Za-z0-9_]*Order[A-Za-z0-9_]*@@", db):
    s=m.group().decode()
    if "Command" in s or "Allocator" in s or "Helper" in s or "Window" in s or "Item" in s: continue
    rva=rva_of(m.start())
    if len(s)<60:
        print(hex(rva) if rva else None, s)

# xref key strings
keys={
    "land_combat_id": 0x2b68880,
    "army_current_supply_ratio": 0x2b39948,
    "GetOrderType_MOVE": 0x2a02d50,
    "GetOrderType_INVASION": 0x2a02c18,
    "GetOrderType_NE_MOVE": 0x2a02cb8,
}
print("===== LEA xrefs =====")
xmap={}
for name,dest in keys.items():
    xs=lea_xrefs(dest)
    xmap[name]=xs
    print(name, xs)
Path("research/t182_order_combat_xrefs.json").write_text(json.dumps({"strings":[{"rva":hex(r) if r else None,"s":s} for r,s in uniq if r],"lea":xmap}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
