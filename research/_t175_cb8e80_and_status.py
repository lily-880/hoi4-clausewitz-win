
import sys,struct,json,bisect,os
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_IMM
from mem import Proc,find_pid
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country,read_campaign_summary

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

# 717410 from 0x717520 to ret covering all branches
raw=pe.read_rva(0x717507, 0x70) or b""
ins=list(cs.disasm(raw,0x717507))
print("===== 717410 tail =====")
for i in ins:
    print(hex(i.address), i.mnemonic, i.op_str)
    if i.mnemonic=="ret" and i.address>0x717541:
        break

# cb8e80 from 0xcb8f45 to end
w=pdata(0xcb8e80)
raw=pe.read_rva(0xcb8f45, w[1]-0xcb8f45) or b""
ins=list(cs.disasm(raw,0xcb8f45))
lines=["%s  %s %s"%(hex(i.address),i.mnemonic,i.op_str) for i in ins]
Path("research/_t175_clip_cb8e80_body.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n===== cb8e80 body calls and stores =====")
for i in ins:
    s=i.mnemonic+" "+i.op_str
    if i.mnemonic in ("call","ret") or "rbp" in i.op_str and i.mnemonic.startswith("mov") or "[r13" in i.op_str or "0xf68" in s or "0x200" in s or "0xf88" in s:
        print(hex(i.address), s)

# lea to CReinforcementStatus vtable 0x2a4b878
def find_lea(target_rva):
    text=next(s for s in pe.sections if s.name==".text")
    blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
    va=text.virtual_address
    hits=[]; pos=0
    while True:
        i=blob.find(b"\x8D",pos)
        if i<0: break
        for start,inslen in ((i-1,7),(i,6)):
            if start<0: continue
            if start==i-1 and blob[start] not in (0x48,0x4C,0x4D,0x49):
                continue
            if i+1>=len(blob): continue
            if (blob[i+1] & 0xC7)!=0x05: continue
            disp=struct.unpack_from("<i",blob,i+2)[0]
            insn_rva=va+start
            dest=(insn_rva+inslen+disp)&0xffffffff
            if dest==target_rva:
                w=pdata(insn_rva)
                hits.append((insn_rva, w[0] if w else None))
        pos=i+1
        if len(hits)>30: break
    return hits

leas=find_lea(0x2a4b878)
print("\nLEA CReinforcementStatus vtable", [(hex(a),hex(f) if f else None) for a,f in leas])

# live: CReinforcementStatus +0x20 list and +0x38
def looks(x): return type(x) is int and 0x10000<x<0x7fffffffffff

p=None
try:
    p=Proc(find_pid("hoi4.exe"))
    pe2=PE(p.image_path)
    session=detect_session(p,pe2)
    if not (session.get("in_game") and session.get("session")=="in_game"):
        print("STOP not in game"); raise SystemExit(0)
    gs=int(session["signals"]["gs_ptr"],16)
    player=resolve_player_country(p,gs)
    country=int(player["country_ptr"],16) if isinstance(player["country_ptr"],str) else player["country_ptr"]
    def q(a): return struct.unpack("<Q",p.read(a,8))[0]
    def i32(a): return struct.unpack("<i",p.read(a,4))[0]
    def cls(a):
        if not looks(a): return None
        try: vt=q(a)
        except OSError: return None
        if not (p.base<=vt<p.base+p.image_size): return None
        return typenames(_rtti_name_from_vtable(pe2,vt-p.base))
    status=q(country+0xf78)
    rec={"CReinforcementStatus":hex(status),"class":cls(status)}
    if looks(status):
        rec["plus20"]=hex(q(status+0x20)) if looks(q(status+0x20)) else q(status+0x20)
        rec["plus20_class"]=cls(q(status+0x20)) if looks(q(status+0x20)) else None
        # try as pointer array header {begin, cap, count} at +0x20
        b,c,n=struct.unpack("<QII",p.read(status+0x20,16))
        rec["plus20_header"]={"begin":hex(b) if looks(b) else b,"cap":c,"count":n}
        items=[]
        if looks(b) and 0<=n<=64:
            for i in range(n):
                rp=q(b+i*8)
                items.append({"ptr":hex(rp) if looks(rp) else rp,"class":cls(rp) if looks(rp) else None})
        rec["plus20_items"]=items
        rec["plus28"]=i32(status+0x28); rec["plus2c"]=i32(status+0x2c)
        rec["plus38"]=hex(q(status+0x38)) if looks(q(status+0x38)) else q(status+0x38)
        rec["plus38_class"]=cls(q(status+0x38)) if looks(q(status+0x38)) else None
        rec["known_request_1835"]="0x26cb1969530"
        rec["request_1835_in_list"]=any(x.get("ptr")=="0x26cb1969530" for x in items)
    Path("research/t175_reinforcement_status_live.json").write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding="utf-8")
    print("\nLIVE status", json.dumps(rec,indent=2,ensure_ascii=False)[:4000])
finally:
    if p is not None: p.close()
