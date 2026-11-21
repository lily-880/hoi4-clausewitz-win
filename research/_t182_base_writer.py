import sys, struct, re, json, bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={item["token"]:item["name"] for item in mp}

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)

def clip(start, end, path=None):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# 0xc5c0a0 size 0x570 -> end 0xc5c610
lines=clip(0xc5c0a0, 0xc5c610, "research/_t182_clip_carmy_base_writer_0xc5c0a0.txt")
print("===== 0xc5c0a0 base writer =====")
print("\n".join(lines))

# around land_combat_id 0x2091bc and combat 0x20ab0f in 0x208f90
print("\n===== 0x208f90 around land_combat_id =====")
print("\n".join(clip(0x209180, 0x209280)))
print("\n===== 0x208f90 around combat token =====")
print("\n".join(clip(0x20aac0, 0x20ab80)))
# also function start to identify object
print("\n===== 0x208f90 start =====")
print("\n".join(clip(0x208f90, 0x208ff0)))
