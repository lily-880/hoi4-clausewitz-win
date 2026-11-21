import sys,os,re,json,struct,bisect,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable, tag_for_index
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def lea_xrefs(rva, limit=20):
    hits=[]
    for m in re.finditer(b"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x2d\x35\x3d]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+3)[0]
        dest=text_rva+at+7+rel
        if dest==rva:
            fo=func_of(text_rva+at)
            hits.append((hex(text_rva+at), hex(fo[0]) if fo else None))
            if len(hits)>=limit:
                break
    return hits

print("CWarRelation vt lea", lea_xrefs(0x29dcc08))
# also CRelation 0x29dcb48
print("CRelation vt lea", lea_xrefs(0x29dcb48)[:12])

p=Proc(find_pid("hoi4.exe"))
try:
    def cls(a):
        if not a or a<0x10000 or a>0x7fffffffffff: return None
        try:
            vt=p.ptr(a)
        except Exception:
            return None
        if not vt or not (p.base<=vt<p.base+p.image_size): return None
        try:
            return _rtti_name_from_vtable(pe, vt-p.base)
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)

    # tag table
    tags={}
    for i in range(440):
        try:
            t=tag_for_index(p, gs, i)
        except TypeError:
            try:
                t=tag_for_index(p, i)
            except Exception as e:
                t=str(e)
                break
        except Exception as e:
            t=None
        if t:
            tags[i]=t
    # print interesting
    inv={v:k for k,v in tags.items() if isinstance(v,str)}
    print("n tags", len(tags), "ETH", inv.get("ETH"), "ITA", inv.get("ITA"), "sample", list(tags.items())[:8], "err?" )
    if tags and not any(isinstance(v,str) and len(v)==3 for v in list(tags.values())[:10]):
        print("first tags raw", list(tags.items())[:15])

    # inspect tag_for_index signature
    import inspect
    print("tag_for_index", inspect.signature(tag_for_index), (inspect.getdoc(tag_for_index) or "")[:300])
finally:
    p.close()
