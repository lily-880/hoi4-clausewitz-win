from pathlib import Path
import sys
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import re,json

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def clip(start, nbytes, path=None):
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
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

print("======= FULL 0xe55060 =====")
print("\n".join(clip(0xe55060, 0x80, "research/_t187_clip_Pause_0xe55060.txt")))

print("\n======= FULL 0xe56c30 =====")
print("\n".join(clip(0xe56c30, 0x40, "research/_t187_clip_Pause_0xe56c30.txt")))

print("\n======= FULL 0xe571a0 =====")
lines=clip(0xe571a0, 0x300, "research/_t187_clip_Pause_0xe571a0.txt")
print("n", len(lines), "last", lines[-1])
print("\n".join(lines))

print("\n======= CSetGameSpeed 0xf85bc0 / 0xf85d10 / 0xf84770 =====")
for start,tag,nb in ((0xf85bc0,"SetSpeed_0xf85bc0",0x200),(0xf85d10,"SetSpeed_0xf85d10",0x200),(0xf84770,"SetSpeed_0xf84770",0x200),(0xf859a0,"IncSpeed_0xf859a0",0x200),(0xf85460,"DecSpeed_0xf85460",0x200)):
    lines=clip(start, nb, f"research/_t187_clip_{tag}.txt")
    print(f"\n--- {hex(start)} {tag} n={len(lines)} last={lines[-1] if lines else None} ---")
    for ln in lines:
        if any(k in ln for k in ("byte ptr","dword ptr","TOKEN","call 0x","0x4b","rip","paused","speed")):
            print(ln)
