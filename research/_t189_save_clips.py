import sys,re
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
# short clip of 0x1571ef0 around +0x148 use and assert
raw=pe.read_rva(0x1571ef0, 0x40) or b""
head=[]
for i in cs.disasm(raw, 0x1571ef0):
    head.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
raw=pe.read_rva(0x1572bf0, 0x90) or b""
mid=[]
for i in cs.disasm(raw, 0x1572bf0):
    mid.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if i.address>=0x1572c64:
        break
text="======= 0x1571ef0 head =====\n"+"\n".join(head)+"\n======= 0x1572bf0 EncirclementPoints =====\n"+"\n".join(mid)+"\n"
Path("research/_t189_clip_encirclement_points_0x1571ef0.txt").write_text(text, encoding="utf-8")
print(text)

# intel writer tokens clip
import json
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
raw=pe.read_rva(0xd689d0, 0x280) or b""
lines=[]
for i in cs.disasm(raw, 0xd689d0):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d), 0x([0-9a-f]+)", i.op_str)
    if m:
        t=int(m.group(2),16)
        if t in id2name:
            a += "  ; TOKEN "+id2name[t]
    lines.append(a)
    if i.mnemonic=="ret":
        break
Path("research/_t189_clip_intel_writer_0xd689d0.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("intel tokens:")
for ln in lines:
    if "TOKEN" in ln or ln.endswith(" ret"):
        print(ln)
