from __future__ import annotations
import json, struct, sys
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session
from province import resolve_province
from input_loaded_fields import LoadedReader, province_land_neighbors, province_adjacencies
from gamestate import _rtti_name_from_vtable

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
p=Proc(mem_find_pid("hoi4.exe"))
pe=PE(EXE)
session=detect_session(p,pe)
gs=int(session["signals"]["gs_ptr"],16)

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

r=LoadedReader(p.read, cls)
border=[1984,13237,13238,4995,8062,12812]
info={}
pairs=[]
for pid in border+[5010,8036,7980]:
    prov=resolve_province(p, pid, p.base, gs)
    if not prov:
        info[pid]={"err":"resolve_failed"}; continue
    try:
        adj=province_adjacencies(r, prov)
        nbs=adj.get("neighbors") if isinstance(adj, dict) else adj
        land=None
        try:
            land, ev=province_land_neighbors(r, prov)
        except Exception as e:
            land=str(e)
        info[pid]={"prov":hex(prov),"adj_keys":list(adj) if isinstance(adj,dict) else type(adj).__name__,
                   "neighbors":nbs,"land":land}
    except Exception as e:
        info[pid]={"err":str(e),"prov":hex(prov)}

# extract integer neighbor ids
def ids_of(x):
    out=[]
    if isinstance(x, dict):
        if "neighbors" in x:
            return ids_of(x["neighbors"])
        if "id" in x: return [x["id"]]
    if isinstance(x, (list,tuple)):
        for i in x:
            if isinstance(i, int): out.append(i)
            elif isinstance(i, dict):
                for k in ("id","province_id","to","neighbor","dst"):
                    if k in i and isinstance(i[k], int):
                        out.append(i[k]); break
    return out

print(json.dumps({str(k):v for k,v in info.items()}, indent=2, ensure_ascii=False, default=str)[:4000])
for a in border:
    nbs=ids_of(info.get(a,{}).get("land")) or ids_of(info.get(a,{}).get("neighbors"))
    for b in nbs:
        if b in border and a<b:
            pairs.append((a,b))
print("PAIRS", pairs)
p.close()
