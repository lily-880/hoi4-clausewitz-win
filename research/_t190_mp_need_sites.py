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

def ba_sites(tok, limit=15):
    imm=struct.pack("<I", tok)
    sites=[]; start=0
    while True:
        k=blob.find(imm, start)
        if k<0: break
        if k>=1 and blob[k-1]==0xBA:
            sites.append(base+k-1)
        start=k+1
        if len(sites)>=limit: break
    return sites

for name,tok in (("army_manpower_need",0x36fc),("army_manpower_value",0x36fb),("need",0x2f4f),("manpower",0x283c),("amount_manpower_in_deployment_queue",0x39e6),("garrison_manpower_need",0x4aca),("manpower_pool",0x3635),("available",0x2fe8)):
    sites=ba_sites(tok)
    print(f"{name} 0x{tok:x}: " + " ".join(hex(s) for s in sites))

# CCountryManpower writer? search rtti and known  from t167: CCountryManpower
# t167 mentioned writer around D5DAE0 as getter not writer
# token available 0x2fe8 was StateManpower writer 14874B0
print("\n=== CC6480 first lines (known gap getter) ===")
raw=pe.read_rva(0xcc6480, 0x80) or b""
for i in cs.disasm(raw, 0xcc6480):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if i.mnemonic=="ret":
        break
