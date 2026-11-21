
import sys, struct, json, bisect
from pathlib import Path
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True

def pdata(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def nearby(rva,n=8):
    i=bisect.bisect_right(starts,rva)
    lo=max(0,i-3); hi=min(len(functions),i+n)
    return [(hex(s),hex(e),e-s) for s,e in functions[lo:hi]]

def stitch(entry, stop):
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
    return text, out, last

def callers(target, limit=40):
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

jobs={
    'ee1250': 0xee1250,
    '10955c0': 0x10955c0,
    '1094990': 0x1094990,
    '1092b70': 0x1092b70,
    'ed1b40': 0xed1b40,
    'cd6700': 0xcd6700,
    '10961f0': 0x10961f0,
}
index={}
for name,entry in jobs.items():
    w=pdata(entry)
    print(name, 'pdata', None if not w else (hex(w[0]),hex(w[1]),w[1]-w[0]))
    print(' nearby', nearby(entry,8)[:10])
    # stop at next clearly independent function after a generous window
    # default stop: if pdata reasonably long use pdata end + 0x40, else 0x400
    if w and (w[1]-w[0])>=32:
        stop=w[1]+0x80
    else:
        stop=entry+0x400
    # but don't go into a far next if pdata is short and next pdata is close after int3
    if w:
        # find next pdata start after this window
        i=bisect.bisect_right(starts, entry)
        # if this pdata is tiny, continue fragments until int3+new prologue: use 0x200
        if w[1]-w[0] < 64:
            stop=entry+0x300
        else:
            stop=w[1]+16
    text,out,last=stitch(entry, stop)
    Path(f'research/_t174_clip_{name}.txt').write_text(text+'\n',encoding='utf-8')
    rec={'entry':hex(entry),'pdata':({'start':hex(w[0]),'end':hex(w[1])} if w else None),
         'ins':len(out),'end':hex(out[-1].address) if out else None,
         'calls':sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='call'}),
         'caller_count':0,'caller_funcs':[]}
    cs_list=callers(entry)
    rec['caller_count']=len(cs_list)
    rec['caller_funcs']=sorted({c['func'] for c in cs_list if c['func']})
    rec['path']=f'research/_t174_clip_{name}.txt'
    index[name]=rec
    print(' ', rec['ins'], 'end', rec['end'], 'calls', rec['calls'], 'callers', rec['caller_count'], rec['caller_funcs'][:10])

Path('research/t174_ee1250_helpers.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
print('done')
