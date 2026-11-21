"""t179 static: identify 52df40, filter 1409890 stores, search adjacency strings."""
from __future__ import annotations
import sys, struct, bisect, json, re
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

HERE=Path('research')
IMAGE=0x140000000
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address

def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def e8_callers(target):
    hits=[]; start=0
    while True:
        j=blob.find(b'\xe8', start)
        if j<0 or j+5>len(blob): break
        rel=struct.unpack_from('<i', blob, j+1)[0]
        if va+j+5+rel==target:
            site=va+j; f=fn_of(site)
            hits.append({'site':hex(site),'func':hex(f[0]) if f else None,'end':hex(f[1]) if f else None})
        start=j+1
    return hits

def disasm(start,end,maxb=0x2000):
    size=min(max(end-start,0),maxb)
    raw=pe.read_rva(start,size) or b''
    out=[]
    for i in cs.disasm(raw,start):
        out.append((i.address,(i.mnemonic+' '+i.op_str).strip()))
        if i.address+i.size>=start+size: break
    return out

def lea_strings(func,end,maxb=0x8000):
    size=min(end-func,maxb)
    raw=pe.read_rva(func,size) or b''
    hits=[]
    for i in cs.disasm(raw,func):
        if i.mnemonic=='lea' and 'rip' in i.op_str and i.operands and len(i.operands)>=2:
            op=i.operands[1]
            if getattr(op,'type',None)==3:
                dest=i.address+i.size+op.mem.disp
                b=pe.read_rva(dest,96) or b''
                z=b.find(b'\x00')
                if z>=4 and all(32<=c<127 for c in b[:z]):
                    hits.append({'at':hex(i.address),'dest':hex(dest),'s':b[:z].decode('ascii')})
    return hits

# 52df40 identity
s,e=0x52df40, fn_of(0x52df40)[1] if fn_of(0x52df40) else 0x52e500
leas=lea_strings(s,e)
print('52df40 window',hex(s),hex(e),'strings:')
for x in leas:
    print(' ',x)

# who calls 52df40
c52=e8_callers(0x52df40)
print('E8 52df40 count',len(c52),'funcs',sorted({x['func'] for x in c52 if x['func']})[:20])

# 1453780 identity
for fn in (0x1453780,0x52df40):
    f=fn_of(fn)
    print('fn',hex(fn),'pdata',hex(f[0]) if f else None, hex(f[1]) if f else None)

# 1409890 callers excluding 1409810: nearby strings + post-call stores to non-stack?
callers=e8_callers(0x1409890)
print('1409890 sites',len(callers))
rows=[]
for hit in callers:
    func=int(hit['func'],16) if hit['func'] else int(hit['site'],16)
    fend=int(hit['end'],16) if hit['end'] else func+0x200
    strs=lea_strings(func, min(fend,func+0x6000))
    site=int(hit['site'],16)
    post=disasm(site, min(fend,site+0xa0), 0xa0)
    stores=[a for a in post if any(k in a[1] for k in ('mov qword ptr [','mov dword ptr [','lock add','add qword ptr ['))]
    # classify stack vs object
    obj_stores=[]
    for addr,asm in stores:
        if any(x in asm for x in ('rsp','rbp','esp','ebp')):
            continue
        obj_stores.append({'rva':hex(addr),'asm':asm})
    rows.append({
        'site':hit['site'],'func':hit['func'],
        'is_1409810_itself': hit['func']=='0x1409810',
        'strings':[s['s'] for s in strs[:15]],
        'obj_stores':obj_stores[:8],
    })
    print('1409890',hit['site'],'func',hit['func'],'obj_stores',len(obj_stores),'strs', [s['s'] for s in strs[:8]])

Path('research/t179_1409890_callers.json').write_text(json.dumps({
    '52df40':{'pdata':[hex(s),hex(e)],'strings':leas,'e8_callers':c52},
    '1409890_windows':rows,
},indent=2,ensure_ascii=False),encoding='utf-8')

# adjacency / neighbor strings
needles=[
    b'adjacency', b'Adjacency', b'ADJACENCY',
    b'neighbour', b'neighbor', b'Neighbour', b'Neighbor',
    b'river_crossing', b'RIVER_CROSSING', b'has_river',
    b'GetNeighbour', b'GetNeighbor', b'GetAdjacent',
    b'adjacent_provinces', b'adjacent_province',
    b'CAdjacency', b'province_adjacency',
    b'NAVAL_CROSSING', b'strait',
]
found=defaultdict(list)
for sec in pe.sections:
    data=pe.data[sec.raw_ptr:sec.raw_ptr+sec.raw_size]
    for n in needles:
        start=0
        while True:
            j=data.find(n,start)
            if j<0: break
            # full cstring
            # walk back to start
            i=j
            while i>0 and 32<=data[i-1]<127:
                i-=1
            z=data.find(b'\x00',j)
            s=data[i:z].decode('ascii','replace') if z>i else n.decode()
            rva=sec.virtual_address+i
            found[n.decode()].append({'rva':hex(rva),'s':s,'section':sec.name})
            start=j+len(n)
            if len(found[n.decode()])>=30:
                break

# also broader regex in .rdata only
rdata=next(s for s in pe.sections if s.name=='.rdata')
rd=pe.data[rdata.raw_ptr:rdata.raw_ptr+rdata.raw_size]
extra=[]
for m in re.finditer(rb'[\x20-\x7e]*(?:adjacen|neighbour|neighbor|river.?cross)[\x20-\x7e]*\x00', rd, re.I):
    s=m.group()[:-1].decode('ascii','replace')
    if len(s)<4: continue
    extra.append({'rva':hex(rdata.virtual_address+m.start()),'s':s})
    if len(extra)>=80:
        break

print('NEEDLE HITS')
for k,v in found.items():
    print(k, len(v), 'ex', v[0]['s'] if v else None)
print('rdata extra', len(extra))
for x in extra[:40]:
    print(' ',x)

Path('research/t179_adjacency_strings.json').write_text(json.dumps({
    'needles':{k:v[:20] for k,v in found.items()},
    'rdata_extra':extra,
},indent=2,ensure_ascii=False),encoding='utf-8')
print('done')
