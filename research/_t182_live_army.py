import sys, os, struct, json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")

def cstrings_around(rva, before=0x400, after=0x400):
    for s in pe.sections:
        if s.virtual_address <= rva < s.virtual_address+s.virtual_size:
            off=s.raw_ptr+(rva-s.virtual_address)
            start=max(s.raw_ptr, off-before)
            end=min(s.raw_ptr+s.raw_size, off+after)
            blob=pe.data[start:end]
            out=[]; i=0
            while i<len(blob):
                if 32<=blob[i]<127:
                    j=i
                    while j<len(blob) and 32<=blob[j]<127: j+=1
                    if j>i+2 and (j==len(blob) or blob[j]==0):
                        out.append({"rva":hex(s.virtual_address+(start-s.raw_ptr)+i), "s":blob[i:j].decode("ascii")})
                    i=j+1
                else:
                    i+=1
            return out
    return []

print("===== around army_current_supply_ratio =====")
for e in cstrings_around(0x2b39948, 0x300, 0x300):
    print(e)
print("===== around land_combat_id =====")
for e in cstrings_around(0x2b68880, 0x200, 0x200):
    print(e)

# live CArmy
p=Proc(find_pid("hoi4.exe"))
try:
    def ptr(x): return type(x) is int and 0x10000<x<0x7fffffffffff
    def q(a):
        b=p.read(a,8)
        return struct.unpack("<Q", b)[0] if b and len(b)==8 else None
    def i32(a):
        b=p.read(a,4)
        return struct.unpack("<i", b)[0] if b and len(b)==4 else None
    def cls(a):
        if not ptr(a): return None
        try:
            vt=q(a)
            if not ptr(vt): return None
            return _rtti_name_from_vtable(p, vt)
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16) if isinstance(res["country_ptr"],str) else res["country_ptr"]
    ar=_pdx_array(p, co+0x290)
    print("armies", ar)
    comb=_pdx_array(p, gs+0x268)
    print("GS+0x268 combats", comb)

    units=[]
    n=min(ar["size"], 21)
    data=ar["data"]
    for slot in range(n):
        ap=q(data+slot*8)
        uid=struct.unpack("<I", p.read(ap+0x1c,4))[0]
        # scan 0x180-0x280 for pointers + path-like arrays
        rec={"unit_id":uid,"ptr":hex(ap)}
        # +0x200 as possible pdx array or object
        blob=p.read(ap+0x1c0, 0xC0)
        rec["raw_1c0_280"]=blob.hex()
        # interpret common layouts
        fields={}
        for off in range(0x1c0, 0x280, 8):
            v=struct.unpack_from("<Q", blob, off-0x1c0)[0]
            c=None
            if ptr(v):
                c=cls(v)
            fields[hex(off)]={"u64":hex(v), "i32":struct.unpack_from("<i", blob, off-0x1c0)[0], "class":c}
        rec["fields"]=fields
        # specifically pdx at +0x200
        d,cap,sz=struct.unpack_from("<QII", blob, 0x200-0x1c0)
        rec["path200"]={"data":hex(d),"cap":cap,"size":sz,"data_class":cls(d) if ptr(d) else None}
        units.append(rec)
        print("unit", uid, "path200", rec["path200"])
        # print pointer classes in range
        for off,fv in fields.items():
            if fv["class"]:
                print(" ", off, fv["u64"], fv["class"])

    # summarize unique classes in the window
    classes=Counter()
    for u in units:
        for off,fv in u["fields"].items():
            if fv["class"]:
                classes[(off,fv["class"])]+=1
    print("class histogram", classes)
    Path("research/t182_carmy_1c0_280.json").write_text(json.dumps({"combats":comb,"units":[{k:v for k,v in u.items() if k!="raw_1c0_280"} for u in units]}, indent=2, default=str)+"\n", encoding="utf-8")
finally:
    p.close()
