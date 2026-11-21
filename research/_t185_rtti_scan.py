import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base

# Probe candidate vtable starts around 0x29d7030 and 0x19eeaa0 neighborhood
cands=[]
for rva in range(0x29d6d80, 0x29d7200, 8):
    name=_rtti_name_from_vtable(pe, rva)
    if name:
        cands.append((hex(rva), name))
print("RTTI near 0x29d6d80-7200:")
for c in cands:
    print(" ", c)

# Also search all RTTI names containing Combat, Order, Supply, Isolated
# We can walk complete object locators / type descriptors by scanning for .?AV
# This might be large; filter Combat/InCombat/Supply/Isolated/Order
pat=re.compile(rb"\.\?AV[A-Za-z0-9_]*@@")
found=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in pat.finditer(blob):
        name=m.group().decode("ascii", "replace")
        if any(k in name.lower() for k in ("combat","supply","isolat","in_combat","order","commandlist","encircl")):
            found.append((hex(s.virtual_address+m.start()), name))
print("\nRTTI names of interest (first 80):", len(found))
for x in found[:80]:
    print(" ", x)

# uniquely interesting
print("\n--- combat-ish class names ---")
for x in found:
    n=x[1].lower()
    if "combat" in n or "isolat" in n or "insupply" in n or "in_supply" in n:
        print(x)
