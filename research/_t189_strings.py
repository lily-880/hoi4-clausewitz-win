import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""

print("=== alert/crisis/encircle/spotted/fog strings ===")
pats=rb"(ALERT_[A-Z0-9_]+|alert_[a-z0-9_]+|encircled|encirclement|org_collapse|plan_failed|out_of_supply|fog_of_war|FogOfWar|unit_spotted|is_spotted|spotted_by|land_visibility|INTEL_[A-Z0-9_]+|visibility_spotted|combat_intel)"
seen=set()
for m in re.finditer(pats, rblob, re.I):
    a=m.start()
    while a>0 and 32<=rblob[a-1]<127: a-=1
    b=m.end()
    while b<len(rblob) and 32<=rblob[b]<127: b+=1
    s=rblob[a:b].decode("latin1")
    if s in seen: continue
    if any(x in s.lower() for x in ("shader","github","fallback_law","airplane")):
        continue
    seen.add(s)
    if len(seen)<=80:
        print(f"  0x{rdata.virtual_address+a:x} {s[:180]}")
print("unique", len(seen))

print("\n=== RTTI Alert/Crisis/Spot/Fog/Intel/Visibility (core) ===")
names=set(m.group().decode("latin1") for m in re.finditer(rb"\.\?AV[A-Za-z0-9_@]+", rblob))
drop=("Command","Effect","Trigger","View","Item","Tooltip","Handler","Define","Tut","Window","Popup","Database","Config","Medal")
for n in sorted(names):
    if any(k in n for k in ("Alert","Crisis","Encirc","Spotted","Fog","Visibility","IntelLedger","UnitIntel","LandIntel","Recon","CombatIntel")):
        if not any(k in n for k in drop):
            print(" ", n)
