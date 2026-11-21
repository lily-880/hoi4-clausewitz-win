"""t179 live: logistics 77 peek + province neighbor structure dump. Read-only."""
from __future__ import annotations
import os, sys, json, struct
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, _pdx_array
import offsets as O

FIXED=100000
CO_ARMIES=O.HYPOTHESIS_STRUCT['CO_ARMIES']  # 656
CA_PROVINCE=O.HYPOTHESIS_STRUCT['CA_PROVINCE']  # 496

def demangle(n):
    if not n: return None
    if n.startswith('.?A') and n.endswith('@@'):
        return n[4:-2].split('@')[0]
    return n

def cls(pe,P,addr):
    if not addr or not (0x10000 < addr < 0x7fffffffffff):
        return None
    try:
        vt=P.u64(addr)
    except Exception:
        return None
    if not (P.base <= vt < P.base+P.image_size):
        return None
    try:
        return demangle(_rtti_name_from_vtable(pe, vt-P.base))
    except Exception:
        return None

def i32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<i',b)[0] if b and len(b)==4 else None

def u32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None

def u64(P,a):
    b=P.try_read(a,8)
    return struct.unpack('<Q',b)[0] if b and len(b)==8 else None

def main():
    pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
    P=Proc(find_pid('hoi4.exe'))
    try:
        session=detect_session(P,pe)
        gs=int(session['signals']['gs_ptr'],16)
        country=resolve_player_country(P,gs)
        cp=int(country['country_ptr'],16) if isinstance(country['country_ptr'],str) else country['country_ptr']
        out={'pid':P.pid,'tag':country['tag'],'index':country['player_index'],'read_only':True}

        # logistics peek: CLogisticsStatus, look at arrays and values 77 / 7700000
        logi=P.u64(cp+0xf98)
        logi_hits=[]
        blob=P.try_read(logi,0x2000) or b''
        for off in range(0,len(blob)-7,8):
            v=struct.unpack_from('<q',blob,off)[0]
            if v in (77,-77,77*FIXED,-77*FIXED,80*FIXED,3*FIXED,2520*FIXED,2520,80,-80):
                logi_hits.append({'off':hex(off),'i64':v})
        # also inspect pointers with class and any pdx arrays
        logi_ptrs=[]
        for off in range(0,min(len(blob),0x400)-7,8):
            v=struct.unpack_from('<Q',blob,off)[0]
            n=cls(pe,P,v)
            if n and 'Allocator' not in n:
                logi_ptrs.append({'off':hex(off),'ptr':hex(v),'class':n})
        out['logistics']={'ptr':hex(logi),'class':cls(pe,P,logi),'hits_77ish':logi_hits,'typed_ptrs':logi_ptrs}

        # own divisions and unique provinces
        armies=_pdx_array(P, cp+CO_ARMIES)
        units=[]
        provs={}
        size=armies['size'] if armies else 0
        data=armies['data'] if armies else 0
        for i in range(min(size,64)):
            ap=P.u64(data+8*i)
            if not ap: continue
            if cls(pe,P,ap)!='CArmy':
                continue
            uid=i32(P, ap+0x10)  # may be wrong; try common id offsets later if needed
            # unit_id: look at several; previous work used a known field
            pp=P.u64(ap+CA_PROVINCE)
            pid=u32(P, pp+0xa4) if pp else None
            rec={'army':hex(ap),'unit_id_plus10':uid,'province':hex(pp) if pp else None,'province_id':pid,'pclass':cls(pe,P,pp) if pp else None}
            units.append(rec)
            if pp and pid and pid not in provs:
                provs[pid]=pp
        out['army_array']={'off':CO_ARMIES,'size':size,'cap':armies.get('capacity') if armies else None}
        out['unit_count']=len(units)
        out['unique_provinces']=len(provs)

        def dump_prov(pid,pp):
            d={'province_id':pid,'ptr':hex(pp),'class':cls(pe,P,pp)}
            d['i32']={hex(off): i32(P,pp+off) for off in (0x54,0x58,0x5c,0xa0,0xa4,0xa8,0xbc,0xc8,0xcc,0x134,0x11c)}
            d['ptrs']={}
            for off in (0x30,0x48,0xb0,0xb8,0xc0,0xc8,0xd0):
                v=u64(P,pp+off)
                d['ptrs'][hex(off)]={'ptr':hex(v) if v else None,'class':cls(pe,P,v)}
            # if +0x30 looks like definition with +0x110/+0x11c
            p30=u64(P,pp+0x30)
            if p30:
                cnt=i32(P,p30+0x11c)
                arr=u64(P,p30+0x110)
                ids=[]
                if cnt is not None and 0<=cnt<=256 and arr and arr>0x10000:
                    raw=P.try_read(arr, cnt*4) or b''
                    ids=list(struct.unpack_from('<'+'i'*(len(raw)//4), raw))
                d['def30']={'ptr':hex(p30),'class':cls(pe,P,p30),'count_11c':cnt,'arr_110':hex(arr) if arr else None,'ids':ids,
                            'id_58':i32(P,p30+0x58),'id_a4':u32(P,p30+0xa4)}
            # +0xb8 data pointer as t156
            p_b8=u64(P,pp+0xb8)
            if p_b8:
                d['b8']={'ptr':hex(p_b8),'class':cls(pe,P,p_b8)}
                for hdr in (0x70,0xb0,0x110):
                    try:
                        ar=_pdx_array(P, p_b8+hdr)
                    except Exception:
                        ar=None
                    if ar and isinstance(ar.get('size'),int) and 0<=ar['size']<=256:
                        d['b8'][hex(hdr)]={'size':ar['size'],'cap':ar.get('capacity'),'data':hex(ar['data']) if ar.get('data') else None}
            # +0xb0 pointer array, count +0xbc (db76e0 on some object)
            cnt=i32(P,pp+0xbc)
            arr=u64(P,pp+0xb0)
            neigh=[]
            if cnt is not None and 0<=cnt<=256 and arr and arr>0x10000:
                raw=P.try_read(arr, cnt*8) or b''
                for i in range(len(raw)//8):
                    q=struct.unpack_from('<Q',raw,i*8)[0]
                    nid=i32(P,q+0x58) if q else None
                    nid_a4=u32(P,q+0xa4) if q else None
                    neigh.append({'ptr':hex(q) if q else None,'class':cls(pe,P,q),'id_58':nid,'id_a4':nid_a4})
            d['b0_bc']={'count':cnt,'arr':hex(arr) if arr else None,'elems':neigh}
            return d

        dumps=[dump_prov(pid,pp) for pid,pp in sorted(provs.items())]
        out['provinces']=dumps
        Path('research/t179_province_neighbor_live.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
        # brief
        print('units',len(units),'provinces',len(provs),'logi_hits',logi_hits,'logi_ptrs',logi_ptrs[:8])
        for d in dumps:
            print('PID',d['province_id'],'class',d['class'],
                  'id58',d['i32'].get('0x58'),'id_a4',d['i32'].get('0xa4'),
                  'def30', {k:d.get('def30',{}).get(k) for k in ('class','count_11c','ids')} if d.get('def30') else None,
                  'b0_bc count', d['b0_bc']['count'], 'ids58',[e['id_58'] for e in d['b0_bc']['elems'][:12]],
                  'b8', d.get('b8'))
    finally:
        P.close()

if __name__=='__main__':
    main()
