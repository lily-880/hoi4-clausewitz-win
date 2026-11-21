import os, sys, json, struct
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from handle import resolve_handle, HANDLE_TYPE_ARMY

# reuse list of ids from previous hunt
IDS = [2248,2278,2283,2291,2296,2323,2342,2347,2370,2373,2385,2397,2415,2424,2439,2455,2479,2483,2486,2493,2509,2516]
CA_HANDLE=0x18
CA_PROVINCE_ID=0x28
CA_COUNTRY_TAG=0x1E0
CA_SUB=O.HYPOTHESIS_STRUCT.get("CA_SUBUNIT_DEF",0x138)
CA_PROV=O.HYPOTHESIS_STRUCT.get("CA_PROVINCE",0x1F0)
CA_TMPL=O.HYPOTHESIS_STRUCT.get("CA_DIV_TEMPLATE",0x3B8)
CA_NAME=0x340

p=Proc(find_pid(config.EXE_NAME))
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
def u32(a):
    x=p.try_read(a,4)
    return struct.unpack_from("<I",x,0)[0] if x else None

# vtable drift: live often 0x29d6d98 vs proven 0x29D6D68
rows=[]
for ix in IDS:
    obj=resolve_handle(b, HANDLE_TYPE_ARMY, ix, p.base)
    vt=u64(obj)
    sub,prov,tmpl,name=u64(obj+CA_SUB),u64(obj+CA_PROV),u64(obj+CA_TMPL),u64(obj+CA_NAME)
    def child_vt(ptr):
        return hex(u64(ptr)) if ptr and 0x10000<ptr<0x7FFFFFFFFFFF else None
    rows.append({
        "id": ix,
        "obj": hex(obj),
        "vt": hex(vt) if vt else None,
        "vt_rva": hex(vt-p.base) if vt and vt>=p.base else None,
        "province": u32(obj+CA_PROVINCE_ID),
        "sub": hex(sub) if sub else None, "sub_vt": child_vt(sub),
        "provp": hex(prov) if prov else None, "prov_vt": child_vt(prov),
        "tmpl": hex(tmpl) if tmpl else None, "tmpl_vt": child_vt(tmpl),
        "name_member": hex(name) if name else None, "name_vt": child_vt(name),
        "markers": {
            "sub_nonzero": bool(sub and sub>0x10000),
            "prov_nonzero": bool(prov and prov>0x10000),
            "tmpl_nonzero": bool(tmpl and tmpl>0x10000),
            "name_nonzero": bool(name and name>0x10000),
        }
    })
print(json.dumps(rows, indent=2))
# vtable groups
from collections import Counter
print("VT", Counter(r["vt"] for r in rows))
p.close()
