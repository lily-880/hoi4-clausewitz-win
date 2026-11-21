import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base

def clip(start, end, path=None, stop_ret=True):
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
        if stop_ret and i.mnemonic in ("ret","jmp") and i.address>start+12 and "jmp qword" not in a:
            # allow early jmp if tailcall at end-ish
            if i.mnemonic=="ret" or (i.mnemonic=="jmp" and "0x" in i.op_str and not i.op_str.startswith("qword")):
                # stop on ret; on far jmp after some body too
                if i.mnemonic=="ret" or len(lines)>8:
                    break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

lines=clip(0x147ff20, 0x147ff20+0x200, "research/_t185_clip_combatant_base_0x147ff20.txt")
print("===== 0x147ff20 full =====")
print("\n".join(lines))

print("\n===== combat-ish tokens =====")
for i in mp:
    n=i["name"]
    if n in ("in_combat","is_in_combat","is_attacking","is_defending","has_combat","combat_id","land_combat","land_combat_id") or ("combat" in n and n.startswith("is_")) or n in ("num_armies_in_combat",):
        print(hex(i["token"]), n, i.get("registration_rva"))

# CArmy primary vtable: find by RTTI name
# type desc at name-0x10
def vtables_for(name):
    pat=name.encode()
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(pat), blob):
            tdescs.append(s.virtual_address+m.start()-0x10)
    vts=[]
    for tdesc in tdescs:
        col_imm=struct.pack("<I", tdesc)
        cols=[]
        for s in pe.sections:
            blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
            for m in re.finditer(re.escape(col_imm), blob):
                col_rva=s.virtual_address+m.start()-0x0C
                raw=pe.read_rva(col_rva, 4)
                if raw and struct.unpack("<I", raw)[0] in (0,1):
                    cols.append(col_rva)
        for col in cols:
            need=struct.pack("<Q", IMAGE+col)
            for s in pe.sections:
                blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
                for m in re.finditer(re.escape(need), blob):
                    vt=s.virtual_address+m.start()+8
                    if _rtti_name_from_vtable(pe, vt)==name:
                        vts.append(vt)
    return sorted(set(vts))

vts=vtables_for(".?AVCArmy@@")
print("CArmy vtables", [hex(v) for v in vts])
for vt in vts:
    raw=pe.read_rva(vt, 0xC0) or b""
    fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if struct.unpack_from("<Q", raw, i)[0]>=IMAGE]
    print(hex(vt), fns[:20], "rtti", _rtti_name_from_vtable(pe, vt))
