
"""Read-only: look for stored 1409810 infantry need (77*100000) on known roots and the equipment type."""
from __future__ import annotations
import os,sys,json,struct
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

NEED77=77*100000
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
    def i64(a): return struct.unpack('<q',p.read(a,8))[0]
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

    # infantry type from own unit pool (already proven path)
    data,cap,n=struct.unpack('<QII',p.read(country+0x290,16))
    army=q(data)  # first army; find 1835
    typ=None
    for j in range(n):
        ap=q(data+j*8)
        if i32(ap+0x1c)==1835:
            army=ap
            begin,pcap,pn=struct.unpack('<QII',p.read(ap+0x348+8,16))
            typ=q(begin)
            break
    type_info={'ptr':hex(typ),'class':cls(typ),'name':string(typ+0x18) if typ else None}
    if typ:
        type_info['plus5e0']=hex(q(typ+0x5e0))
        type_info['plus5e0_class']=cls(q(typ+0x5e0))
        type_info['plus608_i64']=i64(typ+0x608)
        type_info['plus648_i64']=i64(typ+0x648)
        type_info['plus608_as_amount']=i64(typ+0x608)//100000 if i64(typ+0x608)%100000==0 else None
        type_info['plus648_as_amount']=i64(typ+0x648)//100000 if i64(typ+0x648)%100000==0 else None

    # logistics +0x20 country backlink, and scan selected offsets for 77*100000
    roots=[]
    def add(name,addr,size):
        if looks(addr) and 0<size<=0x2000:
            roots.append((name,addr,size,cls(addr)))
    add('country',country,0x2000)
    for name,off,sz in (('CReinforcementStatus',0xf78,0x200),('CDeploymentStatus',0xf70,0x200),
                        ('CLogisticsStatus',0xf98,0x400),('CCountryOccupationStatus',0xfd0,0x200),
                        ('CCountryOperationManager',0x15a8,0x200),('CProductionStatus',0xf68,0x400),
                        ('CCountryResources',0x11f8,0x800)):
        add(name,q(country+off),sz)
    # template+0x120 need pool of 1835
    tmpl=q(army+0x3b8)
    add('template_1835',tmpl,0x200)
    add('template_need_pool',tmpl+0x120,0x80)
    add('CEquipmentType_infantry',typ,0x800 if typ else 0)
    add('CArmyRequests_1835',q(army+0x478),0x100)
    # logistics +0x20
    logi=q(country+0xf98)
    logi_info={'ptr':hex(logi),'class':cls(logi),'plus20':hex(q(logi+0x20)),'plus20_is_country':q(logi+0x20)==country,
               'plus28_array':struct.unpack('<QII',p.read(logi+0x28,16))}

    needle=struct.pack('<q',NEED77)
    needle77=struct.pack('<q',77)
    hits={'7700000':[],'77':[]}
    for name,start,size,c in roots:
        blob=p.try_read(start,size)
        if not blob: continue
        for label,nd in (('7700000',needle),('77',needle77)):
            off=0
            while True:
                i=blob.find(nd,off)
                if i<0: break
                # for bare 77, only report 8-byte aligned qwords that are exactly 77 (avoid noise later in summary)
                if label=='77' and (i%8)!=0:
                    off=i+1; continue
                hits[label].append({'region':name,'class':c,'offset':hex(i),'addr':hex(start+i),'value':struct.unpack_from('<q',blob,i)[0] if i+8<=len(blob) else None})
                off=i+1

    # also dump a few logistics qwords around 0x00-0x80
    logi_scan={}
    for off in range(0,0x80,8):
        v=q(logi+off)
        rec={'u64':hex(v),'i64':i64(logi+off)}
        c=cls(v)
        if c: rec['class']=c
        logi_scan[hex(off)]=rec

    out={'pid':p.pid,'tag':player.get('tag'),'hour_tick':i32(gs+0x468),
         'expected_need_raw':NEED77,'expected_need':77,
         'infantry_type':type_info,'logistics':logi_info,'logistics_scan':logi_scan,
         'cdb4b0_implies_worklist_is_template_plus120':True,
         'bounded_hits':hits}
    Path('research/t173_stored_need_live.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in out if k not in ('logistics_scan',)},indent=2,default=str))
    print('logistics_scan',json.dumps(logi_scan,indent=2))
finally:
    if p is not None: p.close()
