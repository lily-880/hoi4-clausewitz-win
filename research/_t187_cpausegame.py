import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

# RTTI names with Pause or GameSpeed
pat=re.compile(rb"\.\?A[UV]C[A-Za-z0-9_]*(Pause|Unpause|GameSpeed|SpeedCommand|TimeControl)[A-Za-z0-9_]*@@")
found=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in pat.finditer(blob):
        found.append(m.group().decode())
print("RTTI pause/speed:", sorted(set(found)))

# also broader Pause
pat2=re.compile(rb"\.\?A[UV]C[A-Za-z0-9_]*Pause[A-Za-z0-9_]*@@")
found2=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in pat2.finditer(blob):
        found2.append(m.group().decode())
print("all Pause classes:", sorted(set(found2)))

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
        if i.mnemonic=="ret" and i.address>start+12:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# dump more CPauseGame vtable
raw=pe.read_rva(0x29e6e10, 0xC0) or b""
print("\nCPauseGame vt 0x29e6e10 slots:")
for i in range(0, len(raw), 8):
    v=struct.unpack_from("<Q", raw, i)[0]
    if IMAGE<=v<IMAGE+0x4000000:
        print(f"  +{i:#x}  {hex(v-IMAGE)}")
    else:
        print(f"  +{i:#x}  raw {hex(v)}")
        if i>0x20: break

# find ALL CPauseGame vtables more carefully and CCommand start nearby
# read 0x200 before 0x29e6e10 for sibling vtables
print("\nRTTI near 0x29e6d00-0x29e7000:")
for rva in range(0x29e6c00, 0x29e7200, 8):
    n=_rtti_name_from_vtable(pe, rva)
    if n:
        print(hex(rva), n)

for start,tag,nb in ((0xe52a30,"CPauseGame_0xe52a30",0x200),(0x22d9400,"CPauseGame_ser_0x22d9400",0x100),(0x22d9160,"CPauseGame_0x22d9160",0x100)):
    lines=clip(start, nb, f"research/_t187_clip_{tag}.txt")
    print(f"\n======= {hex(start)} {tag} n={len(lines)} last={lines[-1] if lines else None} =====")
    print("\n".join(lines[:40]))
