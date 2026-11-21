import sys,re,json,struct
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
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and path and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# CArmyGroup until it hits 0xc4d030 or ret
lines=clip(0xc4cfa0, 0xc4d040, "research/_t184_clip_armygroup_writer_0xc4cfa0.txt")
print("===== CArmyGroup 0xc4cfa0.. =====")
print("\n".join(lines))

print("\n===== CTheaterGroup full pdata 0x54 =====")
print(Path("research/_t184_clip_theatergroup_writer_0x16d9e10.txt").read_text(encoding="utf-8")[:2000])

print("\n===== base id writer 0x22858a0 =====")
print("\n".join(clip(0x22858a0, 0x228598d, "research/_t184_clip_base_id_writer_0x22858a0.txt")))

print("\n===== 0x25458c0 =====")
print("\n".join(clip(0x25458c0, 0x2545940, "research/_t184_clip_write_named_0x25458c0.txt")))

print("\n===== 0x22857c0 unit handle? =====")
print("\n".join(clip(0x22857c0, 0x228589f, "research/_t184_clip_unit_handle_writer_0x22857c0.txt")))

print("\n===== 0x134d5e0 first 40 inst =====")
print("\n".join(clip(0x134d5e0, 0x134d620, "research/_t184_clip_landcombat_writer_0x134d5e0.txt")))
