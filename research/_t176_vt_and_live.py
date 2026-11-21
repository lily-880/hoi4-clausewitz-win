
import os,sys,struct,json
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from pe import PE
from mem import Proc,find_pid
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country,read_campaign_summary

IMAGE=0x140000000
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')

def find_pref(rva):
    needle=struct.pack('<Q', IMAGE+rva)
    hits=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        start=0
        while True:
            j=blob.find(needle,start)
            if j<0: break
            if j%8==0:
                hits.append({'section':s.name,'rva':hex(s.virtual_address+j),'slot_index':None})
            start=j+8
    return hits

# dump known vtables and search 15a8f00 / 15a8cf0
known={
    'CReinforcementRequest':0x2a4b768,
    'CReinforcementRequest_sec':0x2a4b7a0,
    'CArmyReinforcementRequests':0x2a4b7f0,
    'CReinforcementStatus':0x2a4b878,
}
# also read 16 slots from each
def dump_vt(rva, n=16):
    raw=pe.read_rva(rva, n*8) or b''
    slots=[]
    for i in range(n):
        if i*8+8>len(raw): break
        val=struct.unpack_from('<Q',raw,i*8)[0]
        fn=val-IMAGE if val>=IMAGE else val
        slots.append({'i':i,'off':hex(i*8),'ptr':hex(val),'rva':hex(fn) if 0<fn<0x4000000 else hex(val)})
    return slots

out={'vtables':{k:dump_vt(v) for k,v in known.items()},
     'pref_15a8f00':find_pref(0x15a8f00),
     'pref_15a8cf0':find_pref(0x15a8cf0),
     'pref_15a93d0':find_pref(0x15a93d0)}
# for each pref hit, dump surrounding vtable (look back up to 8 slots)
def around(hit_rva, back=8, fwd=8):
    base=int(hit_rva,16)
    start=base-back*8
    raw=pe.read_rva(start, (back+fwd+1)*8) or b''
    slots=[]
    for i in range((back+fwd+1)):
        val=struct.unpack_from('<Q',raw,i*8)[0]
        fn=val-IMAGE if val>=IMAGE else 0
        slots.append({'off':hex(start+i*8),'rva':hex(fn) if 0<fn<0x4000000 else hex(val),
                      'is_hit':(start+i*8)==base})
    return slots
out['around_15a8f00']=[around(h['rva']) for h in out['pref_15a8f00']]
out['around_15a8cf0']=[around(h['rva']) for h in out['pref_15a8cf0']]

# RTTI names for vtable starts: a vtable usually is preceded by col-ptr at vt-8
def rtti_at_vt(vt_rva):
    try:
        n=_rtti_name_from_vtable(pe, vt_rva)
        return n
    except Exception as e:
        return str(e)

# guess vtable start for 15a8f00 hits: walk back while slots look like code ptrs, stop at RTTI
def guess_vt_start(hit_rva, maxback=32):
    base=int(hit_rva,16)
    for back in range(0,maxback+1):
        cand=base-back*8
        name=rtti_at_vt(cand)
        if name and isinstance(name,str) and name.startswith('.?AV'):
            return {'vt':hex(cand),'slot':back,'name':name}
    return {'vt':None,'name':None,'slot':None}

out['15a8f00_classes']=[guess_vt_start(h['rva']) for h in out['pref_15a8f00']]
out['15a8cf0_classes']=[guess_vt_start(h['rva']) for h in out['pref_15a8cf0']]
out['status_rtti']=rtti_at_vt(0x2a4b878)

