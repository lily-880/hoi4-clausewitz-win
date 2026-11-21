
"""Clip-to-pdata (with fragment continue until ret+int3) for 15a5c80, edb2a0, pool helpers."""
import sys, struct, json, bisect
from pathlib import Path
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
cs=Cs(CS_ARCH_X86, CS_MODE_64); cs.detail=True

def pdata(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def stitch(entry, max_bytes=0x2000, stop_before=None):
    """Start at entry. Follow consecutive pdata fragments if the first instruction
    of the next fragment is the fall-through of the previous (no int3 gap, or only
    within the same function because a branch target lands there). Stop at a ret
    that covers all in-range branch targets, or at a new independent prologue
    after int3 padding."""
    raw=pe.read_rva(entry, max_bytes) or b''
    ins=list(cs.disasm(raw, entry))
    if stop_before is None:
        # default: next pdata start after a gap of int3 or after a ret
        # We'll compute branch targets first then clip.
        stop_before = entry+max_bytes
    targets=set()
    for i in ins:
        if i.address>=stop_before: break
        if i.mnemonic.startswith('j') and i.operands and i.operands[0].type==CS_OP_IMM:
            t=i.operands[0].imm
            if entry<=t<stop_before:
                targets.add(t)
    last=max([entry]+[t for t in targets])
    out=[]
    for i in ins:
        if i.address>=stop_before:
            break
        if i.mnemonic=='int3' and out and out[-1].mnemonic in ('ret','jmp') and i.address>last:
            break
        # new function: int3 run then a typical prologue after our ret
        out.append(i)
        if i.mnemonic=='ret' and i.address>=last:
            break
    text='\n'.join(f'{hex(i.address)}  {i.mnemonic} {i.op_str}' for i in out)
    return {
        'entry':hex(entry),
        'stop_before':hex(stop_before),
        'last_target':hex(last),
        'end':hex(out[-1].address) if out else None,
        'ins_count':len(out),
        'calls':sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='call'}),
        'jmps':sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='jmp' and i.op_str.startswith('0x')}),
        'text':text,
    }

# Known solid windows
jobs = {
    '15a5c80': (0x15a5c80, 0x15a6450),  # next independent at 0x15a6450 after pdata end 0x15a6447
    'edb2a0': (0xedb2a0, 0xedb400),      # pdata end 0xedb382; allow a bit for no-pdata tail, but will clip at ret
    '1095b00': (0x1095b00, 0x1095c00),
    '10928b0': (0x10928b0, 0x1092a00),
    '1094990': (0x1094990, 0x1094b00),
    '1095120': (0x1095120, 0x1095300),
    '10955c0': (0x10955c0, 0x1095760),
    '1098540': (0x1098540, 0x1098700),
    '1098700': (0x1098700, 0x1098900),
    'c07bf0': (0xc07bf0, 0xc07d20),  # pdata end 0xc07d18
    'c55aa0': (0xc55aa0, 0xc55c00),
    '140b810': (0x140b810, 0x140b900),
    '15a55e0': (0x15a55e0, 0x15a5710),  # ends 0x15a5700, int3, next at 0x15a5710
}

# print pdata for helpers too
for name,entry,_ in [(k,v[0],v[1]) for k,v in jobs.items()]:
    w=pdata(entry)
    print(f'pdata {name} {hex(entry)} ->', None if not w else (hex(w[0]),hex(w[1]),w[1]-w[0]))

# if helper pdata is small, still use stitch with generous stop and ret clip
index={}
for name,(entry,stop) in jobs.items():
    # if pdata exists and is reasonably long, prefer pdata end as stop unless function clearly continues
    w=pdata(entry)
    d=stitch(entry, max_bytes=max(0x100, stop-entry+0x40), stop_before=stop)
    Path(f'research/_t174_clip_{name}.txt').write_text(d['text']+'\n', encoding='utf-8')
    rec={k:d[k] for k in d if k!='text'}
    rec['pdata'] = ({'start':hex(w[0]),'end':hex(w[1])} if w else None)
    rec['path']=f'research/_t174_clip_{name}.txt'
    index[name]=rec
    print(name, 'ins', rec['ins_count'], 'end', rec['end'], 'calls', rec['calls'])

Path('research/t174_produced_helpers_clip.json').write_text(json.dumps(index, indent=2), encoding='utf-8')
print('done')
