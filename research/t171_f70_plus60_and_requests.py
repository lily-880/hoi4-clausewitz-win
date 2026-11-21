
"""Read-only inspect of official 1409890 deployment array (CDeploymentStatus+0x60)
and request-creation distinctions among short own units.

No Post/write/speed/campaign/save/heap-sweep. No method execution.
"""
from __future__ import annotations
import os, sys, json, struct, hashlib
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable, detect_session, resolve_player_country, read_campaign_summary
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

HERE=Path(__file__).resolve().parent
profile=json.loads((HERE.parent/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'))

def looks_ptr(x):
    return type(x) is int and 0x10000<x<0x7fffffffffff

def typenames(s):
    if not s: return None
    if s.startswith('.?AV') and s.endswith('@@'): return s[4:-2]
    if s.startswith('.?AU') and s.endswith('@@'): return s[4:-2]
    return s

p=None
try:
    p=Proc(find_pid('hoi4.exe'))
    h=hashlib.sha256()
    with open(p.image_path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    if h.hexdigest().upper()!=profile['exe_sha256']:
        raise SystemExit('fingerprint mismatch')
    pe=PE(p.image_path)
    session=detect_session(p,pe)
    if not (session.get('in_game') and session.get('session')=='in_game'):
        print('STOP not in game'); raise SystemExit(0)
    gs=int(session['signals']['gs_ptr'],16)
    fields=read_campaign_summary(p,gs)['fields']
    player=resolve_player_country(p,gs)
    country=int(player['country_ptr'],16) if isinstance(player['country_ptr'],str) else player['country_ptr']

    def q(a): return struct.unpack('<Q', p.read(a,8))[0]
    def i32(a): return struct.unpack('<i', p.read(a,4))[0]
    def i64(a): return struct.unpack('<q', p.read(a,8))[0]
    def cls(a):
        if not looks_ptr(a): return None
        try: vt=q(a)
        except OSError: return None
        if not (p.base<=vt<p.base+p.image_size): return None
        return _rtti_name_from_vtable(pe, vt-p.base)
    def cname(a): return typenames(cls(a))
    def string(a):
        blob=p.try_read(a,32)
        if not blob or len(blob)<32: return None
        size,cap=struct.unpack_from('<QQ',blob,16)
        if not 0<=size<=256 or cap<size: return None
        data=blob[:size] if cap<=15 else p.try_read(struct.unpack_from('<Q',blob)[0], size)
        if data is None: return None
        try: return data.decode('utf-8')
        except Exception: return None
    def arr(a):
        data,cap,size=struct.unpack('<QII', p.read(a,16))
        return {'data':data,'capacity':cap,'size':size}
    def typed_amounts(pool):
        c=cname(pool)
        if c not in ('CEquipmentVariantPool','CEquipmentArcheTypePool'):
            return {'class':c}
        begin,cap,n=struct.unpack('<QII', p.read(pool+8,16))
        if n<0 or n>64 or not looks_ptr(begin):
            return {'class':c,'error':'bad header','n':n}
        stride,off=(24,16) if c=='CEquipmentVariantPool' else (16,8)
        rows=[]
        for j in range(n):
            rec=p.read(begin+j*stride, stride)
            tp=struct.unpack_from('<Q',rec,0)[0]
            raw=struct.unpack_from('<q',rec,off)[0]
            nm=string(tp+0x18) if cname(tp)=='CEquipmentType' else None
            item={'equipment_type':nm,'amount_raw':raw,'amount': raw//100000 if raw%100000==0 else None}
            rows.append(item)
        return {'class':c,'count':n,'rows':rows}

    dep=q(country+0xf70)
    # official array is status+0x60 (b2cb40)
    official=arr(dep+0x60)
    plus20=arr(dep+0x20)
    # also scan nearby headers for completeness (structure only)
    nearby={}
    for off in range(0,0xC0,8):
        try:
            h=arr(dep+off)
        except OSError:
            continue
        if 0<=h['size']<=512 and (looks_ptr(h['data']) or (h['data']==0 and h['size']==0)):
            classes={}
            sample=None
            if looks_ptr(h['data']) and h['size']>0:
                first=q(h['data'])
                sample=cname(first)
                # class counts only, cap 512 already
                for j in range(h['size']):
                    c=cname(q(h['data']+j*8)) or 'null'
                    classes[c]=classes.get(c,0)+1
            nearby[hex(off)]={'capacity':h['capacity'],'size':h['size'],'first_class':sample,'class_counts':classes}

    items=[]
    deficits={'by_type':{}}
    if 0<=official['size']<=256 and looks_ptr(official['data']):
        for j in range(official['size']):
            ip=q(official['data']+j*8)
            rec={'index':j,'ptr':hex(ip),'class':cname(ip)}
            # current pool at +0x20 (31f8b0)
            rec['current_pool']=typed_amounts(ip+0x20)
            # template chain d498a0
            try:
                a=q(ip+0xb8)
            except OSError:
                a=0
            rec['plus_b8']={'ptr':hex(a) if looks_ptr(a) or a==0 else a,'class':cname(a)}
            tmpl=None
            if looks_ptr(a):
                b=q(a+0x38)
                rec['plus_b8_38']={'ptr':hex(b) if looks_ptr(b) or b==0 else b,'class':cname(b)}
                if looks_ptr(b):
                    t=q(b+0x20)
                    rec['template']={'ptr':hex(t) if looks_ptr(t) or t==0 else t,'class':cname(t)}
                    if cname(t)=='CReferencedDivisionTemplate':
                        tmpl=t
                        rec['need_pool']=typed_amounts(t+0x120)
            # try unit identity fields without assuming CArmy layout blindly
            rec['i32_fields']={}
            for off in (0x10,0x14,0x18,0x1c,0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x44,0x48,0x4c,0x50,0x54,0x58,0x5c,0x60,0x64,0x68,0x6c,0x70,0x74,0x78,0x7c,0x80,0x84,0x88,0x8c,0x90,0x94,0x98,0x9c,0xa0,0xa4,0xa8,0xac,0xb0,0xb4):
                try:
                    rec['i32_fields'][hex(off)]=i32(ip+off)
                except OSError:
                    pass
            # interesting pointers
            rec['ptr_fields']={}
            for off in (0x08,0x10,0x18,0x28,0x30,0x38,0x40,0x48,0x50,0x58,0x60,0x68,0x70,0x78,0x80,0x88,0x90,0x98,0xa0,0xa8,0xb0,0xb8,0xc0,0xc8,0xd0):
                try:
                    v=q(ip+off)
                except OSError:
                    continue
                c=cname(v)
                if c or looks_ptr(v):
                    rec['ptr_fields'][hex(off)]={'ptr':hex(v) if looks_ptr(v) else v,'class':c}
            # deficit need-current for matching types
            need_rows=(rec.get('need_pool') or {}).get('rows') or []
            cur_rows=(rec.get('current_pool') or {}).get('rows') or []
            cur={r['equipment_type']:r.get('amount') for r in cur_rows if r.get('equipment_type')}
            need={r['equipment_type']:r.get('amount') for r in need_rows if r.get('equipment_type')}
            rec['deficit']={}
            for typ,nv in need.items():
                cv=cur.get(typ,0) or 0
                nv=nv or 0
                d=nv-cv
                rec['deficit'][typ]={'need':nv,'current':cv,'deficit':d}
                if typ not in deficits['by_type']:
                    deficits['by_type'][typ]={'need':0,'current':0,'positive_deficit_sum':0,'items_positive':0,'items':0}
                deficits['by_type'][typ]['need']+=nv
                deficits['by_type'][typ]['current']+=cv
                deficits['by_type'][typ]['items']+=1
                if d>0:
                    deficits['by_type'][typ]['positive_deficit_sum']+=d
                    deficits['by_type'][typ]['items_positive']+=1
            items.append(rec)

    # Request need-produced (official F78 contribution)
    rs=q(country+0xf78)
    reqs=[]
    rh=arr(rs+0x20)
    if 0<=rh['size']<=64 and looks_ptr(rh['data']):
        for j in range(rh['size']):
            gp=q(rh['data']+j*8)
            army=q(gp+0x20)
            uid=i32(army+0x1c) if cname(army)=='CArmy' else None
            eh=arr(gp+0x28)
            for k in range(eh['size'] if 0<=eh['size']<=256 and looks_ptr(eh['data']) else 0):
                ep=q(eh['data']+k*8)
                need=typed_amounts(ep+0x78)
                prod=typed_amounts(ep+0x38)
                contrib={}
                nmap={r['equipment_type']:r.get('amount') for r in need.get('rows') or [] if r.get('equipment_type')}
                pmap={r['equipment_type']:r.get('amount') for r in prod.get('rows') or [] if r.get('equipment_type')}
                for typ,nv in nmap.items():
                    pv=pmap.get(typ,0) or 0
                    contrib[typ]={'need':nv or 0,'produced':pv,'need_minus_produced':(nv or 0)-pv}
                reqs.append({'unit_id':uid,'army_class':cname(army),'need':need,'produced':prod,'contribution_need_minus_produced':contrib})

    # Compare fielded short units vs request-bearing 1835: a few already-known fields
    army_h=arr(country+0x290)
    fielded=[]
    for j in range(army_h['size'] if 0<=army_h['size']<=256 and looks_ptr(army_h['data']) else 0):
        ap=q(army_h['data']+j*8)
        if cname(ap)!='CArmy':
            continue
        uid=i32(ap+0x1c)
        cur=typed_amounts(ap+0x348)
        tmpl=q(ap+0x3b8)
        need=typed_amounts(tmpl+0x120) if cname(tmpl)=='CReferencedDivisionTemplate' else {}
        nmap={r['equipment_type']:r.get('amount') for r in need.get('rows') or [] if r.get('equipment_type')}
        pmap={r['equipment_type']:r.get('amount') for r in cur.get('rows') or [] if r.get('equipment_type')}
        defs={}
        for typ,nv in nmap.items():
            cv=pmap.get(typ,0) or 0
            defs[typ]={'need':nv or 0,'current':cv,'deficit':(nv or 0)-cv}
        fielded.append({'unit_id':uid,'ptr':hex(ap),'template':cname(tmpl),'deficits':defs,'has_request':any(r['unit_id']==uid for r in reqs)})

    out={
        'pid':p.pid,'tag':player.get('tag'),'index':player['player_index'],
        'speed_notch':fields.get('game_speed_notch'),'date':fields.get('date_full'),
        'read_only':True,'no_method_execution':True,
        'deployment_plus20_is_not_1409890_source':{'header':{'capacity':plus20['capacity'],'size':plus20['size']},'note':'CSubUnitDefinition catalog; b2cb40 returns status+0x60, not +0x20'},
        'deployment_plus60_official':{'capacity':official['capacity'],'size':official['size'],'data':hex(official['data']) if looks_ptr(official['data']) or official['data']==0 else official['data']},
        'deployment_nearby_array_class_counts':nearby,
        'deployment_items':items,
        'deployment_deficit_sums':deficits,
        'reinforcement_request_contributions':reqs,
        'fielded_units_for_contrast':fielded,
    }
    Path(HERE/'t171_f70_plus60_and_requests.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({
        'pid':p.pid,'plus60':out['deployment_plus60_official'],
        'nearby':{k:{'size':v['size'],'cap':v['capacity'],'classes':v['class_counts']} for k,v in nearby.items() if v['size'] or v['capacity']},
        'item_count':len(items),
        'item_classes':{c:sum(1 for i in items if i['class']==c) for c in {i['class'] for i in items}},
        'item_summaries':[{
            'index':i['index'],'class':i['class'],
            'current':i.get('current_pool'),'need':i.get('need_pool'),
            'deficit':i.get('deficit'),
            'plus_b8':i.get('plus_b8'),'template':i.get('template'),
            'i32_subset':{k:v for k,v in i.get('i32_fields',{}).items() if v not in (0,None) and abs(v)<1_000_000},
        } for i in items],
        'deploy_sums':deficits,
        'request_contrib':reqs,
        'fielded':[{'unit_id':u['unit_id'],'has_request':u['has_request'],'deficits':u['deficits']} for u in fielded],
    },ensure_ascii=False,indent=2))
finally:
    if p is not None:
        p.close()