# LIVE
P=None
live={'read_only':True,'no_game_method_execution':True}
try:
    P=Proc(find_pid('hoi4.exe'))
    live['pid']=P.pid
    def u64(a):
        b=P.try_read(a,8)
        return struct.unpack('<Q',b)[0] if b and len(b)==8 else None
    def i64(a):
        b=P.try_read(a,8)
        return struct.unpack('<q',b)[0] if b and len(b)==8 else None
    def u32(a):
        b=P.try_read(a,4)
        return struct.unpack('<I',b)[0] if b and len(b)==4 else None
    def cls(a):
        if not a or not (0x10000<a<0x7fffffffffff): return None
        vt=u64(a)
        if not vt or not (P.base<=vt<P.base+P.image_size): return None
        try:
            n=_rtti_name_from_vtable(pe, vt-P.base)
            return n
        except Exception:
            return None
    def cname(n):
        if not n: return None
        # .?AVCEquipmentType@@
        if n.startswith('.?AV') and n.endswith('@@'):
            return n[4:-2]
        return n
    typ=0x26bc2d15050
    live['infantry_type']={'ptr':hex(typ),'class':cname(cls(typ))}
    p3f0=u64(typ+0x3f0)
    live['type_plus3f0']={'ptr':hex(p3f0) if p3f0 else None,'class':cname(cls(p3f0)) if p3f0 else None,
                          'same_as_type':p3f0==typ}
    def is_air_eval(obj):
        if not obj: return None
        seen=set(); cur=obj
        for _ in range(8):
            if cur in seen: break
            seen.add(cur)
            parent=u64(cur+0x538)
            if parent==cur or not parent:
                break
            cur=parent
        a=u64(cur+0x5a0) or 0
        b=u64(cur+0x5a8) or 0
        if a==0:
            p=u64(cur+0x538)
            if p: a=u64(p+0x5a0) or 0
        bits=a|b
        # 100f620 cleanup
        MASK_TEST=0x80004003c1
        rcx=bits
        if rcx & MASK_TEST:
            if rcx & 0x40:
                rcx = rcx & 0xfffffffffffffe7e
            elif (rcx & 0x80):  # jns is sign of dl (bit 7)
                rcx = rcx & 0xfffffffffffffefe
            else:
                rax=rcx & 0xfffffffffffffffe
                if rcx & 0x100:
                    rcx=rax
        air_mask=0x1f0037fc00
        return {'obj':hex(cur),'class':cname(cls(cur)),'raw_5a0':hex(a),'raw_5a8':hex(b),
                'or_bits':hex(a|b),'cleaned':hex(rcx),'is_air':bool(rcx & air_mask)}
    live['is_air_on_type']=is_air_eval(typ)
    live['is_air_on_plus3f0']=is_air_eval(p3f0) if p3f0 else None
    # also dump type 0x5a0/0x5a8/0x408/0x410/0x42c
    live['type_flags']={
        'plus408':hex(u64(typ+0x408) or 0),
        'plus410_u32':u32(typ+0x410),
        'plus42c_u32':u32(typ+0x42c),
        'plus5a0':hex(u64(typ+0x5a0) or 0),
        'plus5a8':hex(u64(typ+0x5a8) or 0),
        'plus598':u32(typ+0x598),
    }
    # status + country +8 handle for 717410
    status=0x26c49c0c140
    country=0x26c4b672530
    live['status_plus38']=hex(u64(status+0x38) or 0)
    live['country_plus8']=u32(country+8)
    live['country_plus8_u64']=hex(u64(country+8) or 0)
    live['country_plus_f78']=hex(u64(country+0xf78) or 0)
    live['status_is_f78']=u64(country+0xf78)==status
    live['request_need_produced']={}
    req=0x26cb1969530
    # need at +0x78 is a pool; produced at +0x38
    live['request']={'ptr':hex(req),'class':cname(cls(req)),
                     'plus38':hex(u64(req+0x38) or 0),'plus38_class':cname(cls(u64(req+0x38))) if u64(req+0x38) else None}
finally:
    if P: P.close()

Path('research/t176_vtables_and_isair.json').write_text(json.dumps({'static':out,'live':live},indent=2,default=str),encoding='utf-8')
print(json.dumps({'static_15a8f00':out['pref_15a8f00'],'classes_15a8f00':out['15a8f00_classes'],
                  'static_15a8cf0':out['pref_15a8cf0'],'classes_15a8cf0':out['15a8cf0_classes'],
                  'status_slots':out['vtables']['CReinforcementStatus'],
                  'live':live},indent=2))
