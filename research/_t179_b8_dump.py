"""Dump CProvince+0xb8+0x70 array raw; never P.read unverified addrs."""
from __future__ import annotations
import os,sys,json,struct
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,_pdx_array
import offsets as O

def demangle(n):
    if not n: return None
    if n.startswith('.?A') and n.endswith('@@'):
        return n[4:-2].split('@')[0]
    return n
def cls(pe,P,addr):
    if not addr or not (0x10000000000 < addr < 0x7fffffffffff): return None
    b=P.try_read(addr,8)
    if not b or len(b)<8: return None
    vt=struct.unpack_from('<Q',b)[0]
    if not (P.base<=vt<P.base+P.image_size): return None
    try: return demangle(_rtti_name_from_vtable(pe,vt-P.base))
    except Exception: return None
def try_u32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None

pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
P=Proc(find_pid('hoi4.exe'))
try:
    session=detect_session(P,pe)
    gs=int(session['signals']['gs_ptr'],16)
    country=resolve_player_country(P,gs)
    cp=int(country['country_ptr'],16)
    armies=_pdx_array(P,cp+O.HYPOTHESIS_STRUCT['CO_ARMIES'])
    provs={}
    for i in range(min(armies['size'],64)):
        ap=P.u64(armies['data']+8*i)
        if cls(pe,P,ap)!='CArmy': continue
        pp=P.u64(ap+O.HYPOTHESIS_STRUCT['CA_PROVINCE'])
        if not pp: continue
        b=P.try_read(pp+0xa4,4)
        if not b: continue
        pid=struct.unpack('<I',b)[0]
        provs[pid]=pp
    own=set(provs)
    rows=[]
    for pid,pp in sorted(provs.items()):
        b8=P.u64(pp+0xb8)
        hdr=(P.try_read(b8,0x180) or b) if b8 else b''
        qwords=[]
        for o in range(0,min(len(hdr),0x180)-7,8):
            v=struct.unpack_from('<Q',hdr,o)[0]
            n=cls(pe,P,v)
            if n:
                qwords.append({'off':hex(o),'ptr':hex(v),'class':n})
        ar=_pdx_array(P,b8+0x70)
        size,cap,data=ar['size'],ar['capacity'],ar['data']
        buf=P.try_read(data, max(size,1)*128) or b''
        ptr_try=[]
        for i in range(size):
            if len(buf)<(i+1)*8: break
            q=struct.unpack_from('<Q',buf,i*8)[0]
            n=cls(pe,P,q)
            ptr_try.append({'i':i,'q':hex(q),'class':n,
                            'id58': try_u32(P,q+0x58) if n else None,
                            'ida4': try_u32(P,q+0xa4) if n else None})
        stride_ids={}
        for stride in (8,16,20,24,32,36,40,48,56,64):
            recs=[]
            for i in range(size):
                off=i*stride
                if off+min(stride,16)>len(buf):
                    break
                chunk=buf[off:off+stride] if off+stride<=len(buf) else buf[off:]
                u32s=[struct.unpack_from('<I',chunk,j)[0] for j in range(0,len(chunk)-3,4)]
                plausible=[v for v in u32s if 1<=v<=20000]
                recs.append({'i':i,'plausible':plausible,'u32s':u32s[:16],'hex':chunk[:48].hex()})
            stride_ids[stride]=recs
        rows.append({
            'province_id':pid,'pp':hex(pp),'b8':hex(b8),
            'array':{'size':size,'cap':cap,'data':hex(data) if data else None},
            'b8_typed_qwords':qwords,
            'ptr_stride8':ptr_try,
            'buf_len':len(buf),'buf_head':buf[:min(len(buf), 8+size*8)].hex() if buf else '',
            'strides': {str(s):v for s,v in stride_ids.items()},
        })
    print('own',sorted(own))
    for r in rows:
        print('PID',r['province_id'],'size',r['array']['size'],
              'ptr8',[e['class'] for e in r['ptr_stride8']],
              'ida4',[e['ida4'] for e in r['ptr_stride8']])
        for s in (8,16,24,32,40):
            recs=r['strides'][str(s)]
            print('  s',s,'plausible',[x['plausible'] for x in recs])
            if recs:
                print('    rec0 u32s',recs[0]['u32s'])
    Path('research/t179_province_b8_array.json').write_text(json.dumps({'own':sorted(own),'rows':rows},indent=2,default=str,ensure_ascii=False),encoding='utf-8')
finally:
    P.close()
