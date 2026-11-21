import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
raw=pe.read_rva(0x1043480, 0x200) or b""
lines=[]
for i in cs.disasm(raw, 0x1043480):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
    if m:
        t=int(m.group(2),16)
        if t in id2name:
            a += "  ; TOKEN "+id2name[t]
    lines.append(a)
    if i.mnemonic=="ret" and i.address>0x1043530:
        break
print("\n".join(lines))
Path("research/_t188_clip_already_spotted_0x104353b.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
