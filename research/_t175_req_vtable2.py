
"""Full CReinforcementRequest vtable with preferred image base 0x140000000, plus lea xrefs and slot functions."""
import sys,struct,json,bisect
from pathlib import Path
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_IMM,CS_OP_MEM
from gamestate import _rtti_name_from_vtable

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
IMAGE=0x140000000
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name=='.pdata')
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw_pd,o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]

def pdata(rva):
    if rva>=IMAGE: rva-=IMAGE
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def typenames(s):
    if not s: return None
    if s.startswith('.?AV') and s.endswith('@@'): return s[4:-2]
    if s.startswith('.?AU') and s.endswith('@@'): return s[4:-2]
    return s

def rtti(vt):
    try: return typenames(_rtti_name_from_vtable(pe,vt))
    except Exception as e: return str(e)

def to_rva(v):
    if IMAGE<=v<IMAGE+0x8000000: return v-IMAGE
    if v<0x8000000: return v
    return None

def dump_vt(vr, n=80):
    raw=pe.read_rva(vr, n*8) or b''
    slots=[]
    for i in range(0,len(raw)-7,8):
        v=struct.unpack_from('<Q',raw,i)[0]
        rva=to_rva(v)
        w=pdata(v) if rva is not None else None
        rec={'i':i//8,'off':hex(i),'val':hex(v),'rva':hex(rva) if rva is not None else None,
             'pdata_start':hex(w[0]) if w else None,'in_pdata':bool(w)}
        slots.append(rec)
    last=0
    for s in slots:
        if s['in_pdata']: last=s['i']
    # keep a couple after last code
    slots=slots[:last+4]
    return {'vtable':hex(vr),'rtti':rtti(vr),'slots':slots}

primary=dump_vt(0x2a4b768)
secondary=dump_vt(0x2a4b7a0)
print('PRIMARY', primary['rtti'], 'n', len(primary['slots']))
for s in primary['slots']:
    mark=''
    if s['rva'] in ('0x15a92f0','0x15a8c20','0x15a50d0','0x15a8cf0','0x15a8f00'):
        mark=' **'
    print(f"  [{s['i']:2d}] +{s['off']} rva={s['rva']} pdata={s['pdata_start']}{mark}")
print('SECONDARY', secondary['rtti'], 'n', len(secondary['slots']))
for s in secondary['slots']:
    print(f"  [{s['i']:2d}] +{s['off']} rva={s['rva']} pdata={s['pdata_start']}")

# Find RIP-relative LEAs to vtable 0x2a4b768 and 0x2a4b7a0
def find_lea(target_rva, limit=40):
    text=next(s for s in pe.sections if s.name=='.text')
    blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
    va=text.virtual_address
    hits=[]
    pos=0
    while True:
        i=blob.find(b'\x8D', pos)
        if i<0: break
        for start,inslen_base in ((i-1,7),(i,6)):
            if start<0: continue
            if start==i-1 and blob[start] not in (0x48,0x4C,0x4D,0x49):
                continue
            if i+1>=len(blob): continue
            modrm=blob[i+1]
            if (modrm & 0xC7)!=0x05: continue
            disp_at=i+2
            if disp_at+4>len(blob): continue
            inslen=7 if start==i-1 else 6
            insn_rva=va+start
            disp=struct.unpack_from('<i',blob,disp_at)[0]
            dest=(insn_rva+inslen+disp)&0xffffffff
            if dest==target_rva:
                w=pdata(insn_rva)
                hits.append({'at':hex(insn_rva),'func':hex(w[0]) if w else None})
                if len(hits)>=limit: return hits
        pos=i+1
    return hits

leas_pri=find_lea(0x2a4b768)
leas_sec=find_lea(0x2a4b7a0)
print('\nLEA to primary vtable', len(leas_pri), leas_pri)
print('LEA to secondary', len(leas_sec), leas_sec)

# Also 64-bit preferred-base immediate 0x1415a92f0 in rdata already is the vtable slot.
# Search .text for 0x1415a92f0 as imm64 (unlikely) or 0x015a92f0 leftover.

Path('research/t175_CReinforcementRequest_vtables.json').write_text(json.dumps({
    'image_base':hex(IMAGE),
    'primary':primary,'secondary_plus18':secondary,
    'lea_primary':leas_pri,'lea_secondary':leas_sec
},indent=2),encoding='utf-8')
print('done')
