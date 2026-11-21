
"""Read-only: infantry stock, type+0x598, logistics+8 mode objects, request 3/80 still."""
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

p=None
try:
    p=Proc(find_pid('hoi4.exe'))
    pe=PE(p.image_path)
    session=detect_session(p,pe)
    if not (session.get('in_game') and session.get('session')=='in_game'):
        Path('research/t174_alloc_and_stock_live.json').write_text(json.dumps({'stop':'not in game','pid':p.pid,'session':session.get('session')},indent=2),encoding='utf-8')
        print('STOP not in game'); raise SystemExit(0)
    gs=int(session['signals']['gs_ptr'],16)
    fields=read_campaign_summary(p,gs)['fields']
    player=resolve_player_country(p,gs)
    country=int(player['country_ptr'],16) if isinstance(player['country_ptr'],str) else player['country_ptr']
    def q(a): return struct.unpack('<Q',p.read(a,8))[0]
    def i64(a): return struct.unpack('<q',p.read(a,8))[0]
    def i32(a): return struct.unpack('<i',p.read(a,4))[0]
    def u32(a): return struct.unpack('<I',p.read(a,4))[0]
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
    def amt_rows(pool, type_stride, var_off, var_stride, limit=32):
        if not looks(pool): return {'error':'bad pool'}
        begin,cap,n=struct.unpack('<QII',p.read(pool+8,16))
        rows=[]
        for i in range(min(n,limit)):
            base=begin+i*type_stride
            typ=q(base)
            rec={'type':hex(typ),'class':cls(typ),'name':string(typ+0x18) if looks(typ) else None}
            if type_stride==24:
                rec['total_raw']=i64(base+16)
                rec['total']=rec['total_raw']//100000 if rec['total_raw']%100000==0 else rec['total_raw']
                b,c=i32(base+8),i32(base+12)
                rec['variants']=[]
                # begin/count of variants may be packed; follow common layout {ptr, begin i32, count i32, total}
                # actually {ptr, begin, count, total} - begin might be a pointer at +8? t170 used _typed_equipment_amounts
            else:
                rec['amount_raw']=i64(base+var_off)
                rec['amount']=rec['amount_raw']//100000 if rec['amount_raw']%100000==0 else rec['amount_raw']
            rows.append(rec)
        return {'ptr':hex(pool),'class':cls(pool),'begin':hex(begin) if looks(begin) else begin,'cap':cap,'count':n,'rows':rows}

    hour_tick=i32(gs+0x468)
    data,cap,n=struct.unpack('<QII',p.read(country+0x290,16))
    army=None; typ=None
    for j in range(n):
        ap=q(data+j*8)
        if i32(ap+0x1c)==1835:
            army=ap
            begin,pcap,pn=struct.unpack('<QII',p.read(ap+0x348+8,16))
            typ=q(begin) if pn else None
            break
    prod=q(country+0xf68)
    logi=q(country+0xf98)
    reqs=q(army+0x478) if army else 0
    # request via group +0x10 + requests at +0x28
    request=None
    if looks(reqs):
        group=q(reqs+0x10)
        if looks(group):
            b,c,cn=struct.unpack('<QII',p.read(group+0x28+8,16)) if False else (0,0,0)
            # group_requests = 40 = +0x28, array of pointers?
            # try +0x28 as pointer-array header at group+0x28
            try:
                gb,gcap,gn=struct.unpack('<QII',p.read(group+0x28,16))
            except Exception:
                gb,gcap,gn=0,0,0
            # the header might be {begin, cap, count} starting at +0x28 or +0x30
            # t170 used LoadedReader; fallback: CArmyRequests+0x38 count +0x44 from 15a5c80
        # 15a5c80: requests at [CArmyRequests+0x38], count [+0x44]
        rbegin=q(reqs+0x38)
        rcount=i32(reqs+0x44)
        request_list=[]
        if looks(rbegin) and 0<rcount<32:
            for i in range(rcount):
                rp=q(rbegin+i*8)
                request_list.append({'ptr':hex(rp),'class':cls(rp)})
                if request is None:
                    request=rp
        else:
            request_list={'rbegin':hex(rbegin) if looks(rbegin) else rbegin,'rcount':rcount}

    def pool_amounts(pool, stride, amt_off):
        if not looks(pool): return None
        begin,cap,n=struct.unpack('<QII',p.read(pool+8,16))
        rows=[]
        if looks(begin):
            for i in range(min(n,16)):
                typ=q(begin+i*stride)
                raw=i64(begin+i*stride+amt_off)
                rows.append({'type':hex(typ),'class':cls(typ),'name':string(typ+0x18) if looks(typ) else None,
                             'raw':raw,'amount':raw//100000 if raw%100000==0 else raw})
        return {'ptr':hex(pool),'class':cls(pool),'count':n,'cap':cap,'rows':rows}

    stock=pool_amounts(prod+0x200, 24, 16) if looks(prod) else None
    # also try variant-pool type-row total at +16

    type_info=None
    if looks(typ):
        type_info={'ptr':hex(typ),'class':cls(typ),'name':string(typ+0x18),
                   'plus598_i32':i32(typ+0x598),'plus598_u32':u32(typ+0x598),
                   'plus5a0':hex(i32(typ+0x5a0)&0xffffffff)}

    # logistics+8: first qword is array of pointers indexed by mode
    logi8=None
    mode_objs=[]
    if looks(logi):
        arr=q(logi+8)
        logi8={'logistics':hex(logi),'class':cls(logi),'plus8':hex(arr),'plus8_class':cls(arr),
               'plus20_is_country':q(logi+0x20)==country}
        if looks(arr):
            # read modes 0..8 pointers
            for mode in range(9):
                obj=q(arr+mode*8)
                rec={'mode':mode,'obj':hex(obj) if looks(obj) or obj==0 else obj,'class':cls(obj) if looks(obj) else None}
                if looks(obj):
                    inner=q(obj+0x10)
                    rec['plus10']=hex(inner) if looks(inner) else inner
                    rec['plus10_class']=cls(inner) if looks(inner) else None
                    if looks(inner):
                        pool=q(inner+0x30)
                        rec['plus10_plus30']=hex(pool) if looks(pool) else pool
                        rec['plus10_plus30_class']=cls(pool) if looks(pool) else None
                        if looks(pool):
                            # dense array? [pool]=base, [pool+0xc]=count as in 15b3220
                            rec['dense_base']=hex(q(pool)) if looks(q(pool)) else q(pool)
                            rec['dense_plus8']=i32(pool+8)
                            rec['dense_plusc']=i32(pool+0xc)
                            # if type+0x598 looks like an index, read that slot
                            if type_info and 0<=type_info['plus598_i32']<4096 and looks(q(pool)):
                                idx=type_info['plus598_i32']
                                rec['slot_598']={'index':idx,'raw':i64(q(pool)+idx*8)}
                                raw=rec['slot_598']['raw']
                                rec['slot_598']['as_amount']=raw//100000 if raw%100000==0 else None
                mode_objs.append(rec)

    produced=need=None
    if looks(request):
        produced=pool_amounts(request+0x38, 16, 8)
        need=pool_amounts(request+0x78, 16, 8)

    out={
        'pid':p.pid,'read_only':True,'no_game_method_execution':True,
        'hour_tick':hour_tick,'date':fields.get('date_full'),
        'speed_index':fields.get('game_speed_index'),'speed_notch':fields.get('game_speed_notch'),
        'tag':player.get('tag'),'player_index':player.get('player_index'),
        'army_1835':hex(army) if army else None,
        'CProductionStatus':hex(prod),'CProductionStatus_class':cls(prod),
        'CLogisticsStatus':hex(logi),'infantry_type':type_info,
        'stock_production_plus200':stock,
        'logistics':logi8,'mode_objects':mode_objs,
        'CArmyRequests':hex(reqs) if looks(reqs) else reqs,
        'request':hex(request) if looks(request) else request,
        'produced':produced,'need':need,
    }
    Path('research/t174_alloc_and_stock_live.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    # compact print
    compact={
        'pid':p.pid,'hour_tick':hour_tick,'in_game':True,'speed_notch':fields.get('game_speed_notch'),
        'type_name':type_info['name'] if type_info else None,
        'type_plus598':type_info['plus598_i32'] if type_info else None,
        'stock_rows':stock['rows'] if stock else None,
        'produced':produced['rows'] if produced else None,
        'need':need['rows'] if need else None,
        'modes':[{k:m.get(k) for k in ('mode','class','plus10_plus30_class','slot_598')} for m in mode_objs],
    }
    print(json.dumps(compact,ensure_ascii=False,indent=2))
finally:
    if p is not None: p.close()
