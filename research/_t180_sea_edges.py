"""Sea/coastal edge flags + river/adjacency type strings + late cmp +0x10,1/2."""
from __future__ import annotations
import os,sys,json,struct,bisect,re
from pathlib import Path
from collections import Counter
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from pe import PE
from mem import Proc,find_pid
from gamestate import _rtti_name_from_vtable

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
def try_u64(P,a):
    b=P.try_read(a,8)
    return struct.unpack('<Q',b)[0] if b and len(b)==8 else None
def try_i32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<i',b)[0] if b and len(b)==4 else None
def try_u32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None

pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
# rdata strings
rdata=next(s for s in pe.sections if s.name=='.rdata')
rd=pe.data[rdata.raw_ptr:rdata.raw_ptr+rdata.raw_size]
needles=[]
for m in re.finditer(rb'[\x20-\x7e]{3,80}\x00', rd):
    s=m.group()[:-1].decode('ascii','replace')
    sl=s.lower()
    if any(k in sl for k in ('adjacenc','river','strait','is_land','is_sea','land_index','nland','eadjacency','adj_type','adjacency_type')):
        if any(skip in sl for skip in ('influence_per','intel_network','modifier_river','error reading','nmilitary','navy','diplomacy','lua')):
            continue
        if len(s)<80:
            needles.append({'rva':hex(rdata.virtual_address+m.start()),'s':s})
# unique interesting
print('string hits', len(needles))
for x in needles:
    if any(k in x['s'].lower() for k in ('type','land','sea','river','strait','adj','neighbor','crossing','impassable','bitmap')):
        print(x)

# late cmp byte +0x10 imm 1/2 after rva 0x800000
text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address
pd=next(s for s in pe.sections if s.name=='.pdata')
praw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',praw,o)[:2] for o in range(0,len(praw)-11,12)]
starts=[x[0] for x in functions]
def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

# start index for rva 0x800000
# rva = va + offset, va is text.virtual_address
start_off=max(0, 0x800000-va)
hits=[]
i=start_off
n=len(blob)
while i+6<=n:
    if blob[i]==0x80:
        modrm=blob[i+1]
        if (modrm & 0x38)==0x38 and (modrm & 0xC0)==0x40:
            has_sib=((modrm & 7)==4)
            disp_i=i+3 if has_sib else i+2
            if disp_i+1<n and blob[disp_i]==0x10:
                imm=blob[disp_i+1]
                if imm in (1,2):
                    site=va+i
                    f=fn_of(site)
                    hits.append({'at':hex(site),'func':hex(f[0]) if f else None,'imm':imm,'sib':has_sib})
        i+=1; continue
    i+=1
print('late cmp +0x10 imm1/2', hits)

# confirm bytes at 0xe90bb3
off=0xe90bb3-va
print('bytes at e90bb3', blob[off:off+8].hex())

P=Proc(find_pid('hoi4.exe'))
try:
    cmap=try_u64(P,P.base+0x33e7700)
    table=try_u64(P,cmap+0x2c0)
    cap_size=P.try_read(cmap+0x2c8,8)
    cap,size=struct.unpack('<II', cap_size)
    land_arr=try_u64(P,cmap+0x238)
    print('prov table', hex(table), 'cap',cap,'size',size)
    def land_index(pid):
        b=P.try_read(land_arr+pid*4,4)
        return struct.unpack('<i',b)[0] if b and len(b)==4 else None
    def prov_ptr(pid):
        if not (0<=pid<size): return None
        return try_u64(P, table+pid*8)
    def edges_of(pid):
        pp=prov_ptr(pid)
        if not pp: return {'pid':pid,'ptr':None}
        b8=try_u64(P,pp+0xb8)
        sz=try_i32(P,b8+0x7c) if b8 else None
        data=try_u64(P,b8+0x70) if b8 else None
        recs=[]
        if data and sz and 0<sz<=64:
            buf=P.try_read(data,sz*48) or b''
            for i in range(sz):
                off=i*48
                if off+48>len(buf): break
                chunk=buf[off:off+48]
                nid=struct.unpack_from('<I',chunk,8)[0]
                recs.append({'nid':nid,'q0':struct.unpack_from('<Q',chunk,0)[0],
                             'b10':chunk[0x10],'u10hex':hex(struct.unpack_from('<I',chunk,0x10)[0]),
                             'land_index':land_index(nid),'is_sea':land_index(nid)==-1})
        return {'pid':pid,'ptr':hex(pp),'class':cls(pe,P,pp),'id_a4':try_u32(P,pp+0xa4),
                'own_li':land_index(pid),'size':sz,'edges':recs,
                'b10hist':dict(Counter(r['b10'] for r in recs)),
                'sea_nids':[r['nid'] for r in recs if r['is_sea']],
                'land_nids':[r['nid'] for r in recs if r['land_index'] not in (None,-1)]}

    # sea samples
    sea_ids=[4,5,9,13,209,13450]
    sea_dump=[edges_of(i) for i in sea_ids]
    # find coastal from first sea's land neighbors
    coastal=[]
    for sd in sea_dump:
        for nid in sd.get('land_nids') or []:
            if nid not in coastal:
                coastal.append(nid)
            if len(coastal)>=4: break
        if len(coastal)>=4: break
    coast_dump=[edges_of(i) for i in coastal[:4]]
    print('SEA')
    for s in sea_dump:
        print(' sea', s['pid'], 'class', s['class'], 'ida4', s['id_a4'], 'li', s['own_li'], 'size', s['size'],
              'b10', s['b10hist'], 'n_sea', len(s['sea_nids']), 'n_land', len(s['land_nids']),
              'sample edges', s['edges'][:6])
    print('COASTAL')
    for s in coast_dump:
        print(' coast', s['pid'], 'class', s['class'], 'ida4', s['id_a4'], 'li', s['own_li'], 'size', s['size'],
              'b10', s['b10hist'], 'n_sea', len(s['sea_nids']), 'n_land', len(s['land_nids']))
        # b10 of edges that are sea vs land
        print('   sea-edge b10', [r['b10'] for r in s['edges'] if r['is_sea']])
        print('   land-edge b10', [r['b10'] for r in s['edges'] if not r['is_sea']])
    Path('research/t180_sea_coastal_edges.json').write_text(json.dumps({
        'sea':sea_dump,'coastal':coast_dump,'late_cmp':hits,
        'type_strings':[x for x in needles if len(x['s'])<80][:80]
    },indent=2,default=str,ensure_ascii=False),encoding='utf-8')
finally:
    P.close()
