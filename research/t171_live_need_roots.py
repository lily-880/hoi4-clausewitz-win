
"""Read-only live inspect of 1409890 roots, F70 array, 11f8 list, and short callees.

No Post, no write, no speed/campaign change, no heap sweep, no method execution.
Foreign object class names may be recorded for structure only; no fog-hidden
operational amounts or locations are emitted.
"""
from __future__ import annotations
import os, sys, json, struct, hashlib, bisect
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable, detect_session, resolve_player_country, read_campaign_summary
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from input_loaded_fields import LoadedReader, ObservationError

HERE=Path(__file__).resolve().parent
profile=json.loads((HERE.parent/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'))

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest().upper()

def disasm_from(pe, cs, start, max_bytes=0x200):
    raw=pe.read_rva(start, max_bytes) or b''
    out=[]
    for i in cs.disasm(raw, start):
        rec={'rva':hex(i.address),'asm':(i.mnemonic+' '+i.op_str).strip()}
        out.append(rec)
        if i.mnemonic=='ret':
            break
    return out

def looks_ptr(x):
    return type(x) is int and 0x10000<x<0x7fffffffffff

def typenames(s):
    if not s: return s
    if s.startswith('.?AV') and s.endswith('@@'):
        return s[4:-2]
    if s.startswith('.?AU') and s.endswith('@@'):
        return s[4:-2]
    return s

p=None
try:
    p=Proc(find_pid('hoi4.exe'))
    digest=sha256_file(p.image_path)
    if digest!=profile['exe_sha256']:
        raise SystemExit('fingerprint mismatch')
    if p.pid!=26976:
        # still continue if in-game same build, but record
        pass
    pe=PE(p.image_path)
    session=detect_session(p, pe)
    if not (session.get('in_game') and session.get('session')=='in_game'):
        Path(HERE/'t171_live_need_roots.json').write_text(json.dumps({'stop':'not in game','session':session},indent=2),encoding='utf-8')
        print('STOP not in game')
        raise SystemExit(0)
    gs=int(session['signals']['gs_ptr'],16)
    fields=read_campaign_summary(p,gs)['fields']
    if fields.get('game_speed_notch') not in (1,None) and fields.get('game_speed_index') not in (0,None):
        print('SPEED not 1x, not changing', fields.get('game_speed_notch'))
    player=resolve_player_country(p,gs)
    country=int(player['country_ptr'],16) if isinstance(player['country_ptr'],str) else player['country_ptr']
    cs=Cs(CS_ARCH_X86, CS_MODE_64)
    callees={}
    for t in [0x2574ba0,0x717400,0xb2cb40,0xd498a0,0xd49890,0x31f8b0,0xcf4fe0,0xcf5620,0xcf5660,0xcf2e50,0x7362c0]:
        callees[hex(t)]=disasm_from(pe,cs,t,0x180)

    def q(a): return struct.unpack('<Q', p.read(a,8))[0]
    def i32(a): return struct.unpack('<i', p.read(a,4))[0]
    def u32(a): return struct.unpack('<I', p.read(a,4))[0]
    def cls(a):
        if not looks_ptr(a): return None
        try:
            vt=q(a)
        except OSError:
            return None
        if not (p.base<=vt<p.base+p.image_size): return None
        return _rtti_name_from_vtable(pe, vt-p.base)

    def string(a):
        try:
            blob=p.read(a,32)
        except OSError:
            return None
        size,cap=struct.unpack_from('<QQ',blob,16)
        if not 0<=size<=256 or cap<size: return None
        data=blob[:size] if cap<=15 else p.try_read(struct.unpack_from('<Q',blob)[0], size)
        if data is None: return None
        try:
            return data.decode('utf-8')
        except Exception:
            return None

    def array_header(a):
        try:
            data,cap,size=struct.unpack('<QII', p.read(a,16))
        except OSError:
            return None
        return {'data':hex(data) if looks_ptr(data) or data==0 else data,'data_raw':data,'capacity':cap,'size':size}

    def typed_amounts(pool, expected, stride, amount_off, limit=16):
        c=cls(pool)
        if typenames(c)!=expected:
            return {'class':c,'error':'unexpected pool class'}
        hdr=array_header(pool+8)
        if not hdr or hdr['size']<0 or hdr['size']>64:
            return {'class':c,'header':hdr,'error':'bad type array'}
        rows=[]
        data=hdr['data_raw']
        for j in range(min(hdr['size'],limit)):
            tp=q(data+j*stride) if stride else None
            # actually type array at pool+8 is {ptr, begin_i32, count} for variant 24 or archetype 16
            # wait, existing collector uses r.array(pool+8,64,stride) which is pointers?
            pass
        # Use same layout as input_loaded_fields._typed_equipment_amounts
        # types = array of type ptrs? Looking at the function:
        # types=r.array(pool+8,64,stride); data=r.q(pool+8)
        # for j,tp in enumerate(types): amount at data+j*stride+amount_off
        # I need LoadedReader.array or reimplement: ptr, cap?, count at pool+8
        begin=q(pool+8)
        # size at +0x10 / +0xc? Fixture packed <QII begin,1,1 so +8 ptr, +16 cap, +20 count? 
        # pack(obj+8,'<QII',base,1,1) is ptr + two u32 = cap and size at +16 and +20.
        # But official comments said begin i32, count i32 at some places...
        # The live collector already works with this. Use cap/size at +16/+20.
        cap,n=struct.unpack_from('<II', p.read(pool+8,16), 8)
        # wait pack is <QII at obj+8: offset 0 ptr, 8 cap u32, 12 size u32 relative to obj+8, i.e. +16 and +20.
        cap,n=struct.unpack('<II', p.read(pool+16,8))
        if n<0 or n>64: return {'class':c,'error':'bad count','n':n,'cap':cap}
        rows=[]
        for j in range(n):
            rec=p.read(begin+j*stride, stride)
            tp=struct.unpack_from('<Q',rec,0)[0]
            raw=struct.unpack_from('<q',rec,amount_off)[0]
            nm=string(tp+0x18) if cls(tp) and 'CEquipmentType' in (cls(tp) or '') else None
            item={'equipment_type':nm,'amount_raw':raw}
            if raw%100000==0:
                item['amount']=raw//100000
            rows.append(item)
        return {'class':c,'count':n,'rows':rows}

    # Deployment status
    dep=q(country+0xf70)
    dep_cls=cls(dep)
    dep_scan={}
    for off in range(0,0x80,8):
        v=q(dep+off)
        item={'off':hex(off),'u64':hex(v)}
        c=cls(v)
        if c: item['class']=c
        if 0<=off<=0x40:
            try:
                item['as_array']=array_header(dep+off)
            except Exception:
                pass
        dep_scan[hex(off)]=item

    # Candidate arrays: +0x20 as previously noted
    def list_ptrs(header, bound=256):
        if not header or header['size']<0 or header['size']>bound or not looks_ptr(header['data_raw']):
            return [], header
        n=min(header['size'], bound)
        return [q(header['data_raw']+i*8) for i in range(n)], header

    f70_arr,f70_hdr=list_ptrs(array_header(dep+0x20), 256)
    # classify own vs other by owner if CArmy-like
    def owner_of(obj):
        # CArmy owner often at +0x18 or nearby; t170 used army in own list
        for off in (0x18,0x14,0x1c,0x20,0x24,0x28,0x10,0x30,0x34,0x38,0x40):
            try:
                val=i32(obj+off)
            except OSError:
                continue
            if val==player['player_index']:
                return {'off':hex(off),'value':val}
        return None

    def unit_id_of(obj):
        # CArmy unit id at +0x1c proven
        try:
            uid=i32(obj+0x1c)
        except OSError:
            return None
        return uid

    # Own armies
    army_hdr=array_header(country+0x290)
    army_ptrs,_=list_ptrs(army_hdr, 256)
    own_armies={}
    for ap in army_ptrs:
        if typenames(cls(ap))!='CArmy':
            continue
        uid=i32(ap+0x1c)
        own_armies[ap]={'unit_id':uid,'ptr':hex(ap)}

    f70_classes={}
    f70_own_detail=[]
    f70_foreign_class_counts={}
    f70_own_count=0
    f70_other_count=0
    f70_untyped=0
    for ep in f70_arr:
        c=typenames(cls(ep)) or 'null'
        f70_classes[c]=f70_classes.get(c,0)+1
        if not looks_ptr(ep):
            f70_untyped+=1
            continue
        in_own=ep in own_armies
        own_flag=in_own
        # also owner field if present
        uid=unit_id_of(ep) if c in ('CArmy','CDivision','CDeployedDivision') or True else None
        # For non-own objects: only count class, no amounts/locations/ids if not in own list
        if in_own or (uid is not None and any(v['unit_id']==uid for v in own_armies.values()) and owner_of(ep)):
            f70_own_count+=1
            rec={'ptr':hex(ep),'class':c,'unit_id':own_armies.get(ep,{}).get('unit_id', uid),'in_own_army_list':in_own}
            # equipment only for own
            # try d498a0-like and 31f8b0-like by following disasm after we have it
            f70_own_detail.append(rec)
        else:
            f70_other_count+=1
            f70_foreign_class_counts[c]=f70_foreign_class_counts.get(c,0)+1

    # country+0x11f8 for 14080c0
    obj11=q(country+0x11f8)
    info11={'ptr':hex(obj11),'class':cls(obj11)}
    # scan a few offsets around 0x758 / 0x764
    if looks_ptr(obj11):
        try:
            begin=q(obj11+0x758)
            count=i32(obj11+0x764)
            cap=i32(obj11+0x760) if True else None
            info11['array_758']={'begin':hex(begin) if looks_ptr(begin) or begin==0 else begin,'count':count,'cap_760':u32(obj11+0x760)}
            items=[]
            class_counts={}
            own_items=[]
            if 0<=count<=512 and looks_ptr(begin):
                for j in range(count):
                    ip=q(begin+j*8)
                    c=typenames(cls(ip)) or 'null'
                    class_counts[c]=class_counts.get(c,0)+1
                    if ip in own_armies:
                        rec={'ptr':hex(ip),'class':c,'unit_id':own_armies[ip]['unit_id'],'in_own_army_list':True}
                        # pools at +0x198 and +0x1d8
                        rec['pool_198']=typed_amounts(ip+0x198,'CEquipmentVariantPool',24,16) if False else {'class':cls(ip+0x198)}
                        rec['pool_1d8']={'class':cls(ip+0x1d8)}
                        # try typed if classes look like pools
                        for key,off,expect,stride,aoff in (
                            ('pool_198_amounts',0x198,'CEquipmentVariantPool',24,16),
                            ('pool_1d8_amounts',0x1d8,'CEquipmentVariantPool',24,16),
                        ):
                            cpool=typenames(cls(ip+off))
                            rec[key]=typed_amounts(ip+off, cpool or 'CEquipmentVariantPool', 24 if 'Variant' in (cpool or '') else 16, 16 if 'Variant' in (cpool or '') else 8)
                        own_items.append(rec)
            info11['class_counts']=class_counts
            info11['own_item_count']=len(own_items)
            info11['own_items']=own_items
        except OSError as e:
            info11['error']=str(e)

    # Reinforcement confirmation via 717400 target: live F78
    rs=q(country+0xf78)
    rs_info={'ptr':hex(rs),'class':cls(rs),'plus20':array_header(rs+0x20)}

    # Occupation / logistics / operations emptiness as scene fact
    others={}
    for name,off,arr_off in (('occupation',0xfd0,0x28),('logistics',0xf98,0x28),('operations',0x15a8,0x10)):
        o=q(country+off)
        others[name]={'ptr':hex(o),'class':cls(o),'array':array_header(o+arr_off)}

    out={
        'pid':p.pid,
        'player':{'index':player['player_index'],'tag':player.get('tag'),'country':hex(country)},
        'speed_notch':fields.get('game_speed_notch'),
        'date':fields.get('date_full'),
        'read_only':True,
        'callees_until_first_ret':callees,
        'deployment':{'ptr':hex(dep),'class':dep_cls,'scan':dep_scan,'array_20':f70_hdr,
                      'class_counts':f70_classes,'own_count':f70_own_count,'other_count':f70_other_count,
                      'own_items':f70_own_detail,'foreign_class_counts_only':f70_foreign_class_counts},
        'own_army_count':len(own_armies),
        'country_11f8':info11,
        'reinforcement_status':rs_info,
        'other_roots_scene':others,
    }
    Path(HERE/'t171_live_need_roots.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    # compact print
    compact={
        'pid':p.pid,'tag':player.get('tag'),'speed':fields.get('game_speed_notch'),
        'dep_class':dep_cls,'f70_hdr':f70_hdr,'f70_classes':f70_classes,
        'f70_own':f70_own_count,'f70_other':f70_other_count,
        'f70_own_unit_ids':[x.get('unit_id') for x in f70_own_detail],
        'rs':rs_info,'c11f8_class':info11.get('class'),'c11f8_array':info11.get('array_758'),
        'c11f8_classes':info11.get('class_counts'),'c11f8_own':info11.get('own_item_count'),
        'others':others,
        'callee_summaries':{k: v[:12]+(['...'] if len(v)>12 else []) for k,v in callees.items()},
    }
    print(json.dumps(compact,ensure_ascii=False,indent=2))
finally:
    if p is not None:
        p.close()
