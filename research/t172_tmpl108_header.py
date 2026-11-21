
from __future__ import annotations
import os,sys,json,struct
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country

def looks(x): return type(x) is int and 0x10000<x<0x7fffffffffff
def typenames(s):
    if not s: return None
    if s.startswith('.?AV') and s.endswith('@@'): return s[4:-2]
    if s.startswith('.?AU') and s.endswith('@@'): return s[4:-2]
    return s
p=None
try:
    p=Proc(find_pid('hoi4.exe'))
    pe=PE(p.image_path)
    session=detect_session(p,pe)
    gs=int(session['signals']['gs_ptr'],16)
    player=resolve_player_country(p,gs)
    country=int(player['country_ptr'],16) if isinstance(player['country_ptr'],str) else player['country_ptr']
    def q(a): return struct.unpack('<Q',p.read(a,8))[0]
    def i32(a): return struct.unpack('<i',p.read(a,4))[0]
    def cls(a):
        if not looks(a): return None
        try: vt=q(a)
        except OSError: return None
        if not (p.base<=vt<p.base+p.image_size): return None
        return typenames(_rtti_name_from_vtable(pe,vt-p.base))
    def string(a):
        blob=p.try_read(a,32)
        if not blob or len(blob)<32: return None
        size,cap=struct.unpack_from('<QQ',blob,16)
        if not 0<=size<=256 or cap<size: return None
        data=blob[:size] if cap<=15 else p.try_read(struct.unpack_from('<Q',blob)[0], size)
        if data is None: return None
        try: return data.decode('utf-8')
        except Exception: return None
    data,cap,n=struct.unpack('<QII',p.read(country+0x290,16))
    # one army to get CArmy vtable slot of ce4fc0
    ap0=q(data)
    vt=q(ap0)
    target=p.base+0xce4fc0
    slot=None
    for i in range(0, 0x200, 8):
        if q(vt+i)==target:
            slot=i
            break
    rows=[]
    seen_tmpl=set()
    for j in range(n):
        ap=q(data+j*8)
        uid=i32(ap+0x1c)
        tmpl=q(ap+0x3b8)
        if tmpl in seen_tmpl and uid!=1835:
            continue
        seen_tmpl.add(tmpl)
        # c44c40: begin=[obj+8], count=i32[obj+0x14], stride 16
        begin=q(tmpl+0x108+8)
        count=i32(tmpl+0x108+0x14)
        capv=i32(tmpl+0x108+0x10)
        entries=[]
        if 0<=count<=64 and looks(begin):
            for k in range(count):
                tp=q(begin+k*16)
                amt=struct.unpack('<q',p.read(begin+k*16+8,8))[0]
                entries.append({'type':string(tp+0x18) if cls(tp)=='CEquipmentType' else cls(tp),'amount_raw':amt,'amount':amt//100000 if amt%100000==0 else None})
        rows.append({'unit_id':uid,'tmpl':hex(tmpl),'begin':hex(begin) if looks(begin) or begin==0 else begin,'count':count,'cap':capv,'entries':entries})
    out={'ce4fc0_vtable_slot_offset':hex(slot) if slot is not None else None,'slot_index': (slot//8) if slot is not None else None,'templates':rows}
    Path('research/t172_template108_entries.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(out,indent=2))
finally:
    if p is not None: p.close()
