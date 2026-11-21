import os, sys, json, struct, time
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from clock import ui_date, ui_hour
from gamestate import (
    _pdx_array, resolve_player_country, read_campaign_summary, detect_session
)
from country_tags import tag_for_index
from handle import HANDLE_TYPE_ARMY

OUT = Path("research/_t142_own_units.json")
CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_PROVINCE = O.HYPOTHESIS_STRUCT.get("CA_PROVINCE", 0x1F0)
CA_DIV_TEMPLATE = O.HYPOTHESIS_STRUCT.get("CA_DIV_TEMPLATE", 0x3B8)
CA_NAME_MEMBER = 0x340
CNG_DISPLAY_NAME = 0x60
CP_ID = 0xA4
TMPL_NAME = 0x20

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])

def u32(a):
    b = p.try_read(a, 4)
    return struct.unpack_from("<I", b, 0)[0] if b else None
def i32(a):
    b = p.try_read(a, 4)
    return struct.unpack_from("<i", b, 0)[0] if b else None
def u64(a):
    b = p.try_read(a, 8)
    return struct.unpack_from("<Q", b, 0)[0] if b else None

def looks_ptr(x):
    return bool(x) and 0x10000 < x < 0x7FFFFFFFFFFF

def read_utf8(addr, n=128):
    b = p.try_read(addr, n)
    if not b:
        return None
    s = b.split(b"\0", 1)[0]
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
    """Best-effort Clausewitz/SSO string at addr: pointer or inline."""
    if not addr:
        return None
    ptr = u64(addr)
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s:
            return s
    return read_utf8(addr)

def read_tmpl_name(army_ptr):
    tmpl = u64(army_ptr + CA_DIV_TEMPLATE)
    if not tmpl:
        return None, None
    return tmpl, read_pdx_string(tmpl + TMPL_NAME)

def read_unit_name(army_ptr):
    member = u64(army_ptr + CA_NAME_MEMBER)
    if not looks_ptr(member):
        return None
    return read_pdx_string(member + CNG_DISPLAY_NAME)

resolved = resolve_player_country(p, gs)
summary = read_campaign_summary(p, gs)
player_index = resolved.get("player_index")
player_tag = resolved.get("tag") or tag_for_index(player_index)
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
cptr = u64(countries["data"] + player_index * 8) if countries and player_index is not None else 0
armies = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_ARMIES"]) if cptr else None

own_units = []
skipped = []
if armies and armies.get("data"):
    for slot in range(armies["size"]):
        ap = u64(armies["data"] + slot * 8)
        if not ap:
            skipped.append({"slot": slot, "reason": "null CArmy*"})
            continue
        h_ty = u32(ap + CA_HANDLE)
        h_ix = u32(ap + CA_HANDLE + 4)
        prov = u32(ap + CA_PROVINCE_ID)
        owner_index = i32(ap + CA_COUNTRY_TAG)
        pref = u64(ap + CA_PROVINCE)
        pid_a4 = u32(pref + CP_ID) if looks_ptr(pref) else None
        tmpl_ptr, tmpl_name = read_tmpl_name(ap)
        unit = {
            "unit_id": h_ix,
            "province_id": prov,
            "owner": {"index": owner_index},
            "relation_to_player": "self",
        }
        if player_tag and owner_index == player_index:
            unit["owner"]["tag"] = player_tag
        elif owner_index is not None:
            t = tag_for_index(owner_index)
            if t:
                unit["owner"]["tag"] = t
        name = read_unit_name(ap)
        if name:
            unit["name"] = name
        if tmpl_name:
            unit["template"] = {"name": tmpl_name}
        # provenance for this capture only (not part of Unit schema)
        unit["_read"] = {
            "slot": slot,
            "army_ptr": hex(ap),
            "handle_type": h_ty,
            "handle_ok": h_ty == HANDLE_TYPE_ARMY and h_ix is not None,
            "province_id_crosscheck_ok": pid_a4 == prov,
        }
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
        "allow_write": False,
        "geography_scope": None,
    },
    "world": {"own_units": [{k: v for k, v in u.items() if k != "_read"} for u in own_units]},
    "coverage": {
        "source": "CO_ARMIES of the country currently at GS+0x520",
        "armies_array_size": None if not armies else armies["size"],
        "captured": len(own_units),
        "filled": ["unit_id", "name?", "province_id", "owner", "relation_to_player", "template.name?"],
        "omitted_unproven": unread,
        "note": (
            "unit_id is CArmy handle index (type 0x33). province_id is CArmy+0x28, "
            "cross-checked with CProvince+0xA4. name is CArmy+0x340->CNameGroupMember+0x60. "
            "template.name is CReferencedDivisionTemplate+0x20. "
            "organization/strength/supply/in_combat/order/formation/leader are not proven on this Windows build; omitted, not invented."
        ),
    },
    "_debug": {
        "skipped": skipped,
        "handle_ok_count": sum(1 for u in own_units if u["_read"]["handle_ok"]),
        "province_crosscheck_ok_count": sum(1 for u in own_units if u["_read"]["province_id_crosscheck_ok"]),
        "named_count": sum(1 for u in own_units if "name" in {k: v for k, v in u.items() if k != "_read"} or u.get("name")),
        "units_with_read": own_units,
    },
}
# named_count fix
envelope["_debug"]["named_count"] = sum(1 for u in envelope["world"]["own_units"] if u.get("name"))
envelope["_debug"]["templated_count"] = sum(1 for u in envelope["world"]["own_units"] if u.get("template"))
OUT.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
# compact print for operator
brief = {
    "player": envelope["meta"]["player_country"],
    "game_time": envelope["meta"]["game_time"],
    "speed_notch": envelope["meta"]["game_speed_notch"],
    "count": envelope["coverage"]["captured"],
    "array_size": envelope["coverage"]["armies_array_size"],
    "handle_ok": envelope["_debug"]["handle_ok_count"],
    "prov_ok": envelope["_debug"]["province_crosscheck_ok_count"],
    "named": envelope["_debug"]["named_count"],
    "templated": envelope["_debug"]["templated_count"],
    "units": envelope["world"]["own_units"],
}
print(json.dumps(brief, ensure_ascii=False, indent=2))
p.close()
