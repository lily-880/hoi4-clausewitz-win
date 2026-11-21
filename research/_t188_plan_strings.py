import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
name2id={i["name"]:i["token"] for i in mp}

# strings of interest in rdata+data
needles=[
    b"frontline", b"offensive_line", b"area_defense", b"garrison",
    b"fallback", b"spearhead", b"order_instance", b"executing",
    b"ORDER_", b"FrontLine", b"OffensiveLine", b"AreaDefense",
    b"COrderInstance", b"battle_plan", b"BattlePlan",
]
# scan rdata
rdata=[s for s in pe.sections if s.name==".rdata"][0]
blob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
# also .data for some string tables? usually rdata
text=[s for s in pe.sections if s.name==".text"][0]
textblob=pe.read_rva(text.virtual_address, min(text.virtual_size, 0x2783d48)) or b""

def find_cstrs(blob, base, needles):
    hits=[]
    for n in needles:
        start=0
        while True:
            i=blob.find(n, start)
            if i<0: break
            # expand to full cstring
            a=i
            while a>0 and 32<=blob[a-1]<127: a-=1
            b=i+len(n)
            while b<len(blob) and 32<=blob[b]<127: b+=1
            s=blob[a:b].decode("latin1","replace")
            hits.append((base+a, s, n.decode()))
            start=i+1
    return hits

hits=find_cstrs(blob, rdata.virtual_address, needles)
print("string hits", len(hits))
# unique interesting
seen=set()
for va,s,n in hits:
    key=(n,s)
    if key in seen: continue
    # filter noise
    if any(x in s.lower() for x in ("shader","vertex","plane ","airplane","github","fallback_law")):
        continue
    seen.add(key)
    print(f"  0x{va:x}  [{n}] {s[:180]}")

# also search typenames more precisely
for n in [b"frontline", b"offensive_line", b"area_defense", b"spearhead", b"order_instance"]:
    print("--- exact", n, "count in rdata", blob.lower().count(n), "in text", textblob.lower().count(n))

print("tokens:")
for name in ("order_instance","area_defense","fallback","garrison","front","frontline","offensive_line","executing","spearhead","vertices","vertex","axis","children","child_orders","orders"):
    if name in name2id:
        print(f"  {name} 0x{name2id[name]:x}")
