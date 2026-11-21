import sys,re
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""

print("=== ALERT_ loc keys (filtered) ===")
for m in re.finditer(rb"ALERT_[A-Z0-9_]+", rblob):
    s=m.group().decode()
    if any(k in s for k in ("ENCIRC","SUPPLY","ORG","PLAN","COLLAPSE","LOW_ORG","NO_SUPPLY","SURROUND","DIVISION","COMBAT","OOS","ISOLAT")):
        print(f"  0x{rdata.virtual_address+m.start():x} {s}")

print("\n=== alert_ lowercase interesting ===")
for m in re.finditer(rb"alert_[a-z0-9_]+", rblob):
    s=m.group().decode()
    if any(k in s for k in ("encirc","supply","org","plan","combat","surround","oos","isolat","garrison")):
        print(f"  0x{rdata.virtual_address+m.start():x} {s}")

print("\n=== THEATER_ / theatre alert ===")
for m in re.finditer(rb"(THEATER|THEATRE)_[A-Z0-9_]{0,40}(ALERT|ENCIRC|SUPPLY|COMBAT|ORG)[A-Z0-9_]*", rblob):
    print(f"  0x{rdata.virtual_address+m.start():x} {m.group().decode()}")

print("\n=== RTTI containing Alert or Encirc or Fog or Spotted ===")
names=set(m.group().decode("latin1") for m in re.finditer(rb"\.\?AV[A-Za-z0-9_@]+", rblob))
for n in sorted(names):
    if any(k in n for k in ("Alert","Crisis","Encirc","FogOf","CFog","Spotted","VisibilityMap","UnitVisibility","ArmyIntel","CIntelSource","CCountryIntel")):
        print(" ", n)
