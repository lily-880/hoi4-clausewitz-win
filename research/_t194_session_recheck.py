from __future__ import annotations
import json, struct, sys
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from input_loaded_fields import (
    LoadedReader, own_armies, own_army_groups, own_leaders, own_plans,
    unit_formation_army_id, unit_formation_army_group_id, unit_movement_path,
)

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 26976
EXPECTED_GS = 0x26C259D0FF0
EXPECTED_CO = 0x26C4B672530

p = Proc(mem_find_pid("hoi4.exe"))
pe = PE(EXE)
session = detect_session(p, pe)
gs = int(session["signals"]["gs_ptr"], 16)
co = int(resolve_player_country(p, gs)["country_ptr"], 16)
idler = int(session["signals"].get("idler_ptr") or "0", 16)
summary = read_campaign_summary(p, gs)
ver = summary.get("verified") or {}

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF

def cls(a):
    if not is_ptr(a):
        return None
    try:
        vt = struct.unpack("<Q", p.read(a, 8))[0]
    except OSError:
        return None
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)

def pdx(a):
    return struct.unpack("<QII", p.read(a, 16))

def ptr_array(a, bound=4096):
    data, cap, size = pdx(a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return {"data": hex(data), "cap": cap, "size": size, "items": []}
    items = [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]
    return {"data": hex(data), "cap": cap, "size": size, "items": items}

def u32_array(a, bound=64):
    data, cap, size = pdx(a)
    if size <= 0 or not is_ptr(data) or size > bound:
        return {"data": hex(data), "cap": cap, "size": size, "items": []}
    raw = p.read(data, size * 4)
    return {"data": hex(data), "cap": cap, "size": size, "items": list(struct.unpack("<" + "I" * size, raw))}

def handle_at(a):
    t, i = struct.unpack("<II", p.read(a, 8))
    return [t, i]

def snap_unit(ap):
    uid = struct.unpack("<I", p.read(ap + 0x1C, 4))[0]
    prov = struct.unpack("<I", p.read(ap + 0x28, 4))[0]
    path = u32_array(ap + 0x200)
    full = u32_array(ap + 0x220)
    prog = struct.unpack("<f", p.read(ap + 0x240, 4))[0]
    cmd = ptr_array(ap + 0x2C0)
    cmd_elems = []
    for c in cmd["items"]:
        ev = {"ptr": hex(c), "class": cls(c)}
        if is_ptr(c):
            ev["plus8"] = struct.unpack("<I", p.read(c + 8, 4))[0]
            ev["head16"] = p.read(c, 16).hex()
        cmd_elems.append(ev)
    return {
        "ptr": hex(ap),
        "class": cls(ap),
        "unit_id": uid,
        "province": prov,
        "path": path["items"],
        "full_path": full["items"],
        "progress": prog,
        "commandlist_size": cmd["size"],
        "commandlist": cmd_elems,
        "field_564": struct.unpack("<Q", p.read(ap + 0x564, 8))[0] if True else None,
    }

def snap_instance(ip):
    typ = struct.unpack("<I", p.read(ip + 0x30, 4))[0]
    inst = struct.unpack("<I", p.read(ip + 0x244, 4))[0]
    can = p.read(ip + 0x248, 1)[0]
    path = u32_array(ip + 0x70)
    states = u32_array(ip + 0xE0)
    # interesting dwords / qwords around known fields
    interesting = {}
    for off in (0x20, 0x24, 0x28, 0x30, 0x34, 0x38, 0x3C, 0x50, 0x90, 0x220, 0x224, 0x228, 0x22C,
                0x240, 0x244, 0x248, 0x24C, 0x250, 0x254, 0x258, 0x25C, 0x260, 0x264, 0x268, 0x270):
        interesting[hex(off)] = struct.unpack("<I", p.read(ip + off, 4))[0]
    # member / assigned unit arrays: search a few known candidate pdx arrays
    arrays = {}
    for off in (0x38, 0x40, 0x48, 0x50, 0x58, 0x60, 0x70, 0x80, 0x98, 0xB0, 0xC8, 0xE0, 0xF8, 0x110, 0x128, 0x140, 0x280, 0x298, 0x2B0, 0x2C8, 0x2E0, 0x2F8, 0x310):
        try:
            data, cap, size = pdx(ip + off)
        except Exception:
            continue
        if 0 <= size <= cap <= 64 and (size == 0 or is_ptr(data)):
            item_preview = None
            if size and is_ptr(data):
                # try u32s and ptrs
                raw = p.read(data, min(size, 8) * 8)
                item_preview = raw.hex()
            arrays[hex(off)] = {"data": hex(data), "cap": cap, "size": size, "preview": item_preview}
    return {
        "ptr": hex(ip),
        "class": cls(ip),
        "type_30": typ,
        "instance_id_244": inst,
        "can_execute_248": can,
        "path_70": path,
        "states_e0": states,
        "dwords": interesting,
        "arrays": arrays,
        "qword_258": hex(struct.unpack("<Q", p.read(ip + 0x258, 8))[0]),
    }

# theatre walk
theatre = None
# CCountry theatres typically at a known offset; reuse own_* which already works
r = LoadedReader(p.read, cls)
armies, aev = own_armies(r, co)
groups, gev = own_army_groups(r, co)
leaders, lev = own_leaders(r, co)
plans, pev = own_plans(r, co)

units = []
unit_1829 = unit_1838 = None
for ap in ptr_array(co + 0x290, 4096)["items"]:
    uid = struct.unpack("<I", p.read(ap + 0x1C, 4))[0]
    if uid in (1829, 1838):
        snap = snap_unit(ap)
        if uid == 1829:
            unit_1829 = snap
        else:
            unit_1838 = snap

# find army 1 and its instances
# walk CTheatre via country - look at first army from own_armies evidence if needed
# locate COrdersGroup for army 1 via unit 1838 +0xC0
og = None
instances = []
if unit_1838:
    og_ptr = struct.unpack("<Q", p.read(int(unit_1838["ptr"], 16) + 0xC0, 8))[0]
    og = {
        "ptr": hex(og_ptr),
        "class": cls(og_ptr),
        "handle": handle_at(og_ptr + 0x8) if is_ptr(og_ptr) else None,
        "leader": handle_at(struct.unpack("<Q", p.read(og_ptr + 0x88, 8))[0] + 0x18) if is_ptr(struct.unpack("<Q", p.read(og_ptr + 0x88, 8))[0]) else None,
        "parent_1b8": hex(struct.unpack("<Q", p.read(og_ptr + 0x1B8, 8))[0]),
    }
    arr = ptr_array(og_ptr + 0x98)
    og["order_instances_meta"] = {k: arr[k] for k in ("data", "cap", "size")}
    for ip in arr["items"]:
        instances.append(snap_instance(ip))

# leaders unassigned for possible unit assign
unassigned = []
for row in leaders:
    if not row.get("assigned_to"):
        unassigned.append({"leader_id": row.get("leader_id") or row.get("id"), "name": row.get("name") or row.get("token")})

out = {
    "pid": p.pid,
    "pid_ok": p.pid == EXPECTED_PID,
    "gs": hex(gs),
    "gs_ok": gs == EXPECTED_GS,
    "co": hex(co),
    "co_ok": co == EXPECTED_CO,
    "idler": hex(idler),
    "date": ver.get("date_full") or ver.get("date"),
    "hour_tick": (ver.get("date_full") or {}).get("hour_tick") if isinstance(ver.get("date_full"), dict) else ver.get("hour_tick"),
    "pause": p.read(idler + 0x6C1, 1)[0],
    "speed_index": struct.unpack("<i", p.read(gs + 0x4BC, 4))[0],
    "hour_progress": struct.unpack("<f", p.read(gs + 0x4B8, 4))[0],
    "armies": armies,
    "army_groups": groups,
    "plans": plans,
    "assigned": [x for x in leaders if x.get("assigned_to")],
    "unassigned_leader_ids": [u["leader_id"] for u in unassigned][:8],
    "unassigned_sample": unassigned[:8],
    "unit_1829": unit_1829,
    "unit_1838": unit_1838,
    "orders_group": og,
    "instances": instances,
    "process_exit": "alive",
}
Path("research/t194_session_recheck.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
p.close()
