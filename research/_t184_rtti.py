import sys,re,json,struct,bisect,os,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
# --- RTTI name list (scan pe.data for .?AV*Order* / Group / Combat / Command) ---
names=set()
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in re.finditer(rb"\.\?AVC[A-Za-z0-9_]*((Order|Command|Group|Theatre|Theater|Combat|Front|Army)[A-Za-z0-9_]*)@@", blob):
        names.add(m.group().decode("ascii","replace"))
# also looser
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for m in re.finditer(rb"\.\?AVC[A-Za-z0-9_]{0,40}(Order|Command|Combat|Theatre|Theater)[A-Za-z0-9_]{0,40}@@", blob):
        names.add(m.group().decode("ascii","replace"))
interesting=sorted(n for n in names if any(k in n for k in ("Order","Command","Group","Theatre","Theater","Combat","Front","Army","Move","Retreat","Attack","Exercise","Train","Garrison","Supply","Isolat")))
print("RTTI count filtered", len(interesting))
for n in interesting:
    if any(k in n for k in ("Group","Theatre","Theater","Front","LandCombat","UnitCommand","Move","Retreat","Attack","Exercise","Garrison","InCombat","ArmyGroup","Orders","OrderInstance","CCommand@@","CCombat@@")):
        print(" ", n)

# vtable helper
IMAGE=pe.image_base
def vtables_for(name: str):
    pat=name.encode()
    tdescs=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        for m in re.finditer(re.escape(pat), blob):
            tdescs.append(s.virtual_address+m.start()-0x10)
    vts=[]
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
                    if _rtti_name_from_vtable(pe, vt)==name:
                        vts.append(vt)
    return sorted(set(vts))

want_classes=[
    ".?AVCTheatre@@",".?AVCArmyGroup@@",".?AVCTheaterGroup@@",
    ".?AVCOrdersGroup@@",".?AVCOrderGroup@@",".?AVCFront@@",
    ".?AVCLandCombat@@",".?AVCCombat@@",".?AVCCommand@@",
]
# discover additional group/order names from the list
for n in interesting:
    if any(s in n for s in ("OrdersGroup","OrderGroup","ArmyGroup","TheaterGroup","CommandGroup","UnitOrder","MoveOrder","LandCombat","CFront@@","COrderInstance")):
        if n not in want_classes:
            want_classes.append(n)

vt_map={}
for n in want_classes:
    try:
        vts=vtables_for(n)
    except Exception as e:
        print("fail", n, e)
        continue
    fns=[]
    if vts:
        raw=pe.read_rva(vts[0], 0x80) or b""
        fns=[hex(struct.unpack_from("<Q", raw, i)[0]-IMAGE) for i in range(0,min(len(raw),0x50),8) if struct.unpack_from("<Q", raw, i)[0]>=IMAGE]
    vt_map[n]={"vtables":[hex(v) for v in vts[:4]],"n":len(vts),"fns0":fns}
    print("VT", n, vt_map[n])

Path("research/t184_rtti_vtables.json").write_text(json.dumps({"interesting":interesting,"vtables":vt_map}, indent=2)+"\n", encoding="utf-8")
