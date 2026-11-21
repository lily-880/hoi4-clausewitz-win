
"""Dump rdata vtables around 15a92f0 slots and resolve 15a26f0 lea targets. File-only."""
import sys,struct,json,bisect
from pathlib import Path
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_IMM
from gamestate import _rtti_name_from_vtable

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name=='.pdata')
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw_pd,o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]

def pdata(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def typenames(s):
    if not s: return None
    if s.startswith('.?AV') and s.endswith('@@'): return s[4:-2]
    if s.startswith('.?AU') and s.endswith('@@'): return s[4:-2]
    return s

def rtti(vt_rva):
    try:
        return typenames(_rtti_name_from_vtable(pe, vt_rva))
    except Exception as e:
        return f'err:{e}'

def read_qwords(rva, n):
    raw=pe.read_rva(rva, n*8) or b''
    out=[]
    for i in range(0,len(raw)-7,8):
        v=struct.unpack_from('<Q',raw,i)[0]
        out.append(v)
    return out

# dump a wide window around 0x2fcf900 .. 0x2fcfc00
base=0x2fcf800
vals=read_qwords(base, 0x400//8)
# find runs that look like function-pointer vtables (many values in .text range)
rows=[]
for i,v in enumerate(vals):
    rva=base+i*8
    rec={'rva':hex(rva),'val':hex(v) if v<0x100000000 else hex(v)}
    w=pdata(v) if v<0x100000000 else None
    if w:
        rec['func']=hex(w[0]); rec['as_func']=hex(v)
    # RTTI complete-object locator usually sits just before vtable; if this qword is a vtable start,
    # the previous qword might be col pointer in image
    rec['rtti']=None
    rows.append(rec)

# Identify likely vtable starts: qwords that are code pointers AND previous qword is not code
# Also try rtti at each candidate
candidates=[]
for i,v in enumerate(vals):
    if v>0x1000 and v<0x3000000 and pdata(v):
        prev=vals[i-1] if i else 0
        # vtable start often has prev as a pointer into .rdata (COL)
        prev_is_code=bool(prev>0x1000 and prev<0x3000000 and pdata(prev))
        if not prev_is_code:
            rva=base+i*8
            name=rtti(rva)
            candidates.append({'vtable':hex(rva),'first':hex(v),'rtti':name})

print('CANDIDATE VTABLES in window:')
for c in candidates:
    print(' ',c)

# specifically slots of 15a92f0
print('\n15a92f0 slot contexts:')
for hit in (0x2fcfa10, 0x2fcfa48):
    # walk backward to vtable start (first non-code prev)
    # find which candidate contains this
    # dump +/- 16 slots
    slots=[]
    start=hit-16*8
    qs=read_qwords(start, 40)
    for i,v in enumerate(qs):
        addr=start+i*8
        rec={'slot_rva':hex(addr),'off_from_hit':hex(addr-hit if addr>=hit else hit-addr)+(' +' if addr>=hit else ' -'),
             'val':hex(v),'func':hex(pdata(v)[0]) if (v<0x3000000 and pdata(v)) else None,
             'is_target': v==0x15a92f0}
        slots.append(rec)
        if v==0x15a92f0:
            print('  HIT at', hex(addr), 'value', hex(v))
    Path(f'research/_t175_rdata_{hex(hit)}.json').write_text(json.dumps(slots,indent=2),encoding='utf-8')

# compute 15a26f0 lea targets
# need exact instruction lengths. Disasm those sites.
def lea_target(at):
    raw=pe.read_rva(at, 16) or b''
    ins=list(cs.disasm(raw, at))
    if not ins: return None
    i=ins[0]
    if i.operands and i.operands[0].type and len(i.operands)>1:
        # capstone: lea r15, [rip + disp]
        return {'asm':i.mnemonic+' '+i.op_str, 'size':i.size, 'next':hex(i.address+i.size)}
    return {'asm':i.mnemonic+' '+i.op_str,'size':i.size}

leas={
    '15a2872':0x15a2872,
    '15a28cb':0x15a28cb,
    '15a2904':0x15a2904,  # lea rax, [rip+0x14a8e95] stored at request+0x18
    '15a292c':0x15a292c,
    '15a293a':0x15a293a,
    '15a29e8':0x15a29e8,
}
lea_out={}
for name,at in leas.items():
    raw=pe.read_rva(at, 16) or b''
    ins=list(cs.disasm(raw, at))[0]
    # parse rip+disp from op_str or operands
    target=None
    for op in ins.operands:
        if op.type==CS_OP_IMM:
            pass
        if op.type==3:  # MEM
            # rip-relative: disp + next
            target=(ins.address+ins.size+op.mem.disp)&0xffffffffffffffff
    lea_out[name]={'asm':ins.mnemonic+' '+ins.op_str,'at':hex(at),'size':ins.size,'target':hex(target) if target is not None else None,
                   'rtti':rtti(target) if target else None}
    print('LEA', name, lea_out[name])

# Also search rdata for qwords equal to 15a92f0 as 64-bit
# (already know two)

# Map each candidate vtable: list slots as func names/RVAs, mark 15a92f0 index
vt_maps=[]
for c in candidates:
    vr=int(c['vtable'],16)
    qs=read_qwords(vr, 48)
    slots=[]
    for i,v in enumerate(qs):
        if v==0 or v>0x4000000:
            # likely end if not code and not 0?
            if i>2 and not (v<0x3000000 and pdata(v)):
                break
        w=pdata(v) if v<0x3000000 else None
        slots.append({'i':i,'off':hex(i*8),'val':hex(v),'func':hex(w[0]) if w else None,'hit':v in (0x15a92f0,0x15a8cf0,0x15a8f00,0x15a85da,0x15a26f0,0x15aa9c0)})
    # find 15a92f0
    idx=[s['i'] for s in slots if s['val']=='0x15a92f0']
    vt_maps.append({'vtable':c['vtable'],'rtti':c['rtti'],'slot_15a92f0':idx, 'n':len(slots), 'slots':slots})
    print('VT', c['vtable'], c['rtti'], '15a92f0 slots', idx, 'n', len(slots))

Path('research/t175_vtable_map.json').write_text(json.dumps({'leas':lea_out,'vtables':vt_maps,'candidates':candidates},indent=2),encoding='utf-8')
print('done')
