
"""Disassemble the post-140b9c0 produced/stock path in 15aa9c0. File-only, no process attach."""
import sys, struct, json, bisect
from pathlib import Path
sys.path.insert(0, 'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM

EXE = r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe = PE(EXE)
pd = next(s for s in pe.sections if s.name == '.pdata')
raw_pd = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
functions = [struct.unpack_from('<III', raw_pd, o)[:2] for o in range(0, len(raw_pd) - 11, 12)]
starts = [x[0] for x in functions]
cs = Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail = True

def pdata(rva):
    i = bisect.bisect_right(starts, rva) - 1
    if i < 0: return None
    s,e = functions[i]
    return (s,e) if s <= rva < e else None

def until_end(entry, max_bytes=0x800):
    raw = pe.read_rva(entry, max_bytes) or b''
    ins = list(cs.disasm(raw, entry))
    targets=set()
    for i in ins:
        if i.mnemonic.startswith('j') and i.mnemonic!='jmp' and i.operands and i.operands[0].type==CS_OP_IMM:
            t=i.operands[0].imm
            if entry <= t < entry+max_bytes:
                targets.add(t)
        if i.mnemonic=='jmp' and i.operands and i.operands[0].type==CS_OP_IMM:
            t=i.operands[0].imm
            if entry <= t < entry+max_bytes:
                targets.add(t)
    last=entry
    for t in targets:
        last=max(last,t)
    out=[]
    for i in ins:
        # stop if we hit a new function prologue after a ret and after last target, with int3 padding
        if i.mnemonic=='int3' and out and out[-1].mnemonic in ('ret','jmp') and i.address > last:
            break
        out.append(i)
        if i.mnemonic=='ret' and i.address >= last:
            # peek if more int3 then a new function; stop
            break
    # If first ret is before last branch target (early-exit path), continue
    # The loop above breaks at first ret >= last, good.
    # But if we broke at first ret that was BEFORE last because I used break only when >= last... good.
    text='\n'.join(f'{hex(i.address)}  {i.mnemonic} {i.op_str}' for i in out)
    return {
        'entry':hex(entry),
        'pdata':({'start':hex(pdata(entry)[0]),'end':hex(pdata(entry)[1])} if pdata(entry) else None),
        'end':hex(out[-1].address) if out else None,
        'ins_count':len(out),
        'calls':sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='call'}),
        'text':text,
    }

def find_callers(target, limit=80):
    textsec=next(s for s in pe.sections if s.name=='.text')
    data=pe.data[textsec.raw_ptr:textsec.raw_ptr+textsec.raw_size]
    va=textsec.virtual_address
    hits=[]
    pos=0
    while True:
        i=data.find(b'\xE8', pos)
        if i<0: break
        if i+5<=len(data):
            rel=struct.unpack_from('<i', data, i+1)[0]
            at=va+i
            dest=(at+5+rel)&0xffffffff
            if dest==target:
                w=pdata(at)
                hits.append({'at':hex(at),'func':hex(w[0]) if w else None})
                if len(hits)>=limit: break
        pos=i+1
    return hits

targets = [
    0x15a55e0, 0x15a5c80, 0xc55aa0, 0xedb2a0, 0x1095b00,
    0xbd8e40, 0xc07bf0, 0x140b810, 0x10925a0, 0xc2dad0,
    0x1095760, 0x1d6ed0, 0xd6da70,
]
index={}
for t in targets:
    # pick size: 15a55e0/15a5c80 likely medium-large
    d=until_end(t, 0x1000 if t in (0x15a55e0,0x15a5c80,0xedb2a0,0x1095b00,0x140b810) else 0x400)
    Path(f'research/_t174_func_{hex(t)}.txt').write_text(d['text']+'\n', encoding='utf-8')
    rec={k:d[k] for k in d if k!='text'}
    rec['path']=f'research/_t174_func_{hex(t)}.txt'
    rec['callers']=find_callers(t)
    rec['caller_funcs']=sorted({c['func'] for c in rec['callers'] if c['func']})
    rec['caller_count']=len(rec['callers'])
    index[hex(t)]=rec
    print(hex(t), 'pdata', rec['pdata'], 'ins', rec['ins_count'], 'end', rec['end'],
          'calls', rec['calls'][:12], 'callers', rec['caller_count'], 'funcs', rec['caller_funcs'][:12])

Path('research/t174_produced_path_disasm_index.json').write_text(json.dumps(index, indent=2), encoding='utf-8')
print('done')
