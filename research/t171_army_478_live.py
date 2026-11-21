
"""Read-only: CArmy+0x478 reinforcement object presence for own units."""
from __future__ import annotations
import os,sys,json,struct,hashlib
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country,read_campaign_summary

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
    if not (session.get('in_game') and session.get('session')=='in_game'):
        print('STOP not in game'); raise SystemExit(0)
    gs=int(session['signals']['gs_ptr'],16)
    fields=read_campaign_summary(p,gs)['fields']
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
    def arr(a):
        data,cap,size=struct.unpack('<QII',p.read(a,16))
        return data,cap,size
    hour_tick=i32(gs+0x468)
    data,cap,n=arr(country+0x290)
    rows=[]
    for j in range(n):
        ap=q(data+j*8)
        uid=i32(ap+0x1c)
        obj=q(ap+0x478)
        rec={'unit_id':uid,'army':hex(ap),'plus478':hex(obj) if looks(obj) or obj==0 else obj,'plus478_class':cls(obj) if looks(obj) else None}
        if looks(obj):
            rec['plus478_plus8']=hex(q(obj+8))
            rec['plus478_plus8_class']=cls(q(obj+8))
            rec['plus478_plus8_is_this_army']=q(obj+8)==ap
            rec['plus478_e0']=i32(obj+0xe0) if True else None
            rec['plus478_e0_vs_hour_tick']={'e0':i32(obj+0xe0),'hour_tick':hour_tick}
            # if this looks like group at +0 or +0x18
            for off in (0,0x10,0x18,0x20,0x28,0x38):
                rec[f'off_{hex(off)}_class']=cls(obj+off) if off==0 else cls(q(obj+off)) if looks(q(obj+off)) else None
        rows.append(rec)
    out={'pid':p.pid,'hour_tick':hour_tick,'rows':rows,
         'nonnull_478':[r['unit_id'] for r in rows if r['plus478'] not in ('0x0',0)],
         'class_of_478':{r['plus478_class'] for r in rows if r.get('plus478_class')}}
    # set is not json
    out['class_of_478']=list({r['plus478_class'] for r in rows if r.get('plus478_class')})
    Path('research/t171_army_478_live.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in out if k!='rows'},indent=2))
    print(json.dumps(rows,indent=2))
finally:
    if p is not None: p.close()
