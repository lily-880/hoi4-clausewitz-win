from __future__ import annotations
import json, struct, sys, re
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid

pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs = Cs(CS_ARCH_X86, CS_MODE_64)
p = Proc(mem_find_pid("hoi4.exe"))
base = p.base
TABLE = 0x35011E0
TID_BASE = 0x2328

bind = json.loads(Path("research/t194_bind_cmds.json").read_text(encoding="utf-8"))

def disasm(rva, n=0x80):
    return list(cs.disasm(pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n], rva))

def cstr_imm(rva):
    return struct.unpack("<I", pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+4])[0]

# SetPath sentinel addresses
# 0x18dffb4  mov ecx, dword ptr [rip + 0x1b0b2ea]  -> 0x18dffb4+6+0x1b0b2ea
s1 = 0x18dffb4 + 6 + 0x1b0b2ea
s2 = 0x18dffc2 + 6 + 0x1b0b2d8
print("sentinel addrs", hex(s1), hex(s2))
print("sentinel vals", hex(cstr_imm(s1)), hex(cstr_imm(s2)), cstr_imm(s1), cstr_imm(s2))
# also try as signed interpretation - these should be the same empty pair as NewRoot
# t193 sentinels were at 0x33CB2A0 / 0x33CB2A4
print("known NewRoot sentinel pair 0x33CB2A0", hex(cstr_imm(0x33CB2A0)), hex(cstr_imm(0x33CB2A4)))

# type-id: look at vtable slots 1-8 for small functions that `mov eax, imm; ret`
def typeid_from_vt(vt):
    raw = pe.data[pe.rva_to_off(vt):pe.rva_to_off(vt)+16*8]
    found = []
    for i in range(16):
        q = struct.unpack_from("<Q", raw, i*8)[0]
        if not (pe.image_base <= q < pe.image_base + pe.size_of_image):
            continue
        rva = q - pe.image_base
        ins = disasm(rva, 0x20)
        text = " ; ".join(f"{x.mnemonic} {x.op_str}" for x in ins[:6])
        m = re.search(r"mov eax, 0x([0-9a-f]+)", text)
        if m and ins and ins[0].mnemonic in ("mov","push"):
            # often: mov eax, imm; ret
            found.append({"slot": i, "rva": hex(rva), "imm": "0x"+m.group(1), "idx": int(m.group(1),16)-TID_BASE, "ins": text})
        elif "eax" in text and "ret" in text:
            found.append({"slot": i, "rva": hex(rva), "ins": text})
    return found

print("\n======= type-id getters =======")
for name, rec in bind["cmds"].items():
    if not rec.get("vts"):
        continue
    vt = int(rec["vts"][0], 16)
    tids = typeid_from_vt(vt)
    print(name, tids[:6])

# verify PauseGame idx 1732
def factory(idx):
    slot = struct.unpack("<Q", p.read(base + TABLE + idx * 8, 8))[0]
    if not (base <= slot < base + p.image_size):
        return None
    rva = slot - base
    head = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+24]
    size=None
    for i in range(0,16):
        if head[i]==0xB9:
            size=struct.unpack_from("<I", head, i+1)[0]; break
    return {"factory": hex(rva), "head": head.hex(), "size": size}

print("\nPauseGame idx 1732", factory(1732))
# CPauseGame 0x29ec -> 1732 yes

# print IsValid full for Assign, Execute, Pause, NewFront, NewFallback from clips
for name in ["COrderAssignCommand","COrderExecuteCommand","CPauseGame","COrderNewFrontCommand","COrderNewFallbackCommand","CCreateAreaDefenseCommand","CSetArmyLeaderCommand"]:
    rec=bind["cmds"][name]
    isv=rec.get("isvalid")
    if not isv:
        continue
    path=Path(f"research/_t194_clip_{name}_isvalid_{isv}.txt")
    print("\n======== FULL IsValid", name, isv, "========")
    if path.exists():
        print(path.read_text(encoding="utf-8"))

p.close()
