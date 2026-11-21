"""t180: xref neighbor-array asserts, search +0xb8/+0x70 readers, RTTI."""
from __future__ import annotations
import sys, struct, bisect, json, re
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

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

def lea_xrefs(dest):
    hits=[]
    i=0
    n=len(blob)
    while i+7<=n:
        b0=blob[i]
        if b0 in (0x48,0x4c,0x49,0x4d):
            if i+1<n and blob[i+1]==0x8d:
                modrm=blob[i+2]
                if (modrm & 0xC7)==0x05:
                    rel=struct.unpack_from('<i',blob,i+3)[0]
                    if va+i+7+rel==dest:
                        hits.append(va+i)
        elif b0==0x8d and i+6<=n:
            modrm=blob[i+1]
            if (modrm & 0xC7)==0x05:
                rel=struct.unpack_from('<i',blob,i+2)[0]
                if va+i+6+rel==dest:
                    hits.append(va+i)
        i+=1
    return hits

def disasm(start,end,maxb=0x4000):
    size=min(max(end-start,0),maxb)
    raw=pe.read_rva(start,size) or b''
    out=[]
    for ins in cs.disasm(raw,start):
        out.append(f"0x{ins.address:x}  {ins.mnemonic} {ins.op_str}".strip())
        if ins.address+ins.size>=start+size: break
    return out

targets={
    'NeighborAdjs_size':0x29ea290,
    'sea_province_pathfinding':0x29db3e0,
    'RailwayLevels_NumNeighbors':0x29ef4d0,
    'RailwayLevels_MAX':0x29ef5a0,
    'adjacency_tick':0x29d8f80,
    'AlwaysOpenAdjacency':0x29df768,
    'river_crossing_token':0x2b494b0,
}
xmap={}
for name,dest in targets.items():
    xs=lea_xrefs(dest)
    # unique functions
    funcs=[]
    for x in xs:
        f=fn_of(x)
        funcs.append({'at':hex(x),'func':hex(f[0]) if f else None,'end':hex(f[1]) if f else None})
    xmap[name]=funcs
    print(name, 'xrefs', [(h['at'],h['func'],h['end']) for h in funcs])

# dump each unique function (bounded)
written=set()
clips={}
for name,hits in xmap.items():
    for h in hits:
        if not h['func']:
            continue
        fn=int(h['func'],16)
        if fn in written:
            continue
        written.add(fn)
        end=int(h['end'],16)
        # continue a bit if pdata is short
        lines=disasm(fn, end, 0x8000)
        path=Path(f'research/_t180_clip_{name}_{h["func"]}.txt')
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        clips[f'{name}_{h["func"]}']={'func':h['func'],'end':h['end'],'ins':len(lines),'path':str(path),'xref_at':h['at']}
        print('wrote', path.name, 'ins', len(lines))
        # print around xref
        xref=int(h['at'],16)
        around=[l for l in lines if abs(int(l.split()[0],16)-xref)<0x80]
        print('--- around', name, h['at'], '---')
        print('\n'.join(around[:40]))
        print()

# RTTI short names
data=next(s for s in pe.sections if s.name=='.data')
db=pe.data[data.raw_ptr:data.raw_ptr+data.raw_size]
rtti=[]
for m in re.finditer(rb'\.\?AV[ -~]{0,200}(?:Adjacen|Neighbour|Neighbor|Strait|RiverCross)[ -~]{0,200}@@', db):
    s=m.group().decode('ascii','replace')
    if any(x in s for x in ('_Binder','Allocator','_Func_impl','reference_wrapper','CEffectEntry','CTriggerEntry','lambda','SPdxParallel')):
        continue
    rtti.append({'rva':hex(data.virtual_address+m.start()),'s':s})
print('RTTI')
for x in rtti:
    print(' ',x)

Path('research/t180_adjacency_xrefs.json').write_text(json.dumps({
    'lea_xrefs':xmap,'clips':clips,'rtti':rtti
},indent=2,ensure_ascii=False),encoding='utf-8')
print('done xrefs')
