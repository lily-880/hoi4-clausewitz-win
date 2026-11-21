import sys,os,struct,json,re,collections
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
        cols=[]
        for s in pe.sections:
            blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
            for m in re.finditer(re.escape(col_imm), blob):
                col_rva=s.virtual_address+m.start()-0x0C
                raw=pe.read_rva(col_rva, 4)
                if raw and struct.unpack("<I", raw)[0] in (0,1):
                    cols.append(col_rva)
        for col in cols:
            need=struct.pack("<Q", IMAGE+col)
            for s in pe.sections:
                blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
                for m in re.finditer(re.escape(need), blob):
                    vt=s.virtual_address+m.start()+8
                    got=_rtti_name_from_vtable(pe, vt)
                    if got==name:
                        vts.add(vt)
    return sorted(vts)

names=[
    ".?AUSArmyUnitActivityData@@",
    ".?AVCSupplyConsumer@@",
    ".?AVCCombatManager@@",
    ".?AVCOrderInstance@@",
    ".?AVCCombat@@",
    ".?AVCArmyDivisionViewLandCombatEntry@@",
    ".?AVCSupplySystem@@",
    ".?AVCCountrySupplySystem@@",
    ".?AVCSupplyUnits@@",
]
vtmap={}
for n in names:
    vts=vtables_for(n)
    vtmap[n]=[hex(v) for v in vts]
    print(n, [hex(v) for v in vts])
    for vt in vts:
        raw=pe.read_rva(vt, 0x40) or b""
        fns=[]
        for i in range(0,len(raw),8):
            v=struct.unpack_from("<Q", raw, i)[0]
            if IMAGE<=v<IMAGE+0x4000000:
                fns.append(hex(v-IMAGE))
            else:
                break
        print("  slots", fns[:12])

# xrefs of SArmyUnitActivityData vtable (constructor writes lea/mov)
# search immediate IMAGE+vt as qword in .text (absolute) or rip-lea
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address

def qword_xrefs(rva, limit=15):
    need=struct.pack("<Q", IMAGE+rva)
    hits=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(need), blob):
            hits.append((s.name, hex(s.virtual_address+m.start())))
            if len(hits)>=limit:
                return hits
    return hits

def lea_xrefs(rva, limit=20):
    # 48 8D 05/0D/15/1D/2D/35/3D rel32  or 4C 8D 05...
    hits=[]
    for m in re.finditer(b"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x2d\x35\x3d]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+3)[0]
        dest=text_rva+at+7+rel
        if dest==rva:
            hits.append(hex(text_rva+at))
            if len(hits)>=limit:
                break
    return hits

print("\n===== SArmyUnitActivityData vtable refs =====")
for vt in vtables_for(".?AUSArmyUnitActivityData@@"):
    print("vt", hex(vt), "qword", qword_xrefs(vt), "lea", lea_xrefs(vt))

print("\n===== CSupplyConsumer vtable refs =====")
for vt in vtables_for(".?AVCSupplyConsumer@@"):
    print("vt", hex(vt), "lea", lea_xrefs(vt)[:12], "qword_n", len(qword_xrefs(vt,50)))

print("\n===== COrderInstance vtable refs =====")
for vt in vtables_for(".?AVCOrderInstance@@"):
    print("vt", hex(vt), "lea", lea_xrefs(vt)[:12])

# live scan CArmy for these vtables or pointers to them
p=Proc(find_pid("hoi4.exe"))
try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    ar=_pdx_array(p, co+0x290)
    ap=p.ptr(ar["data"])
    want=set()
    for n,vs in vtmap.items():
        for v in vs:
            want.add(int(v,16))
    blob=p.try_read(ap, 0x688) or b""
    hits=[]
    for off in range(0, len(blob)-7, 8):
        v=struct.unpack_from("<Q", blob, off)[0]
        if p.base<=v<p.base+p.image_size:
            rva=v-p.base
            name=_rtti_name_from_vtable(pe, rva)
            if rva in want or (name and any(k in name for k in ("Activity","Supply","Combat","Order","Isolat"))):
                hits.append({"off":hex(off),"rva":hex(rva),"name":name})
        else:
            # maybe pointer to object
            if 0x10000<v<0x7fffffffffff:
                try:
                    vt=p.ptr(v)
                except Exception:
                    continue
                if vt and p.base<=vt<p.base+p.image_size:
                    rva=vt-p.base
                    name=_rtti_name_from_vtable(pe, rva)
                    if rva in want or (name and any(k in (name or "") for k in ("Activity","SupplyConsumer","LandCombat","CombatManager","OrderInstance"))):
                        hits.append({"off":hex(off),"as_ptr_to":hex(v),"rva":hex(rva),"name":name})
    print("\nCArmy 0x688 interesting", json.dumps(hits, indent=2))
    # also scan GS for CombatManager
    gsblob=p.try_read(gs, 0x900) or b""
    gshits=[]
    for off in range(0, len(gsblob)-7, 8):
        v=struct.unpack_from("<Q", gsblob, off)[0]
        if p.base<=v<p.base+p.image_size:
            rva=v-p.base
            name=_rtti_name_from_vtable(pe, rva)
            if name and ("Combat" in name or "Supply" in name):
                gshits.append({"off":hex(off),"rva":hex(rva),"name":name})
        elif 0x10000<v<0x7fffffffffff:
            try:
                vt=p.ptr(v)
            except Exception:
                continue
            if vt and p.base<=vt<p.base+p.image_size:
                name=_rtti_name_from_vtable(pe, vt-p.base)
                if name and ("CombatManager" in name or "SupplySystem" in name or "CountrySupply" in name):
                    gshits.append({"off":hex(off),"ptr":hex(v),"name":name})
    print("GS interesting", json.dumps(gshits, indent=2))
finally:
    p.close()
