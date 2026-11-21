from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
ARMY=0x26d2b077020
AG=0x26d3e6baa50

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF

def cls(p,pe,a):
    if not is_ptr(a): return None
    try:
        vt=struct.unpack("<Q", p.read(a,8))[0]
    except OSError:
        return None
    if not p.base<=vt<p.base+p.image_size: return None
    return _rtti_name_from_vtable(pe, vt-p.base)

p=Proc(mem_find_pid("hoi4.exe"))
pe=PE(EXE)
q=struct.unpack("<Q", p.read(ARMY+0x1B8,8))[0]
print(json.dumps({
    "army_1b8": hex(q),
    "class": cls(p,pe,q),
    "is_ag": q==AG,
    "handle": list(struct.unpack("<II", p.read(q+8,8))) if is_ptr(q) else None,
}, ensure_ascii=False))

# search writer clip for 0x1b8
for name in ["research/_t192_clip_COrdersGroup_writer_0xc4d030.txt","research/_t184_clip_ordersgroup_writer_0xc4d030.txt",
             "research/_t184_clip_armygroup_writer_0xc4cfa0.txt"]:
    path=Path(name)
    if not path.exists():
        continue
    print("====", name)
    for l in path.read_text(encoding="utf-8").splitlines():
        if "0x1b8" in l.lower() or "0x1B8" in l:
            print(l)

# disassemble NewFront IsValid + Execute window
cs=Cs(CS_ARCH_X86, CS_MODE_64)
def read_rva(rva,n):
    off=pe.rva_to_off(rva)
    return pe.data[off:off+n]

print("\n======= NewFront IsValid 0x18df550 =====")
lines=[]
for i in cs.disasm(read_rva(0x18df550, 0x120), 0x18df550):
    line=f"{hex(i.address)}  {i.mnemonic} {i.op_str}"
    lines.append(line)
    print(line)
    if i.mnemonic=="ret":
        break
Path("research/_t193_clip_COrderNewFrontCommand_isvalid_0x18df550.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")

print("\n======= NewFront Execute 0x18d9070 window 0x280 =====")
elines=[]
for i in cs.disasm(read_rva(0x18d9070, 0x280), 0x18d9070):
    elines.append(f"{hex(i.address)}  {i.mnemonic} {i.op_str}")
Path("research/_t193_clip_COrderNewFrontCommand_execute_0x18d9070.txt").write_text("\n".join(elines)+"\n", encoding="utf-8")
for l in elines:
    print(l)
p.close()
