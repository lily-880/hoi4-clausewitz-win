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

def vtables_for(name):
    pat=name.encode()
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(pat), blob):
            tdescs.append(s.virtual_address+m.start()-0x10)
    vts=set()
    for tdesc in tdescs:
        col_imm=struct.pack("<I", tdesc)
        for s in pe.sections:
            blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
            for m in re.finditer(re.escape(col_imm), blob):
                col_rva=s.virtual_address+m.start()-0x0C
                raw=pe.read_rva(col_rva, 4)
                if raw and struct.unpack("<I", raw)[0] in (0,1):
                    need=struct.pack("<Q", IMAGE+col_rva)
                    for s2 in pe.sections:
                        blob2=pe.data[s2.raw_ptr:s2.raw_ptr+s2.raw_size]
                        for m2 in re.finditer(re.escape(need), blob2):
                            vt=s2.virtual_address+m2.start()+8
                            if _rtti_name_from_vtable(pe, vt)==name:
                                vts.add(vt)
    return sorted(vts)

# also CWar exact, CDiplomaticRelation, CRelation, CWarManager
extra=[]
pat=re.compile(rb"\.\?A[UV]C[A-Za-z0-9_]*War[A-Za-z0-9_]*@@|\.\?A[UV]CWar@@|\.\?A[UV]C[A-Za-z0-9_]*(Relation|Diplomacy)[A-Za-z0-9_]*@@")
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in pat.finditer(blob):
        extra.append(m.group().decode())
print("extra class names:")
for n in sorted(set(extra)):
    if any(k in n for k in ("War","Relation","Diplo")) and "Trigger" not in n and "Effect" not in n and "Window" not in n and "Command" not in n and "Action" not in n and "Item" not in n and "View" not in n:
        print(" ", n)

for n in (".?AVCWarRelation@@",):
    vts=vtables_for(n)
    print(n, [hex(v) for v in vts])
    for vt in vts:
        raw=pe.read_rva(vt, 0x40) or b""
        fns=[]
        for i in range(0,len(raw),8):
            v=struct.unpack_from("<Q", raw, i)[0]
            if IMAGE<=v<IMAGE+0x4000000:
                fns.append(hex(v-IMAGE))
            else:
                break
        print(" ", hex(vt), fns[:10])

for start,tag,nb in (
    (0xd8f520,"war_writer_0xd8f520",0x800),
    (0xd80800,"war_relation_0xd80800",0x400),
    (0xd814f7,"war_relation_0xd814f7",0x200),
    (0x73c0d0,"at_war_0x73c0d0",0x200),
    (0x16b0410,"war_with_0x16b0410",0x200),
    (0xd8fb02,"war_token_0xd8fb02",0x80),
):
    fo_start=start
    lines=clip(fo_start, nb, f"research/_t186_clip_{tag}.txt")
    toks=[ln for ln in lines if "TOKEN" in ln]
    print(f"\n======= {hex(start)} {tag} n={len(lines)} toks={len(toks)} =====")
    for ln in toks:
        print(ln)
    if start in (0xd8fb02, 0xd814f7):
        # maybe mid-function; print around
        print("  --- body ---")
        for ln in lines[:25]:
            print(" ", ln)
