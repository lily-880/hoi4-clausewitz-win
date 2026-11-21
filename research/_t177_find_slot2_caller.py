
import sys,struct,json,bisect
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

IMAGE=0x140000000
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

def clip(start,end,cap=0x1000):
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

# --- precise qword [reg+0xf78] ---
# 48/4C 8B /r with mod=2 disp32, or 48/4C 8D (lea)
# encoding: REX 8B ModRM [SIB] disp32
# ModRM mod=10 (0x80-0xBF but specifically top bits 10), and if r/m=4 then SIB
loads=[]
for rex in (0x48,0x4C,0x49,0x4D):  # rex.w variants
    for op in (0x8B,0x8D,0x89):  # mov r,m / lea / mov m,r
        # without SIB: ModRM in 0x80-0xBF except r/m==4
        for modrm in range(0x80,0xC0):
            if (modrm & 7)==4:
                continue
            pat=bytes([rex,op,modrm,0x78,0x0F,0x00,0x00])
            start=0
            while True:
                j=blob.find(pat,start)
                if j<0: break
                rva=va+j
                f=fn_of(rva)
                ins=list(cs.disasm(blob[j:j+7], rva))
                asm=ins[0].mnemonic+' '+ins[0].op_str if ins else 'undecoded'
                loads.append({'rva':hex(rva),'asm':asm,'func':hex(f[0]) if f else None,'kind':hex(op),'rex':hex(rex)})
                start=j+1
        # with SIB: ModRM r/m=4, e.g. 0x84
        for modrm in (0x84,0x8C,0x94,0x9C,0xA4,0xAC,0xB4,0xBC):
            if op!=0x8B and op!=0x8D and op!=0x89: continue
            # SIB is one extra byte; we cannot include unknown SIB in pattern easily.
            # Scan REX OP ModRM ?? 78 0F 00 00
            pat_prefix=bytes([rex,op,modrm])
            start=0
            while True:
                j=blob.find(pat_prefix,start)
                if j<0 or j+8>len(blob): break
                if blob[j+4:j+8]==b'\x78\x0f\x00\x00':
                    rva=va+j
                    f=fn_of(rva)
                    ins=list(cs.disasm(blob[j:j+8], rva))
                    asm=ins[0].mnemonic+' '+ins[0].op_str if ins else 'undecoded'
                    loads.append({'rva':hex(rva),'asm':asm,'func':hex(f[0]) if f else None,'kind':'sib-'+hex(op),'rex':hex(rex)})
                start=j+1

# unique funcs for +0xf78 qword
f78_funcs=defaultdict(list)
for h in loads:
    f78_funcs[h['func'] or 'none'].append(h)

# for each such func, see call [reg+0x10] and other interesting calls
interesting=[]
for fhex, hs in f78_funcs.items():
    if fhex=='none':
        continue
    f=int(fhex,16)
    w=fn_of(f)
    end=w[1] if w else f+0x800
    lines=clip(f,end,0x4000)
    textl='\n'.join(lines)
    rec={
        'func':fhex,'size':(end-f),'n_f78':len(hs),'f78':hs,
        'call_slot10':[l for l in lines if l.split('  ',1)[-1].startswith('call qword ptr [') and '+ 0x10]' in l],
        'call_slot8':[l for l in lines if l.split('  ',1)[-1].startswith('call qword ptr [') and '+ 8]' in l],
        'has_cb8e80':'0xcb8e80' in textl,
        'has_15a16a0':'0x15a16a0' in textl,
        'has_15a93d0':'0x15a93d0' in textl,
        'has_717400':'0x717400' in textl,
        'has_717410':'0x717410' in textl,
        'has_10948a0':'0x10948a0' in textl,
        'has_1092b70':'0x1092b70' in textl,
    }
    if rec['call_slot10'] or rec['has_cb8e80'] or rec['has_15a16a0'] or rec['has_15a93d0'] or rec['has_1092b70']:
        interesting.append(rec)
        Path(f'research/_t177_clip_f78_{fhex}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

print('qword +0xf78 hits', len(loads), 'funcs', len(f78_funcs))
for f,hs in sorted(f78_funcs.items(), key=lambda x: int(x[0],16) if x[0]!='none' else 0):
    print(' F78Q', f, 'n', len(hs), 'eg', hs[0]['asm'])
print('interesting', json.dumps(interesting,indent=2)[:4000])

# E8 callers of slot1 15a8c70, cabbc0, 15a1a80, 15a92c0
e8map={}
for t,n in ((0x15a8c70,'15a8c70'),(0xcabbc0,'cabbc0'),(0x15a1a80,'15a1a80'),(0x15a92c0,'15a92c0'),
            (0x15a7c40,'15a7c40_status_slot4'),(0x15a6450,'15a6450_status_slot5')):
    h=e8_callers(t)
    e8map[n]={'count':len(h),'funcs':sorted({x['func'] for x in h if x['func']}),'sites':h}
    print('E8', n, 'count', len(h), 'funcs', e8map[n]['funcs'])

# preferred-base hits for 15a8c70 and 15a92c0 (already 2 for 15a92c0)
def find_pref(rva):
    needle=struct.pack('<Q', IMAGE+rva)
    hits=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        start=0
        while True:
            j=blob.find(needle,start)
            if j<0: break
            if j%8==0:
                hits.append({'section':s.name,'rva':hex(s.virtual_address+j)})
            start=j+8
    return hits

pref={
    '15a8c70':find_pref(0x15a8c70),
    '15a92c0':find_pref(0x15a92c0),
    '15a93d0':find_pref(0x15a93d0),
}

Path('research/t177_f78_qword_and_e8.json').write_text(json.dumps({
    'f78_loads':loads,
    'f78_funcs':{k:v for k,v in f78_funcs.items()},
    'interesting':interesting,
    'e8':e8map,
    'pref':pref,
},indent=2),encoding='utf-8')
print('pref', pref)
