"""t179: xref neighbour assert + clip logistics.postdailythreaded + rtti adjacency."""
from __future__ import annotations
import sys, struct, bisect, json, re
from pathlib import Path
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
    """Find lea r64,[rip+disp] whose computed dest == dest."""
    hits=[]
    # walk capstone would be slow on all .text; scan rex lea rip encodings
    # 48/4C 8D 05/0D/15/1D/25/2D/35/3D rel32  (rip-relative, modrm 00 xxx 101)
    i=0
    n=len(blob)
    while i+7<=n:
        b0=blob[i]
        # optional REX
        off=i
        if b0 in (0x48,0x4c,0x49,0x4d):
            if i+1<n and blob[i+1]==0x8d:
                modrm=blob[i+2]
                if (modrm & 0xC7)==0x05:  # mod=00, r/m=101 rip
                    rel=struct.unpack_from('<i',blob,i+3)[0]
                    insn_len=7
                    tgt=va+i+insn_len+rel
                    if tgt==dest:
                        hits.append(va+i)
                    i+=1
                    continue
        elif b0==0x8d and i+6<=n:
            modrm=blob[i+1]
            if (modrm & 0xC7)==0x05:
                rel=struct.unpack_from('<i',blob,i+2)[0]
                tgt=va+i+6+rel
                if tgt==dest:
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

# xrefs to key strings
targets={
    'NeighboursCount':0x29b5250,
    'not_neighbours':0x27f8388,
    'NeighborAdjacency_assert':0x29df768,
    'Invalid_adjacency_rule':0x29bb890,
}
xmap={}
for name,dest in targets.items():
    xs=lea_xrefs(dest)
    xmap[name]=[hex(x) for x in xs]
    print(name, 'lea xrefs', [hex(x) for x in xs])
    for x in xs:
        f=fn_of(x)
        print('  in', hex(f[0]) if f else None, '-', hex(f[1]) if f else None)

# dump neighbour-count function(s)
clips={}
for x in xmap['NeighboursCount']:
    rva=int(x,16)
    f=fn_of(rva)
    if not f: continue
    lines=disasm(f[0], f[1], 0x8000)
    clips[f'fn_{x}']={'func':hex(f[0]),'end':hex(f[1]),'xref_at':x,'nins':len(lines)}
    Path(f'research/_t179_clip_neighbours_{hex(f[0])}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('wrote neighbours fn',hex(f[0]),'ins',len(lines),'end',hex(f[1]))
    # print first 80 and around xref
    print('--- head ---')
    print('\n'.join(lines[:80]))
    # around xref
    around=[l for l in lines if abs(int(l.split()[0],16)-rva)<0x80]
    print('--- around xref ---')
    print('\n'.join(around))

for name in ('not_neighbours','NeighborAdjacency_assert'):
    for x in xmap[name]:
        rva=int(x,16)
        f=fn_of(rva)
        if not f: continue
        lines=disasm(f[0], min(f[1], f[0]+0x2000), 0x2000)
        Path(f'research/_t179_clip_{name}_{hex(f[0])}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print('wrote', name, 'fn', hex(f[0]), 'ins', len(lines))
        print('--- around ---')
        around=[l for l in lines if abs(int(l.split()[0],16)-rva)<0x60]
        print('\n'.join(around)[:2000])

# clip 140ba10 around 1409890
f=fn_of(0x140ba10)
print('140ba10 pdata', hex(f[0]) if f else None, hex(f[1]) if f else None)
if f:
    # pdata may truncate; disassemble at least through 140bb92+0x200
    end=max(f[1], 0x140bb92+0x300)
    lines=disasm(0x140ba10, end, 0x4000)
    Path('research/_t179_clip_140ba10.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('140ba10 ins',len(lines),'last',lines[-1] if lines else None)
    # window around call
    around=[l for l in lines if 0x140bb70 <= int(l.split()[0],16) <= 0x140bc80]
    print('--- 140ba10 around 1409890 ---')
    print('\n'.join(around))

# RTTI names containing Adjacency or Neighbour (not only RuleIcon noise)
# scan .data for .?AV*Adjacency* and *Neighbour*
data=next(s for s in pe.sections if s.name=='.data')
db=pe.data[data.raw_ptr:data.raw_ptr+data.raw_size]
rtti=[]
for m in re.finditer(rb'\.\?AV[ -~]{0,160}(?:Adjacen|Neighbour|Neighbor|Province)[ -~]{0,160}@@', db):
    s=m.group().decode('ascii','replace')
    # skip binders / allocators / icons unless short class name
    rtti.append({'rva':hex(data.virtual_address+m.start()),'s':s})
# unique short
short=[]
seen=set()
for x in rtti:
    name=x['s']
    if '_Binder' in name or 'Allocator' in name or '_Func_impl' in name:
        continue
    if name not in seen:
        seen.add(name); short.append(x)
print('RTTI short', len(short))
for x in short[:60]:
    print(' ',x)

Path('research/t179_adjacency_xrefs.json').write_text(json.dumps({
    'lea_xrefs':xmap,
    'clips':clips,
    'rtti_short':short,
    'rtti_all_count':len(rtti),
},indent=2,ensure_ascii=False),encoding='utf-8')
print('done')
