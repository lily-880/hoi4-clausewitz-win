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

def clip(start, nbytes, path=None, stop_ret=True):
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
        if stop_ret and i.mnemonic=="ret" and i.address>start+16:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# window BEFORE 0x2f54d3: look for prologue (sub rsp / push / mov rdi,rcx)
# start from 0x2f5000 or find previous pdata function end
# previous function:
i=bisect.bisect_right(starts, 0x2f54d3)-2
if i>=0:
    print("prev pdata", hex(functions[i][0]), hex(functions[i][1]))
    print("this pdata", hex(functions[i+1][0]), hex(functions[i+1][1]) if i+1<len(functions) else None)
    print("next pdata", hex(functions[i+2][0]), hex(functions[i+2][1]) if i+2<len(functions) else None)

# disassemble 0x2f5200-0x2f54ed without stop, then we can find start
raw=pe.read_rva(0x2f5200, 0x2f54f0-0x2f5200) or b""
# find push rbx / sub rsp patterns
lines=[]
for i in cs.disasm(raw, 0x2f5200):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
    if m:
        tok=int(m.group(2),16)
        if tok in id2name:
            a += "  ; TOKEN "+id2name[tok]
    lines.append(a)
Path("research/_t187_clip_paused_writer_window.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n======= window 0x2f5200-0x2f54ed tokens and prologues =====")
for ln in lines:
    if "TOKEN" in ln or ln.split()[1] in ("push","sub","ret","call") or "paused" in ln or "2546250" in ln or "byte ptr [" in ln:
        if any(k in ln for k in ("TOKEN","push rbx","push rdi","sub rsp","ret","2546250","paused","cmp byte","test ","movzx")):
            print(ln)

# call/jmp xrefs to addresses in 0x2f5300-0x2f54d6
def rel32_xrefs_to(targets, limit=30):
    hits=[]
    tset=set(targets)
    for m in re.finditer(b"[\xe8\xe9]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+1)[0]
        dest=text_rva+at+5+rel
        if dest in tset:
            fo=func_of(text_rva+at)
            hits.append((hex(text_rva+at), "call" if text_raw[at]==0xE8 else "jmp", hex(dest), hex(fo[0]) if fo else None))
            if len(hits)>=limit: break
    return hits

# candidate starts: look for sub rsp, 0x50 shortly before
cands=[]
for ln in lines:
    if "sub rsp, 0x50" in ln or "sub rsp, 50h" in ln:
        cands.append(ln)
print("\nsub rsp 0x50", cands)

# pausegame registrar 0x83760
print("\n======= 0x83760 (pdata may be huge) =====")
fo=func_of(0x83760)
print("func", fo and (hex(fo[0]), hex(fo[1]), hex(fo[1]-fo[0])))
# just clip around 0xa7913
raw=pe.read_rva(0xa78e0, 0x80) or b""
for i in cs.disasm(raw, 0xa78e0):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    print(a)
    if i.address>0xa7960:
        break

# CPauseGame vtables
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

vts=vtables_for(".?AVCPauseGame@@")
print("\nCPauseGame vtables", [hex(v) for v in vts])
for vt in vts:
    raw=pe.read_rva(vt, 0x40) or b""
    fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if IMAGE<=struct.unpack_from("<Q", raw, i)[0]<IMAGE+0x4000000]
    print(hex(vt), fns[:10])
