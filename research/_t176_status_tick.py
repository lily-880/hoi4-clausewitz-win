
import sys,struct,json,bisect,re
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_MEM
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]

def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address

# precise [reg+disp] with disp in country subsystem range
WANTED={0xf60,0xf68,0xf70,0xf78,0xf80,0xf88,0xf90,0xf98,0xfa0,0xfa8}
hits=defaultdict(lambda: defaultdict(list))
# walk .text in chunks with capstone would be slow for 40MB.
# scan for disp32 78 0F 00 00 etc and decode back a few bytes
for off in WANTED:
    needle=struct.pack('<I', off)
    start=0
    while True:
        j=blob.find(needle, start)
        if j<0: break
        # try to decode instruction ending at or containing this disp
        # disp is typically at the end of a 7-byte rex.w r/m32 insn: 48 8B/8D xx disp32, or 4C 8B xx disp32
        # also 48 83 / with imm, etc. Try starts j-3, j-4, j-5, j-6, j-7
        rva=va+j
        decoded=None
        for back in range(2,9):
            if j-back<0: break
            chunk=blob[j-back:j+4]
            ins=list(cs.disasm(chunk, rva-back))
            if not ins: continue
            i=ins[0]
            # instruction must include the disp bytes
            if i.address <= rva and i.address+i.size >= rva+4:
                # check mem disp
                ok=False
                if i.op_str and (f'0x{off:x}' in i.op_str or f'+ {off}' in i.op_str):
                    ok=True
                if any(getattr(op,'type',None)==CS_OP_MEM and op.mem.disp==off for op in i.operands):
                    ok=True
                if ok:
                    decoded={'rva':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'size':i.size}
                    break
        if decoded:
            f=fn_of(i.address)
            hits[hex(off)][hex(f[0]) if f else 'none'].append(decoded)
        start=j+1

# functions that touch 0xf78 specifically with real addressing
f78_funcs=hits.get(hex(0xf78), {})
print('precise +0xf78 funcs', len(f78_funcs))
for f,ls in sorted(f78_funcs.items(), key=lambda x:int(x[0],16) if x[0]!='none' else 0):
    print(' ', f, 'n', len(ls), 'eg', ls[0]['asm'])

# functions that touch at least 3 of the subsystem offsets
func_offs=defaultdict(set)
for off,fmap in hits.items():
    for f in fmap:
        func_offs[f].add(int(off,16))
multi={f:sorted(v) for f,v in func_offs.items() if len(v)>=3}
print('funcs touching >=3 subsystem offs', len(multi))
for f,v in sorted(multi.items(), key=lambda x:int(x[0],16) if x[0]!='none' else 0):
    print(' MULTI', f, [hex(x) for x in v])

# clip 717400 callers (they may still pass status onward)
callers=json.loads(Path('research/t176_717400_callers.json').read_text(encoding='utf-8'))
for c in callers['sites']:
    f=int(c['func'],16)
    site=int(c['site'],16)
    # window around the call
    rawb=pe.data  # use pe.read_rva
    chunk=pe.read_rva(site-48, 160) or b''
    lines=[f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in Cs(CS_ARCH_X86,CS_MODE_64).disasm(chunk,site-48)]
    Path(f"research/_t176_win_717400_{c['func']}_{c['site']}.txt").write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('==== 717400 call at', c['site'], 'in', c['func'])
    print('\n'.join(lines))

Path('research/t176_subsystem_access.json').write_text(json.dumps({
    'f78_funcs':{k:v for k,v in f78_funcs.items()},
    'multi':{k:[hex(x) for x in v] for k,v in multi.items()},
    'all_off_func_counts':{off:len(fmap) for off,fmap in hits.items()},
},indent=2),encoding='utf-8')
