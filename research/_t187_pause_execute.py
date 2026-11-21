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
        if i.mnemonic=="ret" and i.address>start+16:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

def vtables_for(name):
    pat=name.encode()
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        off=0
        while True:
            i=blob.find(pat, off)
            if i<0: break
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

for name in (".?AVCPauseGame@@",".?AVCSetGameSpeedCommand@@",".?AVCIncreaseGameSpeedCommand@@",".?AVCDecreaseGameSpeedCommand@@",".?AVCAutomaticPause@@"):
    vts=vtables_for(name)
    print(name, [hex(v) for v in vts])
    for vt in vts:
        raw=pe.read_rva(vt, 0xC0) or b""
        fns=[]
        for i in range(0,len(raw),8):
            v=struct.unpack_from("<Q", raw, i)[0]
            if IMAGE<=v<IMAGE+0x4000000:
                fns.append((hex(i), hex(v-IMAGE)))
            else:
                break
        print(" ", hex(vt), fns[:16])

# CPauseGame candidate execute slots
for start,tag,nb in (
    (0xe571a0,"Pause_0xe571a0",0x200),
    (0xe581e0,"Pause_0xe581e0",0x200),
    (0xe57ef0,"Pause_0xe57ef0",0x200),
    (0xe55060,"Pause_0xe55060",0x100),
    (0xe56c30,"Pause_0xe56c30",0x100),
    (0xe531e0,"Pause_0xe531e0",0x100),
):
    lines=clip(start, nb, f"research/_t187_clip_{tag}.txt")
    print(f"\n======= {hex(start)} {tag} n={len(lines)} last={lines[-1] if lines else None} =====")
    # highlight mem stores, calls, cmp byte
    useful=[ln for ln in lines if any(k in ln for k in ("mov byte","mov dword","mov qword","TOKEN","call 0x","cmp byte","test ","0x4b8","0x4bc"))]
    for ln in useful[:30]:
        print(ln)
    if not useful:
        print("\n".join(lines[:20]))
