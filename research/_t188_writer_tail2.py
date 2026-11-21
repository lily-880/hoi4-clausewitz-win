import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
raw=pe.read_rva(0x10d1e00, 0x800) or b""
toks=[]
for i in cs.disasm(raw, 0x10d1e00):
    m=re.search(r"(edx|r8d|r9d), 0x([0-9a-f]+)", i.op_str)
    if m:
        tok=int(m.group(2),16)
        if tok in id2name:
            toks.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}  ; TOKEN {id2name[tok]}")
    if i.mnemonic=="ret":
        toks.append(f"0x{i.address:x}  ret")
        break
print("\n".join(toks))
print("done")
