import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
text=[s for s in pe.sections if s.name==".text"][0]
blob=pe.read_rva(text.virtual_address, text.virtual_size) or b""
base=text.virtual_address

# call 0x1571ef0 = E8 rel32
target=0x1571ef0
callers=[]
start=0
while True:
    k=blob.find(b"\xe8", start)
    if k<0: break
    if k+5<=len(blob):
        rel=struct.unpack_from("<i", blob, k+1)[0]
        if base+k+5+rel==target:
            callers.append(base+k)
    start=k+1
    if len(callers)>=20: break
print("direct calls to 0x1571ef0:", [hex(c) for c in callers])

# also lea of 0x1571ef0 in vtables: scan rdata for the rva as qword
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
pat=struct.pack("<Q", target)  # if absolute preferred base 0x140000000+target?
# PE image typically stores RVAs as abs with preferred base 0x140000000
pref=0x140000000
hits=[]
for patt in (struct.pack("<Q", pref+target), struct.pack("<I", target)):
    start=0
    while True:
        k=rblob.find(patt, start)
        if k<0: break
        hits.append((rdata.virtual_address+k, len(patt)))
        start=k+1
        if len(hits)>=15: break
print("rdata ptr hits", [(hex(a),n) for a,n in hits[:15]])

# strings IsVisible / CanSee / GetVisibility / Fog
rdata_s=rblob
print("\n=== visibility/see/fog method-like strings ===")
seen=set()
for pat in (rb"IsVisible", rb"CanSee", rb"GetVisibility", rb"IsSpotted", rb"GetIntel", rb"FogOfWar", rb"IsHidden", rb"IsRevealed", rb"GetSpotting", rb"UnitVisibility"):
    for m in re.finditer(pat, rdata_s):
        a=m.start()
        while a>0 and 32<=rdata_s[a-1]<127: a-=1
        b=m.end()
        while b<len(rdata_s) and 32<=rdata_s[b]<127: b+=1
        s=rdata_s[a:b].decode("latin1")
        if s in seen: continue
        seen.add(s)
        print(f"  0x{rdata.virtual_address+a:x} {s[:180]}")

# token encircled (not encircled_divisions)
print("\n=== tokens with encirc/spotted/visible/intel_level/alert ===")
for i in mp:
    n=i["name"].lower()
    if n in ("encircled","spotted","visible","visibility","detected","intel","intel_level","alerts","alert","fog") or n.endswith("_encircled") or n.startswith("encircled") or "land_intel" in n or "army_intel" in n or "unit_intel" in n:
        print(f"  0x{i['token']:x} {i['name']}")
