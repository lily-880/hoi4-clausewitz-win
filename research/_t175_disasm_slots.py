
"""Disassemble CReinforcementRequest vtable slots 0,1,3,4 and find call [reg+0x10] in related funcs."""
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

def stitch(entry, stop=None):
    if stop is None:
        w=pdata(entry)
        if w and w[1]-w[0]>=16:
            # continue a bit after pdata if fragments
            stop=w[1]+0x80
        else:
            stop=entry+0x400
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

# Known pdata for some
jobs={
    '15a50d0': (0x15a50d0, 0x15a5180),
    '15a8c20': (0x15a8c20, 0x15a8c70),
    '15a7ba0': (0x15a7ba0, 0x15a7c40),
    'b2ada0':  (0xb2ada0, 0xb2ae80),
    '1643cd0': (0x1643cd0, 0x1643d80),
    '15a8c70': (0x15a8c70, 0x15a8cd0),
    '15a93d0': (0x15a93d0, 0x15a9440),
}
index={}
for name,(entry,stop) in jobs.items():
    w=pdata(entry)
    print(name, 'pdata', None if not w else (hex(w[0]),hex(w[1]),w[1]-w[0]))
    # if pdata is short, still stitch to stop but clip at ret
    text,out=stitch(entry, stop)
    Path(f'research/_t175_clip_{name}.txt').write_text(text+'\n',encoding='utf-8')
    calls=sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='call'})
    print(name, 'ins', len(out), 'end', hex(out[-1].address) if out else None, 'calls', calls)
    index[name]={'pdata':({'start':hex(w[0]),'end':hex(w[1])} if w else None),
                 'ins':len(out),'end':hex(out[-1].address) if out else None,'calls':calls,
                 'path':f'research/_t175_clip_{name}.txt'}

# Search selected functions for call qword ptr [reg+0x10]
search_funcs=[0x15aa9c0,0x15a5c80,0x15a8c20,0x15a8cf0,0x15a8f00,0x15a55e0,0x13f9fb0,0xce8c20,
              0x15a85da,0xcd5d70,0xee1250,0x15a9440,0x15a99b0,0x15a9f50]
# also scan a range 0x15a5000-0x15ab400 for "call qword ptr [reg + 0x10]"
raw=pe.read_rva(0x15a4e00, 0x15ac000-0x15a4e00) or b''
ins=list(cs.disasm(raw, 0x15a4e00))
virt=[]
for i in ins:
    if i.mnemonic=='call' and 'qword ptr' in i.op_str and '+ 0x10]' in i.op_str:
        w=pdata(i.address)
        virt.append({'at':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'func':hex(w[0]) if w else None})
print('\ncall [reg+0x10] in 15a4e00-15ac000:', len(virt))
for v in virt:
    print(' ', v)

Path('research/t175_slot_funcs.json').write_text(json.dumps({'slots':index,'virt_calls_15a':virt},indent=2),encoding='utf-8')
print('done')
