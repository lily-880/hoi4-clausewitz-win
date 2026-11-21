
import sys,struct,json,bisect,re
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

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

def clip(start,end,cap=0x800):
    end=min(end,start+cap)
    rawb=pe.read_rva(start,end-start) or b''
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(rawb,start)]

text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address

def e8_callers(target):
    hits=[]
    start=0
    while True:
        j=blob.find(b'\xe8', start)
        if j<0 or j+5>len(blob): break
        rel=struct.unpack_from('<i', blob, j+1)[0]
        dest=va+j+5+rel
        if dest==target:
            site=va+j
            f=fn_of(site)
            hits.append({'site':hex(site),'func':hex(f[0]) if f else None,'func_end':hex(f[1]) if f else None})
        start=j+1
    return hits

callers=e8_callers(0x717400)
print('717400 caller count', len(callers))
# unique funcs
uf=sorted({c['func'] for c in callers if c['func']}, key=lambda x:int(x,16))
print('unique funcs', len(uf))

# For each unique caller func, see if it contains call [reg+0x10] and/or cb8e80/15a16a0/15a93d0
summaries=[]
slot2_funcs=[]
for fhex in uf:
    f=int(fhex,16)
    w=fn_of(f)
    end=w[1] if w else f+0x400
    # cap large funcs at 0x2000 for search, but record size
    size=end-f
    rawb=pe.read_rva(f, min(size,0x4000)) or b''
    lines=[f"{i.mnemonic} {i.op_str}" for i in cs.disasm(rawb,f)]
    textl='\n'.join(lines)
    has_slot2=any('qword ptr [r' in l and '+ 0x10]' in l and l.startswith('call') for l in lines)
    # more precise
    has_call_10=any(l.startswith('call qword ptr [') and '+ 0x10]' in l for l in lines)
    has_cb8e80='0xcb8e80' in textl
    has_15a16a0='0x15a16a0' in textl
    has_15a93d0='0x15a93d0' in textl
    has_15a16='0x15a16a0' in textl
    rec={'func':fhex,'size':size,'n717400':sum(1 for c in callers if c['func']==fhex),
         'call_slot10':has_call_10,'cb8e80':has_cb8e80,'15a16a0':has_15a16a0,'15a93d0':has_15a93d0}
    summaries.append(rec)
    if has_call_10 or has_cb8e80 or has_15a16a0 or has_15a93d0:
        slot2_funcs.append(rec)
        # save clip (cap 0x1000)
        Path(f'research/_t176_clip_717400_caller_{fhex}.txt').write_text('\n'.join(clip(f,end,0x1200))+'\n',encoding='utf-8')

print('funcs with slot2/cb8e80/15a16a0:')
print(json.dumps(slot2_funcs,indent=2))
Path('research/t176_717400_callers.json').write_text(json.dumps({
    'count':len(callers),'sites':callers,'funcs':uf,'summaries':summaries,'interesting':slot2_funcs
},indent=2),encoding='utf-8')
print('all funcs', uf)

# also e8 callers of 100f620? skip. clip 100f620 short and fe35d0 continued
for start,name,cap in ((0x100f620,'100f620',0x80),(0xfe35d0,'fe35d0_again',0x40)):
    w=fn_of(start)
    # if tiny pdata, keep going a bit
    end=(w[1] if w and w[1]-start>8 else start+cap)
    lines=clip(start,end,cap)
    Path(f'research/_t176_clip_{name}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(name, 'pdata', w, 'n', len(lines))
    print('\n'.join(lines[:40]))

# 141c7d0 +0xf78 context: window around sites
for site in (0x141c90d,0x141cb32,0x711f0a,0x7128f9,0x7137ed,0xceee44,0xcf0952,0xcf0a41,0xcf7d5a):
    rawb=pe.read_rva(site-32, 96) or b''
    lines=[f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(rawb,site-32)]
    print('---- around', hex(site))
    print('\n'.join(lines))
