import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

# CountryRef in schema
schema=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
print("===== CountryRef =====")
print(json.dumps(schema["$defs"].get("CountryRef"), indent=2, ensure_ascii=False))

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base

# RTTI names with War
pat=re.compile(rb"\.\?AV[A-Za-z0-9_]*@@")
found=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in pat.finditer(blob):
        name=m.group().decode("ascii","replace")
        if "War" in name or "Truce" in name or "Peace" in name or "Diplo" in name and "War" in name:
            found.append((hex(s.virtual_address+m.start()), name))
print("\n===== RTTI War/Truce/Peace =====", len(found))
for x in found:
    print(" ", x)

# token xrefs for key tokens
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

def token_xrefs(tok):
    imm=struct.pack("<I", tok)
    funcs=set()
    hits=[]
    for prefix in (b"\xba", b"\xb8", b"\xb9", b"\x41\xba", b"\x41\xb8", b"\x41\xb9"):
        for m in re.finditer(re.escape(prefix+imm), text_raw):
            at=text_rva+m.start()
            fo=func_of(at)
            f=fo[0] if fo else None
            funcs.add(f)
            hits.append(at)
    return sorted(x for x in funcs if x), len(hits)

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
want=["war","war_with","at_war","war_relation","war_name","has_war","enemies","truce","peace","start_date","war_score_first_vs_second"]
name2tok={i["name"]:i["token"] for i in mp}
print("\n===== token xref funcs =====")
for n in want:
    tok=name2tok[n]
    funcs,nh=token_xrefs(tok)
    print(n, hex(tok), "hits", nh, "funcs", [hex(f) for f in funcs[:18]], ("..." if len(funcs)>18 else f"n={len(funcs)}"))
