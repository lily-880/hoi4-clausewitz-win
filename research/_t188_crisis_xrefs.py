import sys,struct,re,json
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
for name,tok in (("already_spotted",0x3bb3),("alerts",0x2d42),("alert_level",0x4ba4),("alert_text",0x4a5f),("detected",0x4b06),("intel_levels",0x4b07),("visibility_type",0x4b9d),("encircled_divisions",0x3e62)):
    imm=struct.pack("<I", tok)
    sites=[]
    start=0
    while True:
        k=blob.find(imm, start)
        if k<0: break
        if k>=1 and blob[k-1]==0xBA:
            sites.append(base+k-1)
        start=k+1
        if len(sites)>=8: break
    print(f"{name} 0x{tok:x}: " + " ".join(hex(s) for s in sites))
    if sites:
        raw=pe.read_rva(sites[0]-16, 48) or b""
        for i in cs.disasm(raw, sites[0]-16):
            a=f"  0x{i.address:x}  {i.mnemonic} {i.op_str}"
            m=re.search(r"(edx|r8d), 0x([0-9a-f]+)", i.op_str)
            if m:
                t=int(m.group(2),16)
                if t in id2name: a += "  ; TOKEN "+id2name[t]
            print(a)
