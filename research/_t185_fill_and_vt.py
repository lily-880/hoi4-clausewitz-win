import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

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

# CCombatant / CLandCombatant vtables
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

for n in (".?AVCCombatant@@",".?AVCLandCombatant@@",".?AVCCombat@@"):
    vts=vtables_for(n)
    print(n, [hex(v) for v in vts])
    for vt in vts:
        raw=pe.read_rva(vt, 0x30) or b""
        fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if IMAGE<=struct.unpack_from("<Q", raw, i)[0]<IMAGE+0x4000000]
        print(" ", hex(vt), fns[:8])

# Activity fill functions
for start,tag,nb in (
    (0x13357a0,"13357a0",0x400),
    (0x1338c40,"1338c40",0x200),
    (0x1338ca6,"1338ca6",0x200),
    (0x1468293,"1468293",0x200),
    (0x14691b4,"14691b4",0x200),
    (0x10d1450,"orderinstance_writer_0x10d1450",0x500),
    (0xcecd10,"cecd10_full",0x200),
):
    fo=func_of(start)
    st=fo[0] if fo and abs(fo[0]-start)<0x20 else start
    lines=clip(st, nb, f"research/_t185_clip_{tag}.txt")
    print(f"\n======= {hex(st)} {tag} n={len(lines)} pdata={fo} =====")
    # highlight stores to +8/+0xc and combat-ish
    for ln in lines:
        if any(k in ln for k in ("TOKEN","0x8]","0xc]","0x10]","dword ptr [","call 0x19ee","29d7098","LandCombat","[rax + 8]","[rbx + 8]","[rcx + 8]","[rsi + 8]","[rdi + 8]","[rbp + 8]")):
            print(" ", ln)
    if tag.startswith("order") or tag.startswith("13357") or tag.startswith("1338c40"):
        # also print more complete
        print("  --- first 25 ---")
        for ln in lines[:25]:
            print(" ", ln)

# Search mov dword [???+8] near activity vtable functions — already in clips
# Search CArmy code for GetCombat-like: lea/call that then reads CLandCombat vtable 0x2a23898 or CCombat 0x2a368e8/0x2a369c0
# Find lea of CLandCombat / CCombat vtables
def lea_xrefs(rva, limit=25):
    hits=[]
    for m in re.finditer(b"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x2d\x35\x3d]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+3)[0]
        dest=text_rva+at+7+rel
        if dest==rva:
            fo=func_of(text_rva+at)
            hits.append((hex(text_rva+at), hex(fo[0]) if fo else None))
            if len(hits)>=limit:
                break
    return hits

print("\n===== CLandCombat / CCombat / CCombatant vtable leas =====")
for n,vts in ((".?AVCLandCombat@@", vtables_for(".?AVCLandCombat@@")),
              (".?AVCCombatant@@", vtables_for(".?AVCCombatant@@")),
              (".?AVCLandCombatant@@", vtables_for(".?AVCLandCombatant@@"))):
    print(n, [hex(v) for v in vts])
    for vt in vts:
        xs=lea_xrefs(vt)
        print("  vt", hex(vt), "lea n", len(xs), xs[:10])
