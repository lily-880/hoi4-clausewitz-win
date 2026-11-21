import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def clip(start, nbytes, path):
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
        if i.mnemonic=="ret" and i.address>start+16:
            break
    Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# full COrderInstance writer
lines=clip(0x10d1450, 0x800, "research/_t188_clip_orderinstance_writer_0x10d1450.txt")
print("COrderInstance writer n", len(lines), "last", lines[-1] if lines else None)
print("--- tokens / key slots ---")
for ln in lines:
    if "TOKEN" in ln or "0x30" in ln or "ret" in ln or "mov edx" in ln:
        if any(k in ln for k in ("TOKEN","[r14","[rcx","ret","call 0x254","call 0xcfe","call 0x10")):
            print(ln)

print("\n======= COrdersGroup writer 0xc4d030 =====")
g=clip(0xc4d030, 0x500, "research/_t188_clip_ordersgroup_writer_0xc4d030.txt")
print("n", len(g), "last", g[-1] if g else None)
for ln in g:
    if "TOKEN" in ln or "0x98" in ln or "0xa4" in ln:
        print(ln)
