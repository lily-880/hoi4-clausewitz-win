
import sys,struct,json,bisect
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
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=False

def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, end=None, max_len=0x800):
    if end is None:
        w=fn_of(start)
        end=w[1] if w else start+max_len
    end=min(end, start+max_len)
    rawb=pe.read_rva(start, end-start) or b''
    lines=[]
    for i in cs.disasm(rawb, start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if i.mnemonic=='ret':
            break
    return lines

def section_bytes(name):
    s=next(x for x in pe.sections if x.name==name)
    return s.virtual_address, pe.data[s.raw_ptr:s.raw_ptr+s.raw_size], s

# --- E8/E9 callers ---
targets={
    0xcb8e80:'cb8e80',
    0x15a16a0:'15a16a0',
    0x15a93d0:'15a93d0',
    0x15a92c0:'15a92c0',
    0xfe84d0:'fe84d0',
    0xfe86c0:'fe86c0',
    0xfe6550:'fe6550',
    0xfe1160:'fe1160',
    0xfe1590:'fe1590',
    0x10948a0:'10948a0',
    0xcf4e10:'cf4e10',
    0xc9fde0:'c9fde0',
    0x717410:'717410',
}
text_va, text, text_sec = section_bytes('.text')
callers=defaultdict(list)
# scan E8/E9
mv=memoryview(text)
n=len(text)
i=0
# faster: find all E8/E9 via bytes.find in chunks? iterate
# Use a simple loop; 30-50MB is OK in a few seconds if we skip non-E8 quickly
data=bytes(text)  # already bytes
idx=0
for op,size in ((0xE8,5),(0xE9,5)):
    start=0
    while True:
        j=data.find(bytes([op]), start)
        if j<0 or j+5>n: break
        rel=struct.unpack_from('<i', data, j+1)[0]
        dest=text_va+j+5+rel
        if dest in targets:
            site=text_va+j
            f=fn_of(site)
            callers[targets[dest]].append({
                'site':hex(site),'kind':'e8' if op==0xE8 else 'e9',
                'func':hex(f[0]) if f else None,
                'func_end':hex(f[1]) if f else None,
            })
        start=j+1

# --- preferred-base pointer hits ---
def find_ptr(qword, sections=('.rdata','.data','.text','.rdata')):
    hits=[]
    needle=struct.pack('<Q', qword)
    seen=set()
    for name in ('.rdata','.data','.text'):
        va, blob, sec = section_bytes(name)
        start=0
        while True:
            j=blob.find(needle, start)
            if j<0: break
            if j%8==0 or True:
                hits.append({'section':name,'rva':hex(va+j)})
            start=j+8
    return hits

pref_hits={}
for rva,name in (
    (0x15a93d0,'15a93d0'),
    (0x15a92c0,'15a92c0'),
    (0xcb8e80,'cb8e80'),
    (0x2a4b878,'CReinforcementStatus_vtable'),
):
    pref_hits[name]=find_ptr(IMAGE+rva)

# LEA/RIP-rel to vtable 0x2a4b878 in .text
vt=0x2a4b878
lea_hits=[]
# 48 8D / rex.w lea
# look for rel32 such that site+7+rel == vt (for lea reg, [rip+rel] which is 48 8D 05/0D/15/1D/25/2D/35/3D)
# also 4C 8D for r8-r15
start=0
while True:
    # search potential lea rex
    j=data.find(b'\x8d', start)
    if j<0 or j+5>n: break
    if j>=1 and data[j-1] in (0x48,0x4c) and (data[j+1] & 0xC7)==0x05:
        # lea r, [rip+rel32]; instruction starts at j-1, len 7
        site=text_va+(j-1)
        rel=struct.unpack_from('<i', data, j+2)[0]
        dest=site+7+rel
        if dest==vt:
            f=fn_of(site)
            lea_hits.append({'site':hex(site),'func':hex(f[0]) if f else None,'dest':hex(dest)})
    start=j+1

# clip key functions (first-ret, then also note pdata end)
clips={}
for rva,name,maxlen in (
    (0xfe84d0,'fe84d0',0x600),
    (0xfe86c0,'fe86c0',0x600),
    (0xfe6550,'fe6550',0x300),
    (0xfe1160,'fe1160',0x300),
    (0xfe1590,'fe1590',0x300),
    (0x10948a0,'10948a0',0x500),
    (0xcf4e10,'cf4e10',0x300),
    (0xc9fde0,'c9fde0',0x400),
    (0x717542,'717542_handle_path',0x200),
):
    w=fn_of(rva)
    start=rva if name!='717542_handle_path' else 0x717542
    end=(w[1] if w else start+maxlen)
    lines=clip(start, end, maxlen)
    clips[name]={'pdata':hex(w[0]) if w else None,'pdata_end':hex(w[1]) if w else None,'n':len(lines)}
    Path(f'research/_t176_clip_{name}.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')

# also dump 717410 full to end (pdata)
w=fn_of(0x717410)
if w:
    lines=clip(w[0], w[1], 0x400)
    Path('research/_t176_clip_717410_full.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    clips['717410_full']={'pdata':hex(w[0]),'pdata_end':hex(w[1]),'n':len(lines)}

# summarize callers (cap 40 each, but keep all counts)
out={
    'callers':{k:v[:60] for k,v in callers.items()},
    'caller_counts':{k:len(v) for k,v in callers.items()},
    'preferred_base_hits':pref_hits,
    'vtable_lea_0x2a4b878':lea_hits,
    'clips':clips,
}
# unique caller functions
out['caller_funcs']={k:sorted({c['func'] for c in v if c['func']}) for k,v in callers.items()}
Path('research/t176_static_refs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({
    'caller_counts':out['caller_counts'],
    'caller_funcs':out['caller_funcs'],
    'pref_hit_counts':{k:len(v) for k,v in pref_hits.items()},
    'vtable_lea':lea_hits,
    'clips':{k:v for k,v in clips.items()},
},indent=2))
