import sys, json, os, struct
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable, read_campaign_summary
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
p=Proc(find_pid("hoi4.exe"))

def arr(obj, data_off):
    try:
        a=_pdx_array(p, obj+data_off)
        return a
    except Exception as e:
        return {"error": str(e)}

def cls(ptr):
    try:
        if not ptr or ptr < 0x10000:
            return None
        vt=p.u64(ptr)
        return _rtti_name_from_vtable(pe, vt-p.base)
    except Exception as e:
        return f"err:{e}"

def try_u32(addr):
    b=p.try_read(addr,4)
    return struct.unpack("<I", b)[0] if b and len(b)==4 else None

def try_u64(addr):
    b=p.try_read(addr,8)
    return struct.unpack("<Q", b)[0] if b and len(b)==8 else None

# country list: look at how resolve works / t186
# import after inspecting signature
import inspect
from gamestate import resolve_player_country as rpc
# find countries helper
import gamestate as gsmod
names=[n for n in dir(gsmod) if "countr" in n.lower() or "enum" in n.lower() or "list_" in n.lower()]
print("gamestate helpers", names)

try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    print("player", {k:res[k] for k in res if k in ("tag","index","ptr","country_ptr","player_index","ok") or "ptr" in k or "tag" in k or "index" in k})
    print("player keys", list(res.keys()))
    cptr = res.get("country_ptr") or res.get("ptr") or res.get("country")
    if isinstance(cptr,str):
        cptr=int(cptr,16)
    print("cptr", hex(cptr) if cptr else None, "pause", p.read(int(session['signals']['idler_ptr'],16)+0x6c1,1)[0])
finally:
    p.close()
