import os, sys, json, collections
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, struct
from mem import Proc, find_pid
from pe import PE
from handle import resolve_handle, HANDLE_TYPE_ARMY
from gamestate import _rtti_name_from_vtable
from country_tags import tag_for_index

p=Proc(find_pid(config.EXE_NAME))
exe = getattr(p, "image_path", None) or r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
print("EXE", exe)
pe=PE(exe)

class Backend:
    def __init__(self, proc):
        self._p=proc; self.image_base=proc.base
    def read(self,a,n):
        b=self._p.try_read(a,n)
        if not b or len(b)<n: raise OSError("short")
        return b
b=Backend(p)

def u64(a):
    x=p.try_read(a,8)
    return struct.unpack_from("<Q",x,0)[0] if x else None
def i32(a):
    x=p.try_read(a,4)
    return struct.unpack_from("<i",x,0)[0] if x else None

def rtti(vt):
    if not vt or vt < p.base:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)

print("live CArmy vt", rtti(p.base + 0x29d6d98))
print("proven CArmy vt", rtti(p.base + 0x29D6D68))
print("other 0x29df900", rtti(p.base + 0x29df900))
print("name member army", rtti(0x7ff73a043c88))
print("name member other", rtti(0x7ff73a06f3d8))

vt_counts=collections.Counter()
carmy_by_country=collections.Counter()
usa_by_vt=collections.defaultdict(list)
CA_COUNTRY_TAG=0x1E0
for ix in range(1, 20001):
    try:
        obj=resolve_handle(b, HANDLE_TYPE_ARMY, ix, p.base)
    except Exception:
        continue
    if not obj:
        continue
    vt=u64(obj)
    rva=(vt-p.base) if vt and vt>=p.base else None
    key=hex(rva) if rva is not None else hex(vt or 0)
    vt_counts[key]+=1
    tag=i32(obj+CA_COUNTRY_TAG)
    if rva in (0x29d6d98, 0x29d6d68, 0x29D6D68):
        carmy_by_country[tag]+=1
    if tag==68:
        usa_by_vt[key].append(ix)

print("VT_COUNTS")
for k,c in vt_counts.most_common():
    rva=int(k,16)
    print(f"  {k} n={c} rtti={rtti(p.base+rva)}")
print("USA_BY_VT", {k: (len(v), v[:20]) for k,v in usa_by_vt.items()})
print("CArmy_by_country top", [("idx",i,"tag",tag_for_index(i),"n",n) for i,n in carmy_by_country.most_common(12)])
print("USA CArmy", carmy_by_country.get(68))
p.close()
