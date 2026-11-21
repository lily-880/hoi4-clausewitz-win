import sys, struct, re, json, os, bisect
from pathlib import Path
from collections import Counter
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from mem import Proc, find_pid
from pe import PE as PE2
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
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

def rva_of(off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None

# PARADROP assert string
print("===== PARADROP GetOrderType string =====")
for m in re.finditer(rb"OriginalOrder.GetOrderType\(\) == ORDER_PARADROP[^\x00]{0,80}", pe.data):
    rva=rva_of(m.start())
    # expand
    off=m.start()
    while off>0 and 32<=pe.data[off-1]<127: off-=1
    end=pe.data.find(b"\x00", m.start())
    s=pe.data[off:end].decode("latin1")
    print(hex(rva_of(off)), repr(s))
    dest=rva_of(off)
    # lea xrefs
    hits=[]
    for mm in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", text_raw):
        if mm.start()+7>len(text_raw): continue
        at=text_rva+mm.start()
        rel=struct.unpack_from("<i", text_raw, mm.start()+3)[0]
        if at+7+rel==dest:
            fo=func_of(at)
            hits.append((hex(at), hex(fo[0]) if fo else None))
    print("xrefs", hits)

# asserts containing InCombat or in combat
print("===== InCombat-like asserts =====")
for m in re.finditer(rb"(InCombat\([^\x00]{0,80}|is not in combat[^\x00]{0,60}|already in combat[^\x00]{0,60}|not in a combat[^\x00]{0,60}|GetLandCombat[^\x00]{0,60}|HasCombat[^\x00]{0,60}|pCombat[^\x00]{0,80})", pe.data, re.I):
    off=m.start()
    while off>0 and 32<=pe.data[off-1]<127: off-=1
    end=pe.data.find(b"\x00", m.start())
    s=pe.data[off:end].decode("latin1","replace") if end!=-1 else m.group().decode()
    if len(s)>140: continue
    if "NDefines" in s or "Error reading" in s: continue
    print(hex(rva_of(off) or 0), repr(s[:140]))
