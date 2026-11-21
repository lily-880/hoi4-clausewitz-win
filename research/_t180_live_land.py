"""t180 live: land-index table + per-edge flags. Read-only."""
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
def try_i32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<i',b)[0] if b and len(b)==4 else None
def try_u8(P,a):
    b=P.try_read(a,1)
    return b[0] if b else None
def try_u64(P,a):
    b=P.try_read(a,8)
    return struct.unpack('<Q',b)[0] if b and len(b)==8 else None

pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
P=Proc(find_pid('hoi4.exe'))
try:
    session=detect_session(P,pe)
    gs=int(session['signals']['gs_ptr'],16)
    country=resolve_player_country(P,gs)
    cp=int(country['country_ptr'],16)
    # land-index global at RVA 0x33e7700
    gaddr=P.base+0x33e7700
    gobj=try_u64(P,gaddr)
    land_arr=try_u64(P,gobj+0x238) if gobj else None
    # probe a few object fields / class
    info={'global_rva':'0x33e7700','global_live':hex(gaddr),'object':hex(gobj) if gobj else None,
          'object_class':cls(pe,P,gobj) if gobj else None,'land_arr':hex(land_arr) if land_arr else None}
    # table length? try object+0x2d4 as max id (seen in a228f0 as [rax+0x2d4])
    # also dump nearby dwords
    nearby={}
    if gobj:
        for off in (0x220,0x228,0x230,0x238,0x240,0x248,0x250,0x2c8,0x2d0,0x2d4,0x2d8,0x2dc,0x2e0,0x2ec):
            nearby[hex(off)]={'u64':hex(try_u64(P,gobj+off) or 0),'i32':try_i32(P,gobj+off),'class':cls(pe,P,try_u64(P,gobj+off) or 0)}
    info['nearby']=nearby
    max_id=try_i32(P,gobj+0x2d4) if gobj else None
    info['max_id_2d4']=max_id
    # sample land index for ids 1, 1984, and a likely sea (often low ids are land, some sea)
    samples={}
    if land_arr:
        for pid in [1,2,3,1984,2072,5000,13137,13200,13241,8000,10000]:
            samples[pid]=try_i32(P, land_arr+pid*4)
    info['samples']=samples

    armies=_pdx_array(P,cp+O.HYPOTHESIS_STRUCT['CO_ARMIES'])
    provs={}
    for i in range(min(armies['size'],64)):
        ap=P.u64(armies['data']+8*i)
        if cls(pe,P,ap)!='CArmy': continue
        pp=P.u64(ap+O.HYPOTHESIS_STRUCT['CA_PROVINCE'])
        if not pp: continue
        pid=try_u32(P,pp+0xa4)
        if pid: provs[pid]=pp

    def land_index(pid):
        if not land_arr or pid is None: return None
        return try_i32(P, land_arr+pid*4)

    rows=[]
    all_edges=[]
    for pid,pp in sorted(provs.items()):
        b8=try_u64(P,pp+0xb8)
        size=try_i32(P,b8+0x7c) if b8 else None
        data=try_u64(P,b8+0x70) if b8 else None
        d2=try_u8(P,b8+0xd2) if b8 else None
        recs=[]
        if data and size and 0<size<=64:
            buf=P.try_read(data, size*48) or b''
            for i in range(size):
                off=i*48
                if off+48>len(buf): break
                chunk=buf[off:off+48]
                nid=struct.unpack_from('<I',chunk,8)[0]
                q0=struct.unpack_from('<Q',chunk,0)[0]
                b10=chunk[0x10]
                u10=struct.unpack_from('<I',chunk,0x10)[0]
                u14=struct.unpack_from('<I',chunk,0x14)[0]
                u18=struct.unpack_from('<I',chunk,0x18)[0]
                u20=struct.unpack_from('<I',chunk,0x20)[0]
                u24=struct.unpack_from('<I',chunk,0x24)[0]
                rec={'i':i,'nid':nid,'q0':q0,'b10':b10,'u10':u10,'u10hex':hex(u10),'u14':u14,
                     'u18':u18,'u20':u20,'u24':u24,'land_index':land_index(nid),
                     'is_sea_by_landindex': (land_index(nid)==-1)}
                recs.append(rec)
                all_edges.append((pid,rec))
        rows.append({
            'province_id':pid,'ptr':hex(pp),'b8':hex(b8) if b8 else None,
            'size_7c':size,'data_70':hex(data) if data else None,
            'b8_d2':d2,'b8_d2_bits': {'bit0': bool(d2&1) if d2 is not None else None,'bit1': bool(d2&2) if d2 is not None else None},
            'own_land_index':land_index(pid),'edges':recs,
            'land_neighbors':[r['nid'] for r in recs if r['land_index'] is not None and r['land_index']!=-1],
            'sea_neighbors':[r['nid'] for r in recs if r['land_index']==-1],
        })

    # flag histograms
    from collections import Counter
    hist_b10=Counter(r['b10'] for _,r in all_edges)
    hist_u10=Counter(r['u10hex'] for _,r in all_edges)
    hist_u14=Counter(r['u14'] for _,r in all_edges)
    n_sea=sum(1 for _,r in all_edges if r['is_sea_by_landindex'])
    n_land=sum(1 for _,r in all_edges if r['land_index'] is not None and r['land_index']!=-1)
    n_unknown=sum(1 for _,r in all_edges if r['land_index'] is None)

    # land reciprocity among own land neighbors
    own=set(provs)
    land_graph={r['province_id']:r['land_neighbors'] for r in rows}
    internal=[(p,n) for p,ns in land_graph.items() for n in ns if n in own]
    recip=sum(p in land_graph.get(n,[]) for p,n in internal)

    out={'pid':P.pid,'read_only':True,'land_index_global':info,
         'hist_b10':dict(hist_b10),'hist_u10':dict(hist_u10),'hist_u14':dict(u14 if False else hist_u14),
         'edge_counts':{'total':len(all_edges),'land':n_land,'sea':n_sea,'unknown':n_unknown},
         'own_land_reciprocal':{'internal':len(internal),'reciprocal':recip},
         'provinces':rows}
    Path('research/t180_landindex_and_edges.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    print('global', json.dumps(info,default=str)[:2000])
    print('counts', n_land, 'land', n_sea, 'sea', n_unknown, 'unk', 'hist_b10', dict(hist_b10), 'hist_u14', dict(hist_u14))
    print('recip', recip, '/', len(internal))
    for r in rows:
        print('PID',r['province_id'],'d2',r['b8_d2'],'ownLI',r['own_land_index'],
              'land',r['land_neighbors'],'sea',r['sea_neighbors'],
              'b10',[e['b10'] for e in r['edges']])
finally:
    P.close()
