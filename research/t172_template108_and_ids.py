
"""Read-only: unit_id%24 vs hour residue, and template+0x108 type."""
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

CONST=0x29C55C0
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
    tick=i32(gs+0x468)
    residue=(tick-CONST)%24
    data,cap,n=struct.unpack('<QII',p.read(country+0x290,16))
    rows=[]
    for j in range(n):
        ap=q(data+j*8)
        uid=i32(ap+0x1c)
        tmpl=q(ap+0x3b8)
        rec={'unit_id':uid,'unit_id_mod24':uid%24,'matches_this_hour':(uid%24)==residue,
             'template_class':cls(tmpl)}
        if cls(tmpl)=='CReferencedDivisionTemplate':
            rec['tmpl_plus108_class']=cls(tmpl+0x108)
            rec['tmpl_plus120_class']=cls(tmpl+0x120)
            # header-like at +0x108
            rec['tmpl_plus108_q0']=hex(q(tmpl+0x108))
            rec['tmpl_plus108_first_ptr_class']=cls(q(tmpl+0x108))
        req=q(ap+0x478)
        rec['requests_e0']=i32(req+0xe0) if cls(req)=='CArmyRequests' else None
        rec['e0_equals_tick']=rec['requests_e0']==tick
        rows.append(rec)
    out={'pid':p.pid,'hour_tick':tick,'const':CONST,'hour_residue_mod24':residue,
         'matching_unit_ids':[r['unit_id'] for r in rows if r['matches_this_hour']],
         'stamped_unit_ids':[r['unit_id'] for r in rows if r['e0_equals_tick']],
         'rows':rows,'speed_notch':fields.get('game_speed_notch'),'date':fields.get('date_full')}
    Path('research/t172_stagger_live.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in out if k!='rows'},indent=2))
    print(json.dumps(rows,indent=2))
finally:
    if p is not None: p.close()
