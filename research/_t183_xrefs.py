import json,re,sys,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={item["token"]:item["name"] for item in mp}
name2={item["name"]:item["token"] for item in mp}

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
rdata=next(s for s in pe.sections if s.name==".rdata")
rdata_raw=pe.data[rdata.raw_ptr:rdata.raw_ptr+rdata.raw_size]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

interesting = {
    0x385b:"is_assigned",
    0x385e:"is_field_marshal",
    0x39bb:"is_leading_army_group",
    0x3892:"army_group",
    0x34e2:"field_marshal",
    0x2f1a:"theatre",
    0x35d1:"theater_group",
    0x3801:"field_marshal_group",
    0x2c5b:"commander",
    0x28b7:"leader",
    0xcb:"commandlist",
    0x35bd:"num_armies_in_combat",
    0x4ced:"army_current_supply_ratio",
    0x2916:"combat",
}
# also search names in rdata / text for InCombat, is_in_combat, CLandCombat
needles=[b"IsInCombat", b"is_in_combat", b"in_combat", b"CLandCombat", b"InCombat(", b"is in combat"]
str_hits={}
for nd in needles:
    hits=[]
    # scan all pe.data for ascii
    for m in re.finditer(re.escape(nd), pe.data):
        # convert file off to rva roughly via sections
        off=m.start()
        rva=None
        for s in pe.sections:
            if s.raw_ptr <= off < s.raw_ptr+s.raw_size:
                rva=s.virtual_address+(off-s.raw_ptr)
                break
        hits.append(hex(rva) if rva is not None else f"file+{off}")
    str_hits[nd.decode(errors="replace")]=hits[:20]+([f"...{len(hits)}"] if len(hits)>20 else [])

xrefs={}
for tok,name in interesting.items():
    imm=struct.pack("<I", tok)
    hits=[]
    for prefix,kind in ((b"\xba","mov edx"), (b"\xb8","mov eax"), (b"\xb9","mov ecx"), (b"\x41\xba","mov r10d"), (b"\x41\xb8","mov r8d"), (b"\x41\xb9","mov r9d")):
        for m in re.finditer(re.escape(prefix+imm), text_raw):
            at=text_rva+m.start()
            fo=func_of(at)
            hits.append({"at":hex(at),"kind":kind,"func":hex(fo[0]) if fo else None,"fn_size": (fo[1]-fo[0]) if fo else None})
    xrefs[name]={"token":hex(tok),"count":len(hits),"hits":hits[:25]}

# RTTI names
rtti=[]
for pat in [b".?AVCLandCombat@@", b".?AVCCombat@@", b".?AVCArmyGroup@@", b".?AVCTheaterGroup@@", b".?AVCTheatre@@", b".?AVCCommand@@", b".?AVCUnitCommand@@", b".?AVCArmy@@", b".?AVCArmyLeader@@"]:
    for m in re.finditer(re.escape(pat), pe.data):
        off=m.start(); rva=None
        for s in pe.sections:
            if s.raw_ptr<=off<s.raw_ptr+s.raw_size:
                rva=s.virtual_address+(off-s.raw_ptr); break
        rtti.append({"name":pat.decode(),"rva":hex(rva) if rva else None})

out={"xrefs":xrefs,"strings":str_hits,"rtti":rtti}
Path("research/t183_token_xrefs.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print("STRINGS", json.dumps(str_hits, indent=2))
print("RTTI", json.dumps(rtti, indent=2))
for name,v in xrefs.items():
    print(name, v["token"], "n=", v["count"], "funcs", sorted({h["func"] for h in v["hits"] if h["func"]})[:15])
