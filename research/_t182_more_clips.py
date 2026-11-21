import sys, re, json
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

clip(0x1d2bf0, 0x1d2c90, "research/_t182_clip_path_serializer_0x1d2bf0.txt")
clip(0xced2e0, 0xced6c0, "research/_t182_clip_carmy_secondary_writer_0xced2e0.txt")
clip(0x209180, 0x209280, "research/_t182_clip_land_combat_id_0x208f90.txt")
print("clips written")
print(open("research/_t182_clip_path_serializer_0x1d2bf0.txt",encoding="utf-8").read()[:800])
