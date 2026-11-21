import os, sys, json, struct, time, collections
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import (
    _pdx_array, resolve_player_country, read_campaign_summary, _rtti_name_from_vtable
)
from country_tags import tag_for_index
from handle import resolve_handle, HANDLE_TYPE_ARMY
from pe import PE

OUT = Path("research/_t143_own_units.json")
CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_SUBUNIT_DEF = O.HYPOTHESIS_STRUCT.get("CA_SUBUNIT_DEF", 0x138)
CA_PROVINCE = O.HYPOTHESIS_STRUCT.get("CA_PROVINCE", 0x1F0)
CA_DIV_TEMPLATE = O.HYPOTHESIS_STRUCT.get("CA_DIV_TEMPLATE", 0x3B8)
CA_NAME_MEMBER = 0x340
CNG_DISPLAY_NAME = 0x60
CP_ID = 0xA4
TMPL_NAME = 0x20

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
exe = getattr(p, "image_path", None) or r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(exe)

class Backend:
    def __init__(self, proc):
        self._p = proc
        self.image_base = proc.base
    def read(self, a, n):
        b = self._p.try_read(a, n)
        if not b or len(b) < n:
            raise OSError("short")
        return b

b = Backend(p)

def u32(a):
    x = p.try_read(a, 4)
    return struct.unpack_from("<I", x, 0)[0] if x else None
def i32(a):
    x = p.try_read(a, 4)
    return struct.unpack_from("<i", x, 0)[0] if x else None
def u64(a):
    x = p.try_read(a, 8)
    return struct.unpack_from("<Q", x, 0)[0] if x else None
def looks_ptr(x):
    return bool(x) and 0x10000 < x < 0x7FFFFFFFFFFF
def read_utf8(addr, n=128):
    raw = p.try_read(addr, n)
    if not raw:
        return None
    s = raw.split(b"\0", 1)[0]
    if not s:
        return None
    try:
        t = s.decode("utf-8")
    except Exception:
        return None
    if not all(ch.isprintable() or ch in " \t" for ch in t):
        return None
    return t or None
def read_pdx_string(addr):
    if not addr:
        return None
    ptr = u64(addr)
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s:
            return s
    return read_utf8(addr)
def read_tmpl_name(ap):
    tmpl = u64(ap + CA_DIV_TEMPLATE)
    if not looks_ptr(tmpl):
        return None, None
    return tmpl, read_pdx_string(tmpl + TMPL_NAME)
def read_unit_name(ap):
    member = u64(ap + CA_NAME_MEMBER)
    if not looks_ptr(member):
        return None
    return read_pdx_string(member + CNG_DISPLAY_NAME)
def rtti_from_vt(vt):
    if not vt or vt < p.base:
        return None
    try:
        name = _rtti_name_from_vtable(pe, vt - p.base)
    except Exception:
        return None
    if name and name.startswith(".?AV") and name.endswith("@@"):
        return name[4:-2]
    return name
def class_name(ap):
    return rtti_from_vt(u64(ap))

resolved = resolve_player_country(p, gs)
summary = read_campaign_summary(p, gs)
player_index = resolved.get("player_index")
player_tag = resolved.get("tag") or tag_for_index(player_index)
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
cptr = u64(countries["data"] + player_index * 8) if countries and player_index is not None else 0
armies = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_ARMIES"]) if cptr else None
theatres = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_THEATRES"]) if cptr else None

co_ptrs = []
if armies and armies.get("data"):
    for slot in range(armies["size"]):
        ap = u64(armies["data"] + slot * 8)
        if ap:
            co_ptrs.append(ap)
th_army_ptrs = []
th_info = []
if theatres and theatres.get("data"):
    for i in range(theatres["size"]):
        th = u64(theatres["data"] + i * 8)
        arr = _pdx_array(p, th + O.HYPOTHESIS_STRUCT["TH_ARMIES"]) if th else None
        rec = {"i": i, "th": hex(th) if th else None, "size": None if not arr else arr["size"], "cap": None if not arr else arr["capacity"]}
        th_info.append(rec)
        if arr and arr.get("data"):
            for j in range(arr["size"]):
                th_army_ptrs.append(u64(arr["data"] + j * 8))

