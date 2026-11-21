import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
name2={i["name"]:i["token"] for i in mp}
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
        if stop_ret and i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# combatant base writer
fo=func_of(0x147ff20)
end=(fo[1] if fo else 0x147ff20+0x300)
print("0x147ff20 pdata", hex(fo[0]) if fo else None, hex(fo[1]) if fo else None)
lines=clip(0x147ff20, min(end, 0x147ff20+0x400), "research/_t185_clip_combatant_base_0x147ff20.txt")
print("===== 0x147ff20 =====")
print("\n".join(lines[:80]))
print("... toks", [ln for ln in lines if "TOKEN" in ln])

# in_combat tokens
print("\n===== tokens with combat/supply =====")
for i in mp:
    n=i["name"]
    if n in ("in_combat","is_in_combat","is_attacking","is_defending","has_combat","combat_id","land_combat") or n.endswith("_in_combat") or n.startswith("is_") and "combat" in n:
        print(hex(i["token"]), n, "reg", hex(i.get("registration_rva") or 0))

# CArmy vtables from t184 / t165
# main CArmy rtti 0x31462e8 was the name string. Find vtables.
# We know base writer vt 0x29cfcd8 and secondary 0x29d6f88
for vt,label in ((0x29cfcd8,"base_writer"),(0x29d6f88,"secondary_writer")):
    raw=pe.read_rva(vt, 0x80) or b""
    fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,len(raw),8) if struct.unpack_from("<Q", raw, i)[0]>=IMAGE]
    print("VT", label, hex(vt), "rtti", _rtti_name_from_vtable(pe, vt), "fns", fns[:12])

# find primary CArmy vtable (dtor style like CTheatre  first fn not 25416c0 only)
# search rtti .?AVCArmy@@ vtables - reuse method from t184
