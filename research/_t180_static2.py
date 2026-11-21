"""t180: land-index global, live classify neighbors, edge flags, more readers."""
from __future__ import annotations
import os,sys,json,struct,bisect
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
sys.path.insert(0,'calling')
from pe import PE
from mem import Proc,find_pid
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,_pdx_array
import offsets as O

pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
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
        rel=struct.unpack_from('<i',blob,j+1)[0]
        if va+j+5+rel==target:
            site=va+j; f=fn_of(site)
            hits.append({'site':hex(site),'func':hex(f[0]) if f else None})
        start=j+1
    return hits

# resolve rip of mov r8, [rip+disp] at 0xd55637
# also print a few instructions around it from existing clip
# compute dest from capstone
raw=pe.read_rva(0xd55633, 0x30) or b''
for ins in cs.disasm(raw, 0xd55633):
    print(hex(ins.address), ins.mnemonic, ins.op_str)
    if ins.operands:
        for op in ins.operands:
            if getattr(op,'type',None)==3 and op.mem.base==0: # maybe rip
                pass
            if ins.mnemonic.startswith('mov') and 'rip' in ins.op_str:
                dest=ins.address+ins.size+op.mem.disp if getattr(op,'type',None)==3 else None
                if dest:
                    print('  rip dest', hex(dest))

# search .text for other lea/mov of the same land-index pattern:
# movsxd rdx, dword ptr [reg + 0xa4]
# then [reg + 0x238]
# already have one. Also search imul 0x30 / lea rax,rax*2 shl 4 after +0x70

# find mov/lea involving 0x70 then +8 or add 0x30 in same function - sample count
# quicker: find all "shl rxx, 4" after "lea rxx, [rxx+rxx*2]" i.e. *48
# encoding lea r64, [r + r*2] is various; then shl x, 4

def find_stride48_sites(limit=80):
    sites=[]
    # scan capstone is slow on all text; search bytes for shl r64, 4 after nearby lea
    # shl r/m, 4 : 48 c1 e0..e7 04  or 49 c1 e0..e7 04
    start=0
    while len(sites)<limit:
        # look for 48 8d xx (lea) then within 16 bytes 48 c1 eX 04
        j=blob.find(b'\x48\x8d', start)
        if j<0: break
        window=blob[j:j+16]
        k=window.find(b'\x48\xc1')
        if k>=0 and k+3<len(window) and window[k+2] in range(0xe0,0xe8) and window[k+3]==0x04:
            site=va+j
            f=fn_of(site)
            sites.append({'lea':hex(site),'func':hex(f[0]) if f else None})
        start=j+1
    return sites

s48=find_stride48_sites(60)
print('stride48 lea-shl4 sites', len(s48))
from collections import Counter
print('funcs', Counter(x['func'] for x in s48).most_common(20))

c_e90560=e8_callers(0xe90560)
print('E8 e90560', len(c_e90560), c_e90560[:15])

Path('research/t180_stride48_sites.json').write_text(json.dumps({
    'lea_shl4_sample':s48,
    'e90560_callers':c_e90560,
},indent=2),encoding='utf-8')
print('static part done')
