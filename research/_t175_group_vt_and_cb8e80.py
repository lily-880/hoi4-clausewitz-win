
import sys,struct,json,bisect,os
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from mem import Proc,find_pid
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe=PE(EXE)
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
IMAGE=0x140000000
pd=next(s for s in pe.sections if s.name==".pdata")
rawpd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III",rawpd,o)[:2] for o in range(0,len(rawpd)-11,12)]
starts=[x[0] for x in functions]

def pdata(rva):
    if rva>=IMAGE: rva-=IMAGE
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def typenames(s):
    if not s: return None
    if s.startswith(".?AV") and s.endswith("@@"): return s[4:-2]
    if s.startswith(".?AU") and s.endswith("@@"): return s[4:-2]
    return s

def rtti(vt):
    try: return typenames(_rtti_name_from_vtable(pe,vt))
    except Exception as e: return str(e)

# cb8e80 around 10948a0: 0xcb8f45 to 0xcb90c0
lines=Path("research/_t175_clip_cb8e80_body.txt").read_text(encoding="utf-8").splitlines()
print("===== cb8e80 selected =====")
for l in lines:
    if not l.startswith("0x"): continue
    a=int(l.split()[0],16)
    if 0xcb8f45<=a<=0xcb90c0 or 0xcb9220<=a<=0xcb9328:
        print(l)

# live group vtable
def looks(x): return type(x) is int and 0x10000<x<0x7fffffffffff
p=None
try:
    p=Proc(find_pid("hoi4.exe"))
    session=detect_session(p,pe)
    gs=int(session["signals"]["gs_ptr"],16)
    player=resolve_player_country(p,gs)
    country=int(player["country_ptr"],16) if isinstance(player["country_ptr"],str) else player["country_ptr"]
    def q(a): return struct.unpack("<Q",p.read(a,8))[0]
    def cls(a):
        if not looks(a): return None
        try: vt=q(a)
        except OSError: return None
        if not (p.base<=vt<p.base+p.image_size): return None
        return typenames(_rtti_name_from_vtable(pe,vt-p.base))
    group=0x26cb01e6fa0
    vt=q(group)
    rec={"group":hex(group),"class":cls(group),"vtable":hex(vt),"vtable_rva":hex(vt-p.base)}
    slots=[]
    for i in range(8):
        fn=q(vt+i*8)
        rva=fn-p.base
        w=pdata(rva)
        slots.append({"i":i,"off":hex(i*8),"fn":hex(fn),"rva":hex(rva),"pdata":hex(w[0]) if w else None})
        rec["rtti_of_vt"]=rtti(vt-p.base)
    rec["slots"]=slots
    # group+0x28 request list
    b,c,n=struct.unpack("<QII",p.read(group+0x28,16))
    rec["plus28"]={"begin":hex(b) if looks(b) else b,"cap":c,"count":n}
    items=[]
    if looks(b) and 0<=n<=16:
        for i in range(n):
            rp=q(b+i*8)
            items.append({"ptr":hex(rp),"class":cls(rp)})
    rec["requests"]=items
    rec["contains_1835"]=any(x["ptr"]=="0x26cb1969530" for x in items)
    Path("research/t175_group_vtable_live.json").write_text(json.dumps(rec,indent=2),encoding="utf-8")
    print("\nLIVE group", json.dumps(rec,indent=2))
finally:
    if p is not None: p.close()
