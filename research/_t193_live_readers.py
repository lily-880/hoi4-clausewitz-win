from __future__ import annotations
import json, struct, sys
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from input_loaded_fields import (
    LoadedReader, own_armies, own_army_groups, own_leaders, own_plans,
    unit_formation_army_id, unit_formation_army_group_id, unit_movement_path,
)

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
p=Proc(mem_find_pid("hoi4.exe"))
pe=PE(EXE)
session=detect_session(p,pe)
gs=int(session["signals"]["gs_ptr"],16)
co=int(resolve_player_country(p,gs)["country_ptr"],16)
idler=int(session["signals"].get("idler_ptr") or "0",16)

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

def pdx(a):
    return struct.unpack("<QII", p.read(a,16))
def ptr_array(a,bound=4096):
    data,cap,size=pdx(a)
    if not 0<=size<=cap<=max(bound,100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data+8*j,8))[0] for j in range(size)]

r=LoadedReader(p.read, cls)
armies,aev=own_armies(r,co)
groups,gev=own_army_groups(r,co)
leaders,lev=own_leaders(r,co)
plans,pev=own_plans(r,co)
units=[]
for ap in ptr_array(co+0x290,4096):
    uid=struct.unpack("<I", p.read(ap+0x1C,4))[0]
    fid,_=unit_formation_army_id(r,ap)
    gid,_=unit_formation_army_group_id(r,ap)
    units.append({"unit_id":uid,"army_id":fid,"army_group_id":gid,"path":unit_movement_path(r,ap)})
summary=read_campaign_summary(p,gs)
out={
    "pid":p.pid,
    "date": (summary.get("verified") or {}).get("date_full") or (summary.get("verified") or {}).get("date"),
    "pause": p.read(idler+0x6C1,1)[0],
    "speed": struct.unpack("<i", p.read(gs+0x4BC,4))[0],
    "armies":armies,"armies_ev":aev,
    "army_groups":groups,"army_groups_ev":gev,
    "plans":plans,"plans_ev":pev,
    "assigned":[x for x in leaders if x.get("assigned_to")],
    "units_with_formation":[u for u in units if u["army_id"] is not None or u["army_group_id"] is not None],
    "keep_1829": next(u for u in units if u["unit_id"]==1829),
}
Path("research/t193_live_fields.json").write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
print(json.dumps(out,indent=2,ensure_ascii=False,default=str))
p.close()
