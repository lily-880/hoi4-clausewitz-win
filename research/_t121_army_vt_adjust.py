import json, os, struct, sys
sys.path.insert(0, os.path.join(os.getcwd(), "calling"))
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from gamestate import _pdx_array
from mem import Proc, find_pid

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
tag = struct.unpack_from("<i", p.try_read(gs + O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"], 4), 0)[0]
cptr = struct.unpack_from("<Q", p.try_read(countries["data"] + tag * 8, 8) or b"\0"*8, 0)[0]

CARM = O.PROVEN_STATIC["CArmy_vtable"]
CAG = O.PROVEN_STATIC["CArmyGroup_vtable"]
CARM_MI = set(O.PROVEN_STATIC["CArmy_vtable_mi"])
CAG_MI = set(O.PROVEN_STATIC["CArmyGroup_vtable_mi"])

def vt_rva(addr):
    raw = p.try_read(addr, 8)
    if not raw:
        return None
    vt = struct.unpack_from("<Q", raw, 0)[0]
    if p.base <= vt < p.base + p.image_size:
        return vt - p.base
    return None

def label(rva):
    if rva is None:
        return None
    if rva == CARM:
        return "CArmy_vtable"
    if rva in CARM_MI:
        return "CArmy_vtable_mi"
    if rva == CAG:
        return "CArmyGroup_vtable"
    if rva in CAG_MI:
        return "CArmyGroup_vtable_mi"
    return hex(rva)

armies = _pdx_array(p, cptr + 0x290)
rows = []
for i in range(armies["size"]):
    elem = struct.unpack_from("<Q", p.try_read(armies["data"] + i * 8, 8) or b"\0"*8, 0)[0]
    rec = {"i": i, "ptr": hex(elem) if elem else None}
    for delta, name in ((0, "at"), (-0x08, "m8"), (-0x10, "m10"), (-0x18, "m18"), (-0x20, "m20"), (-0x28, "m28"), (-0x30, "m30"), (-0x38, "m38"), (0x30, "p30")):
        rec[name] = label(vt_rva(elem + delta) if elem else None)
    rows.append(rec)

# 0x2e0 raw slots
arr = _pdx_array(p, cptr + 0x2e0)
raw4 = []
blob = p.try_read(arr["data"], arr["size"] * 8) or b""
for i in range(arr["size"]):
    q = struct.unpack_from("<Q", blob, i * 8)[0] if len(blob) >= (i+1)*8 else None
    lo, hi = (struct.unpack_from("<II", blob, i * 8) if len(blob) >= (i+1)*8 else (None, None))
    raw4.append({"i": i, "u64": hex(q) if q is not None else None, "lo": lo, "hi": hi})

# 0x4a8 vs states first ptr
st = _pdx_array(p, cptr + 0x460)
st_ptrs = set()
for i in range(st["size"]):
    st_ptrs.add(struct.unpack_from("<Q", p.try_read(st["data"] + i * 8, 8) or b"\0"*8, 0)[0])
a48 = _pdx_array(p, cptr + 0x4a8)
a48_ptrs = []
for i in range(a48["size"]):
    a48_ptrs.append(struct.unpack_from("<Q", p.try_read(a48["data"] + i * 8, 8) or b"\0"*8, 0)[0])

# unique army vtables at ptr
from collections import Counter
c = Counter(r["at"] for r in rows)

out = {
    "proven_CArmy_vtable": hex(CARM),
    "army_vt_at_ptr": dict(c),
    "armies": rows,
    "slot_0x2e0": raw4,
    "slot_0x4a8_vs_states": {
        "size": a48["size"],
        "shared_with_states": len(set(a48_ptrs) & st_ptrs),
        "only_here": len(set(a48_ptrs) - st_ptrs),
        "first_same_as_states": a48_ptrs[0] == next(iter([struct.unpack_from("<Q", p.try_read(st["data"], 8) or b"\0"*8, 0)[0]])) if a48_ptrs else False,
    },
}
path = os.path.join("research", "_t121_army_vt_adjust.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps({
    "proven_CArmy_vtable": out["proven_CArmy_vtable"],
    "army_vt_at_ptr": out["army_vt_at_ptr"],
    "first_three": rows[:3],
    "slot_0x2e0": raw4,
    "slot_0x4a8_vs_states": out["slot_0x4a8_vs_states"],
}, ensure_ascii=False, indent=2))