def owner_obj(owner_index):
    obj = {"index": owner_index}
    t = player_tag if owner_index == player_index else tag_for_index(owner_index)
    if t:
        obj["tag"] = t
    return obj

def unit_from(ap, slot=None):
    h_ty = u32(ap + CA_HANDLE)
    h_ix = u32(ap + CA_HANDLE + 4)
    prov = u32(ap + CA_PROVINCE_ID)
    owner_index = i32(ap + CA_COUNTRY_TAG)
    pref = u64(ap + CA_PROVINCE)
    pid_a4 = u32(pref + CP_ID) if looks_ptr(pref) else None
    tmpl_ptr, tmpl_name = read_tmpl_name(ap)
    cls = class_name(ap)
    unit = {
        "unit_id": h_ix,
        "province_id": prov,
        "owner": owner_obj(owner_index),
        "relation_to_player": "self" if owner_index == player_index else "unknown",
    }
    name = read_unit_name(ap)
    if name:
        unit["name"] = name
    if tmpl_name:
        unit["template"] = {"name": tmpl_name}
    unit["_read"] = {
        "slot": slot,
        "army_ptr": hex(ap),
        "rtti": cls,
        "handle_type": h_ty,
        "handle_ok": h_ty == HANDLE_TYPE_ARMY and h_ix is not None,
        "province_id_crosscheck_ok": pid_a4 == prov,
        "in_co_armies": ap in co_ptrs,
        "in_th_armies": ap in th_army_ptrs,
        "has_subunit_def": looks_ptr(u64(ap + CA_SUBUNIT_DEF)),
        "has_province": looks_ptr(pref),
        "has_template": looks_ptr(tmpl_ptr),
    }
    return unit

# Handle-table hunt + RTTI classification
vt_counts = collections.Counter()
carmy_by_country = collections.Counter()
player_taskforces = 0
player_other = []
hunt_carmies = []
seen = set()
for ix in range(1, 20001):
    try:
        obj = resolve_handle(b, HANDLE_TYPE_ARMY, ix, p.base)
    except Exception:
        continue
    if not obj or obj in seen:
        continue
    seen.add(obj)
    vt = u64(obj)
    rva = (vt - p.base) if vt and vt >= p.base else None
    key = hex(rva) if rva is not None else hex(vt or 0)
    vt_counts[key] += 1
    cls = rtti_from_vt(vt)
    tag = i32(obj + CA_COUNTRY_TAG)
    is_carmy = cls == "CArmy" or (cls is None and rva in (0x29d6d98, 0x29d6d68, 0x29D6D68))
    if is_carmy:
        carmy_by_country[tag] += 1
        if tag == player_index:
            hunt_carmies.append(obj)
    elif tag == player_index:
        if cls == "CTaskForce":
            player_taskforces += 1
        else:
            player_other.append({"unit_id": u32(obj + CA_HANDLE + 4), "ptr": hex(obj), "rtti": cls, "vt_rva": key})

# Prefer CO_ARMIES order; append any CArmy found only in the handle table
own_units = []
skipped = []
seen_units = set()
if armies and armies.get("data"):
    for slot in range(armies["size"]):
        ap = u64(armies["data"] + slot * 8)
        if not ap:
            skipped.append({"slot": slot, "reason": "null CArmy*"})
            continue
        unit = unit_from(ap, slot=slot)
        cls = unit["_read"]["rtti"]
        if cls and cls != "CArmy":
            skipped.append({"slot": slot, "reason": "not CArmy", "rtti": cls, "unit_id": unit.get("unit_id")})
            continue
        own_units.append(unit)
        seen_units.add(ap)
for ap in hunt_carmies:
    if ap in seen_units:
        continue
    unit = unit_from(ap)
    unit["_read"]["found_only_in_handle_table"] = True
    own_units.append(unit)

fields = summary.get("fields") or {}
date_full = fields.get("date_full") or {}
ui = date_full.get("ui") or ""
year = month = day = None
if ui and len(ui.split("-")) == 3:
    year, month, day = (int(x) for x in ui.split("-"))

unread = [
    "organization",
    "strength",
    "supply",
    "in_combat",
    "combat_id",
    "order",
    "formation",
    "leader_id",
    "template.template_id",
    "template.battalions",
    "template.combat_width",
]

