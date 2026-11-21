import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\clausewitz_win".replace("clausewitz_win","") if False else r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
# fix
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
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, end, path=None):
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
        if i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# dump vtable 0x29d7030 slots
raw=pe.read_rva(0x29d7030, 0x100) or b""
print("===== VT 0x29d7030 slots =====")
for i in range(0, 0x100, 8):
    v=struct.unpack_from("<Q", raw, i)[0]
    if IMAGE<=v<IMAGE+0x4000000:
        print(f"  +{i:#x}  {hex(v-IMAGE)}")
    else:
        print(f"  +{i:#x}  raw {hex(v)}  (end?)")
        break

print("\n===== VT 0x29d6fe8 slots (CArmy+0xb8) =====")
raw=pe.read_rva(0x29d6fe8, 0x80) or b""
for i in range(0, 0x80, 8):
    v=struct.unpack_from("<Q", raw, i)[0]
    if IMAGE<=v<IMAGE+0x4000000:
        print(f"  +{i:#x}  {hex(v-IMAGE)}")

# xrefs to 0x19eeaa0 (call/jmp rel32 or abs lea)
target=0x19eeaa0
hits=[]
# E8 rel32 call, E9 rel32 jmp
for m in re.finditer(b"[\xe8\xe9]", text_raw):
    at=m.start()
    rel=struct.unpack_from("<i", text_raw, at+1)[0]
    dest=text_rva+at+5+rel
    if dest==target:
        rva=text_rva+at
        fo=func_of(rva)
        hits.append((hex(rva), "call" if text_raw[at]==0xE8 else "jmp", hex(fo[0]) if fo else None))
print("\n===== xrefs 0x19eeaa0 =====", len(hits))
for h in hits[:30]:
    print(h)

# also xrefs to 0x19eea30, 0x19eeb10, 0x19eebc0
for t in (0x19eea30, 0x19eeb10, 0x19eebc0, 0x19ee810):
    hs=[]
    for m in re.finditer(b"[\xe8\xe9]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+1)[0]
        dest=text_rva+at+5+rel
        if dest==t:
            rva=text_rva+at
            fo=func_of(rva)
            hs.append((hex(rva), "call" if text_raw[at]==0xE8 else "jmp", hex(fo[0]) if fo else None))
    print(f"xrefs {hex(t)} n={len(hs)}", hs[:12])

# disassemble serialize candidate 0xccb530 and 0xccb4e0
for rva,name in ((0xccb530,"ccb530"),(0xccb4e0,"ccb4e0"),(0xccb540,"ccb540")):
    lines=clip(rva, rva+0x80, f"research/_t185_clip_{name}.txt")
    print(f"\n==== {hex(rva)} ====")
    print("\n".join(lines[:25]))
