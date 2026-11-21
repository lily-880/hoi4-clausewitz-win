
import sys,struct,json,bisect,re
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

IMAGE=0x140000000
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
cs=Cs(CS_ARCH_X86,CS_MODE_64)

def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, end, first_ret=False):
    rawb=pe.read_rva(start, end-start) or b''
    lines=[]
    for i in cs.disasm(rawb, start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if first_ret and i.mnemonic=='ret':
            break
    return lines

def cstring(rva, n=160):
    b=pe.read_rva(rva, n) or b''
    z=b.find(b'\x00')
    if z<0: z=len(b)
    try:
        return b[:z].decode('utf-8', errors='replace')
    except Exception:
        return b[:z].hex()

# finish clipped funcs: cf4e10, 10948a0
for start,end,name in (
    (0xcf4e10, 0xcf4e80, 'cf4e10_full'),
    (0x10948a0, 0x1094960, '10948a0_full'),
    (0xfdf340, None, 'fdf340'),
    (0xfe35d0, None, 'fe35d0'),
    (0xfe77c0, None, 'fe77c0'),
    (0xd6f4c4, None, 'd6f4c4_parent'),
    (0x717400, None, '717400'),
    (0xc08790, None, 'c08790'),
    (0xc2fe90, None, 'c2fe90'),
    (0xcacb80, None, 'cacb80'),
    (0xcabc08, None, 'cabc08_parent'),
):
    if end is None:
        w=fn_of(start)
        if not w:
            # start in middle: use containing
            i=bisect.bisect_right(starts,start)-1
            w=functions[i] if i>=0 else (start, start+0x400)
            # if start is mid-func, clip from start still, but record parent
        end=w[1] if w and w[1]>start else start+0x500
        # cap
        end=min(end, start+0x700)
        parent=fn_of(start)
    else:
        parent=fn_of(start)
    lines=clip(start, end, first_ret=False)
    # stop at first ret after a reasonable body if huge; keep all within cap
    Path(f'research/_t176_clip_{name}.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(name, 'parent', hex(parent[0]) if parent else None, 'end', hex(parent[1]) if parent else hex(end), 'n', len(lines))

# resolve assert/file strings in fe84d0 / fe86c0
def rip_targets(clip_path, lea_or_file=True):
    lines=Path(clip_path).read_text(encoding='utf-8').splitlines()
    out=[]
    for l in lines:
        m=re.search(r'^(0x[0-9a-f]+)  lea \w+, \[rip \+ (0x[0-9a-f]+)\]', l)
        if not m: continue
        site=int(m.group(1),16)
        rel=int(m.group(2),16)
        # instruction length 7 for rex lea
        dest=site+7+rel
        s=cstring(dest)
        if s and (len(s)>=4):
            out.append({'site':hex(site),'dest':hex(dest),'s':s[:200]})
    return out

for name in ['fe84d0','fe86c0','fe1160','fe1590']:
    refs=rip_targets(f'research/_t176_clip_{name}.txt')
    Path(f'research/_t176_strings_{name}.json').write_text(json.dumps(refs,indent=2,ensure_ascii=False),encoding='utf-8')
    print('strings', name, refs[:6])

# 15a93d0 preferred-base hit locations
pref=struct.pack('<Q', IMAGE+0x15a93d0)
hits=[]
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    start=0
    while True:
        j=blob.find(pref, start)
        if j<0: break
        hits.append({'section':s.name,'rva':hex(s.virtual_address+j)})
        start=j+8
print('15a93d0 pref hits', hits)

# search disp32 == 0xf78 in .text
text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
needle=struct.pack('<I', 0xf78)
sites=[]
start=0
while True:
    j=blob.find(needle, start)
    if j<0: break
    # likely last 4 bytes of a disp32 instruction; include nearby
    rva=text.virtual_address+j
    f=fn_of(rva)
    sites.append({'rva':hex(rva),'func':hex(f[0]) if f else None})
    start=j+1
# unique funcs
funcs=defaultdict(list)
for s in sites:
    funcs[s['func']].append(s['rva'])
# prefer reinforcement-related clusters
interesting=[]
for f,rs in funcs.items():
    if not f: continue
    fv=int(f,16)
    if (0x1400000<=fv<0x1420000) or (0x15a0000<=fv<0x15c0000) or (0xcb0000<=fv<0xcc0000) or (0x710000<=fv<0x720000) or (0xce0000<=fv<0xd00000):
        interesting.append((f,rs))
print('0xf78 site count', len(sites), 'funcs', len(funcs), 'interesting', len(interesting))
Path('research/t176_f78_access.json').write_text(json.dumps({
    'n_sites':len(sites),'n_funcs':len(funcs),
    'interesting':[{'func':f,'sites':rs} for f,rs in sorted(interesting, key=lambda x:int(x[0],16))],
    'all_funcs':sorted((f or 'none') for f in funcs),
},indent=2),encoding='utf-8')
for f,rs in sorted(interesting, key=lambda x:int(x[0],16)):
    print('F78', f, 'n', len(rs), 'e.g.', rs[:4])
