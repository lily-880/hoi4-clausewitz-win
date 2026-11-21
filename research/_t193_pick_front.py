from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable
from province import resolve_province
from input_loaded_fields import LoadedReader, province_land_neighbors

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe=PE(EXE)
cs=Cs(CS_ARCH_X86, CS_MODE_64)
p=Proc(mem_find_pid("hoi4.exe"))

# sentinels
# 0x33CB2A0 and 0x33CB2A4 are RVAs
s0=struct.unpack("<I", pe.data[pe.rva_to_off(0x33CB2A0):pe.rva_to_off(0x33CB2A0)+4])[0]
s1=struct.unpack("<I", pe.data[pe.rva_to_off(0x33CB2A4):pe.rva_to_off(0x33CB2A4)+4])[0]
# also live in process
base=p.base
live0=struct.unpack("<I", p.read(base+0x33CB2A0,4))[0]
live1=struct.unpack("<I", p.read(base+0x33CB2A4,4))[0]
print("sentinels pe", s0, s1, "live", live0, live1, hex(s0), hex(s1))

# disasm 0xc41720 head and 0x10ce370
def find_fn(rva):
    pdata=next(s for s in pe.sections if s.name.startswith(".pdata"))
    raw=pe.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size]
    n=len(raw)//12
    lo,hi=0,n-1
    while lo<=hi:
        mid=(lo+hi)//2
        b,e,u=struct.unpack_from("<III", raw, mid*12)
        if rva<b: hi=mid-1
        elif rva>=e: lo=mid+1
        else: return b,e
    return None

for rva,n in ((0xc41720, 0x80),(0x10ce370, 0x80)):
    fn=find_fn(rva)
    print(f"\n===== {hex(rva)} fn={None if not fn else (hex(fn[0]),hex(fn[1]))} =====")
    blob=pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+(n if not fn else min(n, fn[1]-fn[0]))]
    for i in cs.disasm(blob, rva):
        print(f"{hex(i.address)}  {i.mnemonic} {i.op_str}")
        if i.mnemonic=="ret":
            break

# ORDER_ strings near GetOrderType
# search pe for ORDER_FRONT, FRONTLINE, etc
data=pe.data
for needle in (b"ORDER_FRONT", b"ORDER_OFFENSIVE", b"ORDER_GARRISON", b"AREA_DEFENSE", b"GetOrderType", b"ORDER_MOVE", b"FRONT_LINE", b"frontline"):
    i=0; c=0
    while c<5:
        j=data.find(needle, i)
        if j<0: break
        snippet=data[j:j+80].split(b"\x00")[0]
        print("STR", needle, "off", hex(j), snippet)
        i=j+1; c+=1

# pick two adjacent ITA-border ETH provinces
session=detect_session(p,pe)
gs=int(session["signals"]["gs_ptr"],16)
# reuse t191 neighbor knowledge: candidates
cands=[1984,13237,13238,4995,8062,12812,5010,7980,8036]
# try import resolve
from gamestate import resolve_player_country
co=int(resolve_player_country(p,gs)["country_ptr"],16)

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF

def cls(a):
    if not is_ptr(a): return None
    try:
        vt=struct.unpack("<Q", p.read(a,8))[0]
    except OSError:
        return None
    if not p.base<=vt<p.base+p.image_size: return None
    return _rtti_name_from_vtable(pe, vt-p.base)

# land neighbors via LoadedReader if possible
r=LoadedReader(p.read, lambda a: cls(a))
pairs=[]
info={}
for pid in cands:
    try:
        prov=resolve_province(p, gs, pid)
    except Exception as e:
        info[pid]={"err":str(e)}; continue
    try:
        nbs, ev = province_land_neighbors(r, prov)
    except Exception as e:
        # maybe signature
        try:
            adj=__import__("input_loaded_fields").province_adjacencies(r, prov)
            nbs=adj.get("neighbors") or adj.get("land") or adj
        except Exception as e2:
            info[pid]={"err":f"{e} / {e2}"}; continue
    info[pid]={"neighbors":nbs}
# find pair among border cands
border=set([1984,13237,13238,4995,8062,12812])
for a in border:
    nbs=info.get(a,{}).get("neighbors")
    if not nbs: continue
    ids=nbs if isinstance(nbs, list) and (not nbs or not isinstance(nbs[0], dict)) else None
    if ids is None and isinstance(nbs, list):
        ids=[]
        for item in nbs:
            if isinstance(item, dict):
                ids.append(item.get("id") or item.get("province_id") or item.get("to"))
            elif isinstance(item, int):
                ids.append(item)
    if not ids: 
        info[a]["parsed"]=nbs
        continue
    for b in ids:
        if b in border and a<b:
            pairs.append((a,b))

Path("research/t193_front_provinces.json").write_text(json.dumps({"sentinels":{"pe":[s0,s1],"live":[live0,live1]},"info":{str(k):v for k,v in info.items()},"pairs":pairs}, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
print("PAIRS", pairs)
print("INFO keys", {k: (list(v) if isinstance(v,dict) else type(v)) for k,v in info.items()})
p.close()
