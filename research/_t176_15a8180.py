
import sys,struct,json,bisect
from pathlib import Path
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

def clip(start,end=None,cap=0xa00):
    if end is None:
        w=fn_of(start)
        end=w[1] if w else start+cap
    end=min(end,start+cap)
    rawb=pe.read_rva(start,end-start) or b''
    lines=[]
    for i in cs.disasm(rawb,start):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    return lines

# list pdata funcs in 15a4000-15aa000
near=[(s,e) for s,e in functions if 0x15a4000<=s<0x15aa000]
print('funcs in 15a4-15aa:', len(near))
for s,e in near:
    print(hex(s), hex(e), 'len', e-s)

for start,name,cap in (
    (0x15a8180,'15a8180',0xa00),
    (0x15a4620,'15a4620',0x400),
):
    w=fn_of(start)
    lines=clip(start, w[1] if w else None, cap)
    Path(f'research/_t176_clip_{name}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('====', name, 'pdata', w, 'n', len(lines), 'has slot10', any('call qword ptr' in l and '+ 0x10]' in l for l in lines))
    # print calls
    for l in lines:
        if l.split('  ',1)[1].startswith('call') or '0xf78' in l or '0x200' in l or 'cb8e80' in l or '15a93d0' in l or '15a16a0' in l or '10948a0' in l:
            print(' ', l)

# E8 callers of 15a8180
text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address
def e8(target):
    hits=[]; start=0
    while True:
        j=blob.find(b'\xe8', start)
        if j<0 or j+5>len(blob): break
        rel=struct.unpack_from('<i', blob, j+1)[0]
        if va+j+5+rel==target:
            site=va+j; f=fn_of(site)
            hits.append({'site':hex(site),'func':hex(f[0]) if f else None})
        start=j+1
    return hits
for t,n in ((0x15a8180,'15a8180'),(0x15a4620,'15a4620'),(0x15a4a70,'15a4a70_ctor')):
    h=e8(t)
    print('E8', n, 'count', len(h), 'funcs', sorted({x['func'] for x in h}))
    Path(f'research/t176_e8_{n}.json').write_text(json.dumps(h,indent=2),encoding='utf-8')
