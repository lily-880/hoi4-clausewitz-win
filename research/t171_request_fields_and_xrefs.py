
"""Read-only: named request fields, infantry type gates, vtable xrefs, unit contrasts."""
from __future__ import annotations
import os, sys, json, struct, hashlib, collections
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
    cs=Cs(CS_ARCH_X86, CS_MODE_64)

    def q(a): return struct.unpack('<Q', p.read(a,8))[0]
    def i32(a): return struct.unpack('<i', p.read(a,4))[0]
    def i64(a): return struct.unpack('<q', p.read(a,8))[0]
    def u8(a): return p.read(a,1)[0]
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

    # live request + named fields (serializer 15AB830, this = request+18)
    rs=q(country+0xf78)
    rh=arr(rs+0x20)
    requests=[]
    vt_rvas=set()
    for j in range(rh['size'] if 0<=rh['size']<=64 and looks_ptr(rh['data']) else 0):
        gp=q(rh['data']+j*8)
        army=q(gp+0x20)
        eh=arr(gp+0x28)
        for k in range(eh['size'] if 0<=eh['size']<=256 and looks_ptr(eh['data']) else 0):
            ep=q(eh['data']+k*8)
            vt=q(ep)
            rva=vt-p.base
            vt_rvas.add(rva)
            rec={
                'request':hex(ep),'class':cname(ep),'vtable_rva':hex(rva),
                'group':hex(gp),'unit_id':i32(army+0x1c) if cname(army)=='CArmy' else None,
                'status_u32_plus20':i32(ep+0x20),
                'progress_plus28':i64(ep+0x28),
                'total_progress_plus30':i64(ep+0x30),
                'date_plus_a8_raw':p.read(ep+0xa8,16).hex(),
                'date_plus_a8_i32s':[i32(ep+0xa8+i) for i in range(0,16,4)],
                'date_plus_a8_q':[hex(q(ep+0xa8)), hex(q(ep+0xb0))],
                'date_class':cname(ep+0xa8),
            }
            # date might be a CDate-like 32-bit hour tick or year/month
            requests.append(rec)

    # infantry type flags from own unit pool
    army_h=arr(country+0x290)
    type_info=None
    unit_rows=[]
    focus_ids=set()
    for j in range(army_h['size'] if 0<=army_h['size']<=256 and looks_ptr(army_h['data']) else 0):
        ap=q(army_h['data']+j*8)
        if cname(ap)!='CArmy':
            continue
        uid=i32(ap+0x1c)
        # current pool types
        begin,cap,n=struct.unpack('<QII', p.read(ap+0x348+8,16))
        typ=None
        if 0<n<=16 and looks_ptr(begin):
            typ=q(begin)  # first type ptr in variant row
            if cname(typ)=='CEquipmentType' and type_info is None:
                name=string(typ+0x18)
                type_info={
                    'ptr':hex(typ),'name':name,
                    'byte_44b_cf5660':u8(typ+0x44b),
                    'byte_5b5_assert':u8(typ+0x5b5),
                    'q_5a0':hex(q(typ+0x5a0)),
                    'q_5a8':hex(q(typ+0x5a8)),
                    'q_538_parent':hex(q(typ+0x538)),
                    'parent_class':cname(q(typ+0x538)),
                }
        # bounded field snapshot for contrast: first 0x3c0 as i32 where useful, plus known ptrs
        snapshot={}
        for off in range(0,0x3c0,4):
            snapshot[hex(off)]=i32(ap+off)
        ptrs={}
        for off in (0x20,0x28,0x30,0x38,0x40,0x48,0x50,0x58,0x60,0x68,0x70,0x78,0x80,0x88,0x90,0x98,0xa0,0xa8,0xb0,0xb8,0xc0,0xc8,0xd0,0xd8,0xe0,0x200,0x208,0x210,0x300,0x308,0x310,0x318,0x320,0x328,0x330,0x338,0x340,0x3b0,0x3b8):
            v=q(ap+off)
            ptrs[hex(off)]={'ptr':hex(v) if looks_ptr(v) else hex(v),'class':cname(v)}
        unit_rows.append({'unit_id':uid,'ptr':hex(ap),'i32':snapshot,'ptrs':ptrs})

    # Contrast 1835 against other short units with same 80 deficit (1830 etc.) and a full unit
    by_id={u['unit_id']:u for u in unit_rows}
    base=by_id.get(1835)
    contrasts=[]
    if base:
        for uid in [1829,1830,1833,1834,1836,1840,1842,1843]:
            if uid not in by_id: continue
            other=by_id[uid]
            i32_diff={k:{'1835':base['i32'][k],'other':other['i32'][k]} for k in base['i32'] if base['i32'][k]!=other['i32'][k]}
            # drop obvious identity / pointer-identity fields later in report by filtering huge unique values? keep all but count
            ptr_diff={k:{'1835':base['ptrs'].get(k),'other':other['ptrs'].get(k)} for k in set(base['ptrs'])|set(other['ptrs']) if base['ptrs'].get(k)!=other['ptrs'].get(k)}
            contrasts.append({'other_unit_id':uid,'i32_diff_count':len(i32_diff),'ptr_diff_count':len(ptr_diff),
                              'i32_diff_small':{k:v for k,v in i32_diff.items() if all(abs(x)<10_000_000 for x in v.values())},
                              'ptr_class_diff':{k:v for k,v in ptr_diff.items() if ((v['1835'] or {}).get('class')!=(v['other'] or {}).get('class')) or (v['1835'] or {}).get('class')}})

    # Static RIP-relative refs to request / group vtables
    text=next(s for s in pe.sections if s.name=='.text')
    raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
    def rip_refs(target_rva, limit=40):
        hits=[]
        i=0
        # scan lea/mov rip-rel: 48/4c 8d xx, or 48 8b xx with modrm rip
        while i < len(raw)-7 and len(hits)<limit:
            # skip to 8D or 8B with rex
            if raw[i] in (0x48,0x4C,0x4D,0x49) and raw[i+1] in (0x8D,0x8B) and (raw[i+2] & 0xC7)==0x05:
                rel=struct.unpack_from('<i', raw, i+3)[0]
                inst_rva=text.virtual_address+i
                disp_end=inst_rva+7
                dest=disp_end+rel
                if dest==target_rva:
                    hits.append(hex(inst_rva))
                i+=7
                continue
            i+=1
        return hits

    xref={}
    for rva in sorted(vt_rvas):
        xref[hex(rva)]={'vtable_rva':hex(rva),'rip_refs':rip_refs(rva, 50)}
    # also group vtable
    if looks_ptr(rh['data']):
        gp=q(rh['data'])
        gvt=q(gp)-p.base
        xref['group_'+hex(gvt)]={'vtable_rva':hex(gvt),'rip_refs':rip_refs(gvt, 50)}

    # disasm functions around unique request-vtable refs (constructors usually early in func)
    def funcish(addr, before=32, after=80):
        rawb=pe.read_rva(max(addr-before,0), before+after) or b''
        out=[]
        for ins in cs.disasm(rawb, max(addr-before,0)):
            out.append({'rva':hex(ins.address),'asm':(ins.mnemonic+' '+ins.op_str).strip()})
        return out

    xref_windows={}
    for key,info in xref.items():
        xref_windows[key]=[{'at':h,'window':funcish(int(h,16), 48, 96)} for h in info['rip_refs'][:12]]

    # Bounded search for 77*100000 inside known status objects only (not heap sweep)
    needle=struct.pack('<q', 77*100000)
    needle80=struct.pack('<q', 80*100000)
    bounded_hits={'77':[],'80':[]}
    regions=[]
    def add_region(name, start, size):
        if looks_ptr(start) and 0<size<=0x4000:
            regions.append((name,start,size))
    add_region('CReinforcementStatus', rs, 0x200)
    add_region('CDeploymentStatus', q(country+0xf70), 0x200)
    add_region('CLogisticsStatus', q(country+0xf98), 0x200)
    add_region('CCountryOccupationStatus', q(country+0xfd0), 0x200)
    add_region('CCountryOperationManager', q(country+0x15a8), 0x200)
    add_region('CProductionStatus', q(country+0xf68), 0x400)
    add_region('CCountryResources', q(country+0x11f8), 0x800)
    add_region('country_window', country, 0x2000)
    for j in range(rh['size'] if 0<=rh['size']<=4 and looks_ptr(rh['data']) else 0):
        gp=q(rh['data']+j*8)
        add_region('group', gp, 0x80)
        eh=arr(gp+0x28)
        for k in range(eh['size'] if 0<=eh['size']<=8 and looks_ptr(eh['data']) else 0):
            add_region('request', q(eh['data']+k*8), 0x100)
    for name,start,size in regions:
        blob=p.try_read(start,size)
        if not blob: continue
        for label,nd in (('77',needle),('80',needle80)):
            off=0
            while True:
                i=blob.find(nd, off)
                if i<0: break
                bounded_hits[label].append({'region':name,'offset':hex(i),'addr':hex(start+i)})
                off=i+1

    out={
        'pid':p.pid,'tag':player.get('tag'),'speed_notch':fields.get('game_speed_notch'),
        'read_only':True,
        'named_request_fields':requests,
        'infantry_type_gates':type_info,
        'vtable_xrefs':xref,
        'xref_windows':xref_windows,
        'contrasts_vs_1835':contrasts,
        'bounded_need_value_hits':bounded_hits,
    }
    Path(HERE/'t171_request_fields_and_xrefs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({
        'named_request_fields':requests,
        'infantry_type_gates':type_info,
        'vtable_xrefs':xref,
        'xref_count':{k:len(v['rip_refs']) for k,v in xref.items()},
        'contrast_summary':[{'other':c['other_unit_id'],'i32_small':c['i32_diff_small'],'ptr_class':{k:v for k,v in c['ptr_class_diff'].items() if (v['1835'] or {}).get('class') or (v['other'] or {}).get('class')}} for c in contrasts],
        'bounded_hits':bounded_hits,
    },ensure_ascii=False,indent=2))
finally:
    if p is not None:
        p.close()
