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

def clip(start, end, path=None, stop_ret=False):
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
        if stop_ret and i.mnemonic=="ret" and i.address>start+16:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

def token_xrefs(tok, limit=20):
    imm=struct.pack("<I", tok)
    hits=[]
    for prefix,kind in ((b"\xba","mov edx"),(b"\xb8","mov eax"),(b"\xb9","mov ecx"),
                        (b"\x41\xba","mov r10d"),(b"\x41\xb8","mov r8d"),(b"\x41\xb9","mov r9d")):
        for m in re.finditer(re.escape(prefix+imm), text_raw):
            at=text_rva+m.start()
            fo=func_of(at)
            hits.append((hex(at), kind, hex(fo[0]) if fo else None))
    return hits

print("===== land_combat 0x2919 xrefs =====")
hits=token_xrefs(0x2919)
print("n", len(hits))
for h in hits[:20]:
    print(h)

print("===== combat 0x2916 funcs (reconfirm) =====")
hits2=token_xrefs(0x2916)
funcs=sorted({h[2] for h in hits2 if h[2]})
print(funcs)

# disassemble 0x19eeaa0 and 0x19eea30
for rva,name,sz in ((0x19eeaa0,"19eeaa0",0x200),(0x19eea30,"19eea30",0x200),(0x19eeb10,"19eeb10",0x200),(0x19eebc0,"19eebc0",0x200)):
    fo=func_of(rva)
    start=fo[0] if fo else rva
    end=min((fo[1] if fo else rva+sz), start+sz)
    lines=clip(start, end, f"research/_t185_clip_{name}.txt")
    toks=[ln for ln in lines if "TOKEN" in ln]
    print(f"\n==== {hex(start)} size {end-start:#x} toks {len(toks)} rtti-context ====")
    for ln in toks:
        print(ln)
    # also mem ops first 40
    useful=[ln for ln in lines if "TOKEN" in ln or re.search(r"\[r(cx|bx|si|di|bp|1[0-4]) \+", ln) or "call 0x22858a0" in ln]
    for ln in useful[:25]:
        print(" ", ln)

# rtti of vtable 0x29d7030 more carefully — which offset in CArmy?
# dump 16 bytes before 0x29d7030 (COL)
print("\nVT 0x29d7030 rtti", _rtti_name_from_vtable(pe, 0x29d7030))
print("VT 0x29d6fe8 rtti", _rtti_name_from_vtable(pe, 0x29d6fe8))
print("VT 0x29d6d98 rtti", _rtti_name_from_vtable(pe, 0x29d6d98))
