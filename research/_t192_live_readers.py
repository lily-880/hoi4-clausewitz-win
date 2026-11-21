from __future__ import annotations
import json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from input_loaded_fields import LoadedReader, own_armies, unit_formation_army_id, own_leaders, unit_movement_path

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"

def is_ptr(x):
    return type(x) is int and 0x100000000 < x < 0x7FFFFFFFFFFF

def ptr_array(p, a, bound=4096):
    data, cap, size = struct.unpack("<QII", p.read(a, 16))
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data+8*j, 8))[0] for j in range(size)]

p = Proc(mem_find_pid("hoi4.exe"))
pe = PE(EXE)
session = detect_session(p, pe)
gs = int(session["signals"]["gs_ptr"], 16)
co = int(resolve_player_country(p, gs)["country_ptr"], 16)
idler = int(session["signals"].get("idler_ptr") or "0", 16)
summary = read_campaign_summary(p, gs)
ver = summary.get("verified") or {}

def class_name(a):
    vt = struct.unpack("<Q", p.read(a, 8))[0]
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)

r = LoadedReader(p.read, class_name)
armies, aev = own_armies(r, co)
leaders, lev = own_leaders(r, co)
units = []
for ap in ptr_array(p, co+0x290, 4096):
    uid = struct.unpack("<I", p.read(ap+0x1C, 4))[0]
    fid, fev = unit_formation_army_id(r, ap)
    path = unit_movement_path(r, ap)
    units.append({"unit_id": uid, "formation_army_id": fid, "path": path})

assigned = [x for x in leaders if x.get("assigned_to")]
out = {
    "pid": p.pid,
    "date": ver.get("date_full") or ver.get("date"),
    "pause_flag_6c1": p.read(idler+0x6C1, 1)[0] if idler else None,
    "speed_index": struct.unpack("<i", p.read(gs+0x4BC, 4))[0],
    "armies": armies,
    "armies_evidence": aev,
    "assigned_leaders": assigned,
    "leaders_n": len(leaders),
    "units_with_army": [u for u in units if u["formation_army_id"] is not None],
    "units_without_army": [u["unit_id"] for u in units if u["formation_army_id"] is None],
    "keep_1829": next(u for u in units if u["unit_id"]==1829),
}
Path("research/t192_live_fields.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
p.close()
