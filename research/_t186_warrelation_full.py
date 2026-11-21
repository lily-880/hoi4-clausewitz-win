import sys,os,re,json,struct,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

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

# CWarRelation writer 0xd8f900 and likely base 0xd8f520
for start,tag,nb in ((0xd8f900,"warrelation_writer_0xd8f900",0x800),(0xd8f520,"relation_base_0xd8f520",0x200)):
    lines=clip(start, nb, f"research/_t186_clip_{tag}.txt")
    print(f"\n======= {hex(start)} {tag} n={len(lines)} last={lines[-1] if lines else None} =====")
    for ln in lines:
        if "TOKEN" in ln or "call 0x22858" in ln or "call 0xd8f" in ln or re.search(r"\[r(bx|cx|si|di|14|15|bp) \+", ln) or ln.endswith(" ret") or "jmp 0x" in ln:
            print(ln)

# CRelation vtables
def vtables_for(name):
    pat=name.encode()
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(pat)+b"(?!.)", blob):
            # exact-ish: name followed by what? just use finditer of exact
            pass
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        off=0
        while True:
            i=blob.find(pat, off)
            if i<0: break
            # ensure terminator
            tdescs.append(s.virtual_address+i-0x10)
            off=i+1
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

for n in (".?AVCRelation@@",".?AVCRelationStatus@@",".?AVCDiplomacyStatus@@"):
    vts=vtables_for(n)
    print(n, [hex(v) for v in vts])
    for vt in vts:
        raw=pe.read_rva(vt, 0x30) or b""
        fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if IMAGE<=struct.unpack_from("<Q", raw, i)[0]<IMAGE+0x4000000]
        print(" ", hex(vt), fns[:8])
