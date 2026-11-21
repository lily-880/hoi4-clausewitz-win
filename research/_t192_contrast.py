from __future__ import annotations
import json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
GROUP = 0x26d2b077020

def is_ptr(x):
    return type(x) is int and 0x100000000 < x < 0x7FFFFFFFFFFF

def pdx(p, a):
    data, cap, size = struct.unpack("<QII", p.read(a, 16))
    return data, cap, size

def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data+8*j, 8))[0] for j in range(size)]

def cls(p, pe, a):
    if not is_ptr(a):
        return None
    vt = struct.unpack("<Q", p.read(a, 8))[0]
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)

p = Proc(mem_find_pid("hoi4.exe"))
pe = PE(EXE)
session = detect_session(p, pe)
gs = int(session["signals"]["gs_ptr"], 16)
co = int(resolve_player_country(p, gs)["country_ptr"], 16)

rows = []
for ap in ptr_array(p, co+0x290, 4096):
    uid = struct.unpack("<I", p.read(ap+0x1C, 4))[0]
    c0 = struct.unpack("<Q", p.read(ap+0xC0, 8))[0]
    off750 = struct.unpack("<Q", p.read(ap+0x750, 8))[0]
    rec = {
        "id": uid,
        "ptr": hex(ap),
        "plus_c0": hex(c0),
        "plus_c0_class": cls(p, pe, c0),
        "plus_c0_is_group": c0 == GROUP,
        "plus_c0_handle": struct.unpack("<II", p.read(c0+8, 8)) if is_ptr(c0) and cls(p,pe,c0) else None,
        "plus_750": hex(off750),
        "plus_750_is_group": off750 == GROUP,
        "plus_750_class": cls(p, pe, off750) if is_ptr(off750) else None,
    }
    rows.append(rec)

# leaders +0x1048 contrast
cc = struct.unpack("<Q", p.read(co+0xFF0, 8))[0]
leaders = ptr_array(p, cc+0x70, 512)
lrows = []
for lp in leaders:
    htype, hid = struct.unpack("<II", p.read(lp+8, 8))
    asg_t, asg_id = struct.unpack("<II", p.read(lp+0x1048, 8))
    deployed = p.read(lp+0x1068, 1)[0]
    hq = struct.unpack("<Q", p.read(lp+0x1058, 8))[0]
    lrows.append({
        "leader_id": hid,
        "handle_type": htype,
        "assigned_handle": [asg_t, asg_id],
        "deployed": deployed,
        "deploy_hq_1058": hex(hq),
        "is_312": hid==312,
    })

# members this-adjust confirm
tp = ptr_array(p, co+0x168, 64)[0]
ogs = ptr_array(p, tp+0x80, 256)
gp = ogs[0]
mems = ptr_array(p, gp+0x50, 256)
member_resolve = []
for mp in mems:
    # try this-adjust 0xB8
    primary = mp - 0xB8
    member_resolve.append({
        "member_ptr": hex(mp),
        "member_class": cls(p, pe, mp),
        "primary": hex(primary),
        "primary_class": cls(p, pe, primary),
        "primary_handle": struct.unpack("<II", p.read(primary+0x18, 8)) if is_ptr(primary) else None,
        "primary_id_1c": struct.unpack("<I", p.read(primary+0x1C, 4))[0] if is_ptr(primary) else None,
        "back_c0": hex(struct.unpack("<Q", p.read(primary+0xC0, 8))[0]) if is_ptr(primary) else None,
    })

# 1837 +0x740..0x760 context
u1837 = next(r for r in rows if r["id"]==1837)
ap = int(u1837["ptr"], 16)
ctx = []
blob = p.read(ap+0x730, 0x40)
for i in range(0, 0x40, 8):
    q = struct.unpack_from("<Q", blob, i)[0]
    ctx.append({"off": hex(0x730+i), "val": hex(q), "class": cls(p, pe, q)})

out = {
    "units_c0_750": rows,
    "c0_group_units": [r["id"] for r in rows if r["plus_c0_is_group"]],
    "c0_nonzero": [r for r in rows if int(r["plus_c0"],16) != 0],
    "750_group_units": [r["id"] for r in rows if r["plus_750_is_group"]],
    "leaders_1048": lrows,
    "leaders_assigned_nonzero": [x for x in lrows if x["assigned_handle"] != [0,0]],
    "member_resolve": member_resolve,
    "u1837_750_context": ctx,
}
Path("research/t192_contrast.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
print(json.dumps({
    "c0_group_units": out["c0_group_units"],
    "c0_nonzero": out["c0_nonzero"],
    "750_group_units": out["750_group_units"],
    "u1837_750_context": ctx,
    "leaders_assigned_nonzero": out["leaders_assigned_nonzero"],
    "leaders_unassigned_sample": [x for x in lrows if x["assigned_handle"]==[0,0]][:3],
    "unassigned_count": sum(1 for x in lrows if x["assigned_handle"]==[0,0]),
    "member_resolve": member_resolve,
}, indent=2, ensure_ascii=False, default=str))
p.close()

