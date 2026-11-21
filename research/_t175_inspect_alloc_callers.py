
"""Disassemble high-value parents around their call [reg+0x10] / 1092b70 / 1095b00 sites."""
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

def window(at, before=40, after=16):
    start=max(0, at-before*6)  # rough
    # better: disasm from at-80 bytes
    raw=pe.read_rva(at-80, 80+48) or b''
    ins=list(cs.disasm(raw, at-80))
    lines=[]
    for i in ins:
        if at-80<=i.address<=at+48:
            mark=' <<<' if i.address==at else ''
            lines.append(f'{hex(i.address)}  {i.mnemonic} {i.op_str}{mark}')
    return lines

# sites to inspect
sites={
    '1596b50_slot2':0x1596e99,
    '1596b50_maybe2':0x1596a71,  # 1596740
    '159a810_a':0x159ac48,
    '4ba620':0x4baa6f,
    '149bea0':0x149c44e,
    '13f9fb0_1092b70':0x13fa96b,
    '16502c0':0x1650616,
    '107e8d0_a':0x107ea74,
    '107e8d0_b':0x107eb45,
}
# also all 159a810 sites
for at in (0x159ac48,0x159ac6b,0x159acd1,0x159acee,0x159ada7,0x159adc5,0x159adc4):
    sites[f'159a810_{hex(at)}']=at

out={}
for name,at in sites.items():
    w=pdata(at)
    lines=window(at)
    rec={'at':hex(at),'func':hex(w[0]) if w else None,'pdata_end':hex(w[1]) if w else None,'lines':lines}
    out[name]=rec
    print('='*70, name, 'func', rec['func'])
    print('\n'.join(lines))
    print()

Path('research/t175_alloc_caller_windows.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('done')