top_countries = []
for i, n in carmy_by_country.most_common(12):
    top_countries.append({"index": i, "tag": tag_for_index(i), "n": n})

vt_named = []
for k, c in vt_counts.most_common():
    try:
        rva = int(k, 16)
        name = rtti_from_vt(p.base + rva)
    except Exception:
        name = None
    vt_named.append({"vt_rva": k, "n": c, "rtti": name})

envelope = {
    "captured_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pid": p.pid,
    "meta": {
        "game_time": {
            "year": year,
            "month": month,
            "day": day,
            "hour": date_full.get("ui_hour") or fields.get("date_ui_hour"),
        },
        "player_country": {"index": player_index, "tag": player_tag},
        "game_speed_index": fields.get("game_speed_index"),
        "game_speed_notch": fields.get("game_speed_notch"),
        "game_hour_progress": fields.get("game_hour_progress"),
        "allow_write": False,
        "geography_scope": None,
    },
    "world": {"own_units": [{k: v for k, v in u.items() if k != "_read"} for u in own_units]},
    "coverage": {
        "source": "CO_ARMIES of the country at GS+0x520, plus HANDLE_TYPE_ARMY CArmy confirmed by RTTI",
        "armies_array_size": None if not armies else armies["size"],
        "armies_array_capacity": None if not armies else armies.get("capacity"),
        "theatre_army_count": len(th_army_ptrs),
        "captured": len(own_units),
        "found_only_in_handle_table": sum(1 for u in own_units if u["_read"].get("found_only_in_handle_table")),
        "player_taskforces_excluded": player_taskforces,
        "filled": ["unit_id", "name?", "province_id", "owner", "relation_to_player", "template.name?"],
        "omitted_unproven": unread,
        "note": (
            "unit_id is CArmy handle index (type 0x33). province_id is CArmy+0x28, "
            "cross-checked with CProvince+0xA4. name is CArmy+0x340->CNameGroupMember+0x60. "
            "template.name is CReferencedDivisionTemplate+0x20. HANDLE_TYPE_ARMY also resolves "
            "CTaskForce (navy); those are excluded. organization/strength/supply/in_combat/"
            "order/formation/leader are not proven on this Windows build; omitted, not invented."
        ),
    },
    "_debug": {
        "skipped": skipped,
        "handle_ok_count": sum(1 for u in own_units if u["_read"]["handle_ok"]),
        "province_crosscheck_ok_count": sum(1 for u in own_units if u["_read"]["province_id_crosscheck_ok"]),
        "named_count": 0,
        "templated_count": 0,
        "theatres": th_info,
        "handle_hits_any": len(seen),
        "rtti_vt_counts": vt_named,
        "carmy_by_country_top": top_countries,
        "player_carmy_handle_count": carmy_by_country.get(player_index, 0),
        "player_other_army_handles": player_other,
        "units_with_read": own_units,
    },
}
envelope["_debug"]["named_count"] = sum(1 for u in envelope["world"]["own_units"] if u.get("name"))
envelope["_debug"]["templated_count"] = sum(1 for u in envelope["world"]["own_units"] if u.get("template"))
OUT.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
brief = {
    "pid": envelope["pid"],
    "player": envelope["meta"]["player_country"],
    "game_time": envelope["meta"]["game_time"],
    "speed_notch": envelope["meta"]["game_speed_notch"],
    "hour_progress": envelope["meta"]["game_hour_progress"],
    "count": envelope["coverage"]["captured"],
    "array_size": envelope["coverage"]["armies_array_size"],
    "array_cap": envelope["coverage"]["armies_array_capacity"],
    "th_army_count": envelope["coverage"]["theatre_army_count"],
    "handle_only": envelope["coverage"]["found_only_in_handle_table"],
    "taskforces_excluded": envelope["coverage"]["player_taskforces_excluded"],
    "handle_ok": envelope["_debug"]["handle_ok_count"],
    "prov_ok": envelope["_debug"]["province_crosscheck_ok_count"],
    "named": envelope["_debug"]["named_count"],
    "templated": envelope["_debug"]["templated_count"],
    "player_carmy_handle_count": envelope["_debug"]["player_carmy_handle_count"],
    "carmy_by_country_top": top_countries,
    "units": envelope["world"]["own_units"],
}
print(json.dumps(brief, ensure_ascii=False, indent=2))
p.close()
