import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
for s in pe.sections:
    print(f"  {s.name} va=0x{s.virtual_address:x} vsize=0x{s.virtual_size:x}")

rdata = [s for s in pe.sections if s.name==".rdata"][0]
data = pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
print("rdata bytes", len(data))

names=set()
# also scan other data sections
for s in pe.sections:
    if s.name in (".rdata", ".data", ".rsrc"):
        blob = pe.read_rva(s.virtual_address, s.virtual_size) or b""
        for m in re.finditer(rb"\.\?AV[A-Za-z0-9_@]+", blob):
            names.add(m.group().decode("latin1"))
print("RTTI count", len(names))
keys=("Order","Front","Plan","Battle","AreaDef","Garrison","Fallback","Spear","Offense","Theatre","Theater","Crisis","Alert","Encirc","Spot","Intel","Visibility","Building","Damage","Assignment","NavalInv","Invasion")
interesting=[n for n in sorted(names) if any(k in n for k in keys)]
print("interesting", len(interesting))
for n in interesting:
    print(n)
Path("research/t188_rtti_plan_names.json").write_text(json.dumps(interesting, indent=2)+"\n", encoding="utf-8")
