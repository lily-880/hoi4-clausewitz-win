from pathlib import Path
lines=Path("research/_t187_clip_idler_setpause_0xe487f0.txt").read_text(encoding="utf-8").splitlines()
print("--- 0xe48aa0 through end ---")
for ln in lines:
    addr=int(ln.split()[0],16)
    if addr>=0xe48aa0:
        print(ln)

# also 0xe46350 and 0xe48e30
import sys,re,json
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def clip(start, nbytes):
    raw=pe.read_rva(start, nbytes) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+8:
            break
    return lines

print("\n======= vt+0x290 0xe46350 =====")
print("\n".join(clip(0xe46350, 0x80)))
print("\n======= vt+0x288 0xe48e30 =====")
ls=clip(0xe48e30, 0x100)
print("\n".join(ls[:40]))
