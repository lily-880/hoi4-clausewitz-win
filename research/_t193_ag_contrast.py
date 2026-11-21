from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
AG=0x26d3e6baa50
ARMY=0x26d2b077020
LEAD312=0x26cb4c76af0
LEAD313=0x26cb4c78d10

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF

def pdx(p,a):
    return struct.unpack("<QII", p.read(a,16))

def ptr_array(p,a,bound=4096):
    data,cap,size=pdx(p,a)
    if not 0<=size<=cap<=max(bound,100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data+8*j,8))[0] for j in range(size)]

def cls(p,pe,a):
    if not is_ptr(a): return None
    vt=struct.unpack("<Q", p.read(a,8))[0]
    if not p.base<=vt<p.base+p.image_size: return None
    return _rtti_name_from_vtable(pe, vt-p.base)

p=Proc(mem_find_pid("hoi4.exe"))
pe=PE(EXE)
session=detect_session(p,pe)
gs=int(session["signals"]["gs_ptr"],16)
co=int(resolve_player_country(p,gs)["country_ptr"],16)

# scan units for AG ptr or handle 53,2 ; also C0 still army1
arr=ptr_array(p, co+0x290, 4096)
unit_hits={"ag_ptr":[], "h53_2":[], "c0":[]}
for ap in arr:
    uid=struct.unpack("<I", p.read(ap+0x1C,4))[0]
    c0=struct.unpack("<Q", p.read(ap+0xC0,8))[0]
    unit_hits["c0"].append({"id":uid,"c0":hex(c0),"c0_class":cls(p,pe,c0) if is_ptr(c0) else None,
                            "c0_handle": list(struct.unpack("<II", p.read(c0+8,8))) if is_ptr(c0) else None})
    blob=p.read(ap, 0x690)  # official object size, no overlap
    for off in range(0, 0x690-7, 8):
        q=struct.unpack_from("<Q", blob, off)[0]
        if q==AG:
            unit_hits["ag_ptr"].append({"unit":uid,"off":hex(off)})
    for off in range(0, 0x690-7, 4):
        t,i=struct.unpack_from("<II", blob, off)
        if t==53 and i==2:
            unit_hits["h53_2"].append({"unit":uid,"off":hex(off)})

# scan COrdersGroup army1 (object window ~0x250+)
og_hits={"ag_ptr":[], "h53_2":[]}
blob=p.read(ARMY, 0x300)
for off in range(0, 0x300-7, 8):
    q=struct.unpack_from("<Q", blob, off)[0]
    if q==AG:
        og_hits["ag_ptr"].append(hex(off))
for off in range(0, 0x300-7, 4):
    t,i=struct.unpack_from("<II", blob, off)
    if t==53 and i==2:
        og_hits["h53_2"].append(hex(off))

# leaders 1048 + resolve
cc=struct.unpack("<Q", p.read(co+0xFF0,8))[0]
leaders=ptr_array(p, cc+0x70, 512)
lrows=[]
for lp in leaders:
    h=list(struct.unpack("<II", p.read(lp+8,8)))
    asg=list(struct.unpack("<II", p.read(lp+0x1048,8)))
    deployed=p.read(lp+0x1068,1)[0]
    resolved=None
    if asg!=[0,0]:
        # can't easily resolve handle here without handle.resolve; scan army/ag pointers
        resolved={"handle":asg}
        if asg==[53,1]:
            resolved["kind_guess"]="army" if cls(p,pe,ARMY) else None
            resolved["obj"]=hex(ARMY)
        elif asg==[53,2]:
            resolved["kind_guess"]="army_group"
            resolved["obj"]=hex(AG)
            resolved["class"]=cls(p,pe,AG)
    lrows.append({"leader_id":h[1],"assigned":asg,"deployed":deployed,"resolved":resolved})

# named offsets on army1 around possible parent
interesting={}
for off in (0x20,0x28,0x30,0x38,0x40,0x48,0x80,0x88,0x90,0xA0,0xB0,0xC0,0xD0,0xE0,0xF0,0x100,0x110,0x200,0x210,0x220,0x228,0x230):
    q=struct.unpack("<Q", p.read(ARMY+off,8))[0]
    interesting[hex(off)]={"u64":hex(q),"class":cls(p,pe,q)}

out={
    "unit_ag_ptr": unit_hits["ag_ptr"],
    "unit_h53_2": unit_hits["h53_2"],
    "units_c0_nonzero": [r for r in unit_hits["c0"] if int(r["c0"],16)!=0],
    "og_hits": og_hits,
    "og_interesting": interesting,
    "leaders_assigned": [x for x in lrows if x["assigned"]!=[0,0]],
    "deployed_nonzero": [x for x in lrows if x["deployed"]],
    "ag_class": cls(p,pe,AG),
    "ag_handle": list(struct.unpack("<II", p.read(AG+8,8))),
    "ag_leader": hex(struct.unpack("<Q", p.read(AG+0x88,8))[0]),
}
Path("research/t193_ag_contrast.json").write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
p.close()

