import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def clip(start, n, until_ret=False):
    raw=pe.read_rva(start, n) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            t=int(m.group(2),16)
            if t in id2name:
                a += "  ; TOKEN "+id2name[t]
        lines.append(a)
        if until_ret and i.mnemonic=="ret" and i.address>start+8:
            break
    return lines

print("======= 0x156c870 start =====")
print("\n".join(clip(0x156c870, 0x120)[:60]))

print("\n======= visible writer 0xf0a950 =====")
# find func start via going back to int3
raw=pe.read_rva(0xf0a900, 0x200) or b""
# print window with tokens
ls=clip(0xf0a900, 0x200, True)
for ln in ls:
    if any(k in ln for k in ("TOKEN","ret","lea r8","mov edx","call 0x254")):
        print(ln)
Path("research/_t189_clip_visible_token_0xf0a978.txt").write_text("\n".join(ls)+"\n", encoding="utf-8")

print("\n======= visible 0x1c3c7c0 =====")
ls2=clip(0x1c3c740, 0x200, True)
for ln in ls2:
    if "TOKEN" in ln or "ret" in ln:
        print(ln)

print("\n======= intel 0xd689d0 =====")
ls3=clip(0xd68980, 0x180, True)
for ln in ls3:
    if "TOKEN" in ln or "ret" in ln:
        print(ln)

print("\n======= intel 0x123c3c0 =====")
ls4=clip(0x123c380, 0x200, True)
for ln in ls4:
    if "TOKEN" in ln or "ret" in ln:
        print(ln)
