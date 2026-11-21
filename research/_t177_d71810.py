
import sys,struct,bisect,json
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

def clip(start,end,cap=0x2000):
    end=min(end,start+cap)
    rawb=pe.read_rva(start,end-start) or b''
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(rawb,start)]

text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address

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

def window(site, before=80, after=160):
    rawb=pe.read_rva(site-before, before+after) or b''
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(rawb, site-before)]

targets={
    'd71810':0xd71810,
    '188d90':0x188d90,
    '72f220':0x72f220,
    '75aab0':0x75aab0,
    '72a990':0x72a990,
    '15a6450':0x15a6450,
}
for name,rva in targets.items():
    w=fn_of(rva)
    if not w:
        print(name, 'NO PDATA at', hex(rva), 'containing', fn_of(rva) if False else 'try mid')
        # if mid-function, still clip from rva
        w=(rva, rva+0x800)
    lines=clip(w[0] if w[0]==rva else rva, w[1] if w and w[1]>rva else rva+0x1000, 0x2000)
    Path(f'research/_t177_clip_{name}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    calls=[l for l in lines if 'call ' in l]
    print('====', name, 'pdata', hex(w[0]), hex(w[1]) if w else None, 'n', len(lines), 'ncalls', len(calls))
    # print interesting calls
    for l in lines:
        if any(k in l for k in ('call ','0xf78','0x15a93d0','0xcb8e80','0x15a16a0','0x15a92c0','0x1092b70','0x10948a0','+ 0x10]','+ 8]')):
            if l.split('  ',1)[-1].startswith(('call','mov','lea','cmp')) or '0x15a' in l or '0xcb8' in l:
                print(' ', l)

# better 74dee0 window: try several alignments
print('===== 74f87c alignments =====')
site=0x74f87c
# disassemble the whole function from pdata start around the site
w=fn_of(site)
print('containing', w)
if w:
    # extract lines near site from a precise disasm of the function chunk covering site
    start=max(w[0], site-0x200)
    rawb=pe.read_rva(start, min(w[1], site+0x200)-start) or b''
    lines=[f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(rawb,start)]
    # find first line >= site-80
    sel=[l for l in lines if site-80<=int(l.split()[0],16)<=site+160]
    Path('research/_t177_win_f78_0x74dee0_aligned.txt').write_text('\n'.join(sel)+'\n',encoding='utf-8')
    print('\n'.join(sel))

# E8 of d71810, 188d90, 72f220, 75aab0
e8={}
for name,rva in (('d71810',0xd71810),('188d90',0x188d90),('72f220',0x72f220),('75aab0',0x75aab0)):
    h=e8_callers(rva)
    e8[name]={'count':len(h),'funcs':sorted({x['func'] for x in h if x['func']}),'sites':h}
    print('E8', name, 'count', len(h), 'funcs', e8[name]['funcs'])

Path('research/t177_d71810_e8.json').write_text(json.dumps(e8,indent=2),encoding='utf-8')
