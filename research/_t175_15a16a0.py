
"""Disassemble 15a16a0 and find its callers — candidate offer dispatcher."""
import sys,struct,json,bisect
from pathlib import Path
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_IMM,CS_OP_MEM

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name=='.pdata')
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw_pd,o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
IMAGE=0x140000000

def pdata(rva):
    if rva>=IMAGE: rva-=IMAGE
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def stitch(entry, stop=None, maxb=0x800):
    w=pdata(entry)
    if stop is None:
        stop=entry+maxb if not w else min(entry+maxb, w[1]+0x40)
    raw=pe.read_rva(entry, stop-entry) or b''
    ins=list(cs.disasm(raw, entry))
    targets=set()
    for i in ins:
        if i.mnemonic.startswith('j') and i.operands and i.operands[0].type==CS_OP_IMM:
            t=i.operands[0].imm
            if entry<=t<stop: targets.add(t)
    last=max([entry]+list(targets))
    out=[]
    for i in ins:
        if i.address>=stop: break
        if i.mnemonic=='int3' and out and out[-1].mnemonic in ('ret','jmp') and i.address>last:
            break
        out.append(i)
        if i.mnemonic=='ret' and i.address>=last:
            break
    text='\n'.join(f'{hex(i.address)}  {i.mnemonic} {i.op_str}' for i in out)
    return text,out

def callers(target, limit=80):
    textsec=next(s for s in pe.sections if s.name=='.text')
    data=pe.data[textsec.raw_ptr:textsec.raw_ptr+textsec.raw_size]
    va=textsec.virtual_address
    hits=[]; pos=0
    while True:
        i=data.find(b'\xE8',pos)
        if i<0: break
        if i+5<=len(data):
            rel=struct.unpack_from('<i',data,i+1)[0]
            at=va+i
            dest=(at+5+rel)&0xffffffff
            if dest==target:
                w=pdata(at)
                hits.append({'at':hex(at),'func':hex(w[0]) if w else None})
                if len(hits)>=limit: break
        pos=i+1
    return hits

for entry,name in [(0x15a16a0,'15a16a0'),(0x15a1a80,'15a1a80'),(0x717410,'717410'),(0xcb8e80,'cb8e80'),(0xcabbc0,'cabbc0')]:
    w=pdata(entry)
    print(name, 'pdata', None if not w else (hex(w[0]),hex(w[1]),w[1]-w[0]))
    stop=None
    if w and w[1]-w[0]>=16:
        stop=w[1]+16
    text,out=stitch(entry, stop, 0x600)
    Path(f'research/_t175_clip_{name}.txt').write_text(text+'\n',encoding='utf-8')
    cs_list=callers(entry)
    funcs=sorted({c['func'] for c in cs_list if c['func']})
    print(name, 'ins', len(out), 'end', hex(out[-1].address) if out else None,
          'calls', sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='call'}),
          'caller_n', len(cs_list), 'funcs', funcs[:20])

print('\n===== 15a16a0 text =====')
print(Path('research/_t175_clip_15a16a0.txt').read_text(encoding='utf-8'))
