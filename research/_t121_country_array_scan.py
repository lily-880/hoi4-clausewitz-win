# Read-only: scan player CCountry for CPdxArray-like slots; compare to known vtables.
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__)) if False else os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "calling"))
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"

import config
import offsets as O
from gamestate import _pdx_array, _rtti_name_from_vtable
from mem import Proc, find_pid
from pe import PE

KNOWN_VT = {}
for k, v in O.PROVEN_STATIC.items():
    if isinstance(v, int) and "vtable" in k.lower():
        KNOWN_VT[v] = k
    elif isinstance(v, (list, tuple)) and "vtable" in k.lower():
        for item in v:
            if isinstance(item, int):
                KNOWN_VT[item] = k

pid = find_pid(config.EXE_NAME)
if not pid:
    raise SystemExit("hoi4.exe not running")
p = Proc(pid)
pe = None
try:
    dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    pe = PE(dump if os.path.isfile(dump) else (p.image_path or ""))
except Exception:
    pe = None

ggs = O.WINDOWS_GLOBALS["G_GAMESTATE"]
gs_ptr = p.u64(p.base + ggs)
countries = _pdx_array(p, gs_ptr + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
tag = struct.unpack_from("<i", p.try_read(gs_ptr + O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"], 4), 0)[0]
cptr = struct.unpack_from("<Q", p.try_read(countries["data"] + tag * 8, 8) or b"\0" * 8, 0)[0]


def first_elem_info(arr):
    if not arr or not arr.get("data"):
        return None
    elem = struct.unpack_from("<Q", p.try_read(arr["data"], 8) or b"\0" * 8, 0)[0]
    if not elem:
        return {"elem": None}
    raw = p.try_read(elem, 8)
    if not raw:
        return {"elem": hex(elem), "vt": None}
    vt = struct.unpack_from("<Q", raw, 0)[0]
    vt_rva = (vt - p.base) if (vt and p.base <= vt < p.base + p.image_size) else None
    rtti = _rtti_name_from_vtable(pe, vt_rva) if (pe is not None and vt_rva is not None) else None
    return {
        "elem": hex(elem),
        "vt_rva": hex(vt_rva) if vt_rva is not None else None,
        "known_vt": KNOWN_VT.get(vt_rva) if vt_rva is not None else None,
        "rtti": rtti,
    }


def array_vtable_census(arr, limit=32):
    counts = {}
    n = min(arr["size"], limit)
    for i in range(n):
        raw = p.try_read(arr["data"] + i * 8, 8)
        if not raw:
            counts["unreadable"] = counts.get("unreadable", 0) + 1
            continue
        elem = struct.unpack_from("<Q", raw, 0)[0]
        if not elem:
            counts["null"] = counts.get("null", 0) + 1
            continue
        vtr = p.try_read(elem, 8)
        if not vtr:
            counts["no_vt"] = counts.get("no_vt", 0) + 1
            continue
        vt = struct.unpack_from("<Q", vtr, 0)[0]
        vt_rva = (vt - p.base) if (vt and p.base <= vt < p.base + p.image_size) else None
        key = KNOWN_VT.get(vt_rva) if vt_rva is not None else (hex(vt_rva) if vt_rva is not None else "non_image_vt")
        counts[key] = counts.get(key, 0) + 1
    return counts


hits = []
for off in range(0, 0x800, 8):
    arr = _pdx_array(p, cptr + off)
    if not arr:
        continue
    size, cap, data = arr["size"], arr["capacity"], arr["data"]
    if not (1 <= size <= 2000 and size <= cap <= 4000):
        continue
    if not (0x10000 < data < 0x7FFFFFFFFFFF):
        continue
    info = {
        "offset": hex(off),
        "size": size,
        "capacity": cap,
        "data": hex(data),
        "first": first_elem_info(arr),
    }
    known_names = {
        0x168: "CO_THEATRES",
        0x1B8: "CO_DIV_TEMPLATES",
        0x278: "CO_FLEETS",
        0x290: "CO_ARMIES",
        0x460: "CO_STATES",
        0x548: "CO_CONTROLLER_AREAS",
        0x560: "CO_OWNER_AREAS",
        0x5D0: "CO_MODIFIERS",
    }
    if off in known_names:
        info["known"] = known_names[off]
        info["census"] = array_vtable_census(arr)
    elif size in (4, 17, 21) or (info["first"] and info["first"].get("known_vt") in ("CArmy_vtable", "CArmyGroup_vtable", "CUnit_vtable")):
        info["census"] = array_vtable_census(arr)
    # keep all plausible arrays, but mark interesting
    info["interesting"] = bool(
        size in (4, 17, 21)
        or off in known_names
        or (info["first"] and info["first"].get("known_vt") in ("CArmy_vtable", "CArmyGroup_vtable", "CUnit_vtable"))
    )
    hits.append(info)

# Theatre armies
th_arr = _pdx_array(p, cptr + 0x168)
th_armies = None
if th_arr and th_arr["size"] > 0:
    th_ptr = struct.unpack_from("<Q", p.try_read(th_arr["data"], 8) or b"\0" * 8, 0)[0]
    if th_ptr:
        tarr = _pdx_array(p, th_ptr + 0x68)
        if tarr:
            th_armies = {
                "theatre_ptr": hex(th_ptr),
                "size": tarr["size"],
                "capacity": tarr["capacity"],
                "first": first_elem_info(tarr),
                "census": array_vtable_census(tarr) if 0 < tarr["size"] <= 2000 else None,
            }

# Compare CO_ARMIES pointer set vs any size-21 array
army_arr = _pdx_array(p, cptr + 0x290)
army_ptrs = set()
if army_arr:
    for i in range(army_arr["size"]):
        raw = p.try_read(army_arr["data"] + i * 8, 8)
        if raw:
            army_ptrs.add(struct.unpack_from("<Q", raw, 0)[0])

size21 = [h for h in hits if h["size"] == 21]
overlap = []
for h in size21:
    arr = _pdx_array(p, cptr + int(h["offset"], 16))
    ptrs = []
    for i in range(arr["size"]):
        raw = p.try_read(arr["data"] + i * 8, 8)
        ptrs.append(struct.unpack_from("<Q", raw, 0)[0] if raw else 0)
    overlap.append({
        "offset": h["offset"],
        "shared_with_CO_ARMIES": len(set(ptrs) & army_ptrs),
        "only_here": len(set(ptrs) - army_ptrs),
        "only_armies": len(army_ptrs - set(ptrs)),
    })

out = {
    "pid": pid,
    "player_index": tag,
    "country_ptr": hex(cptr),
    "plausible_arrays": hits,
    "interesting": [h for h in hits if h.get("interesting")],
    "th_armies": th_armies,
    "size21_overlap_with_CO_ARMIES": overlap,
    "co_armies_census": next((h.get("census") for h in hits if h.get("known") == "CO_ARMIES"), None),
}
path = os.path.join(ROOT, "research", "_t121_country_array_scan.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("wrote", path)
print(json.dumps({
    "player_index": tag,
    "n_plausible": len(hits),
    "interesting": out["interesting"],
    "th_armies": th_armies,
    "size21_overlap_with_CO_ARMIES": overlap,
    "sizes": sorted({(h["offset"], h["size"], h.get("known"), (h.get("first") or {}).get("known_vt")) for h in hits}),
}, ensure_ascii=False, indent=2))
