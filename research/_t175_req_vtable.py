
"""Map CReinforcementRequest vtables at 0x2a4b768 and 0x2a4b7a0. File-only."""
import sys,struct,json,bisect
from pathlib import Path
sys.path.insert(0,'calling')
from pe import PE
from gamestate import _rtti_name_from_vtable

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
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

def rtti(vt):
    try: return typenames(_rtti_name_from_vtable(pe,vt))
    except Exception as e: return str(e)

def dump_vt(vr, n=64):
    raw=pe.read_rva(vr, n*8) or b''
    slots=[]
    for i in range(0,len(raw)-7,8):
        v=struct.unpack_from('<Q',raw,i)[0]
        w=pdata(v) if v<0x4000000 else None
        rec={'i':i//8,'off':hex(i),'val':hex(v),'pdata_start':hex(w[0]) if w else None,'in_pdata':bool(w),
             'interesting': v in {0x15a92f0,0x15a8cf0,0x15a8f00,0x15a85da,0x15a26f0,0x15aa9c0,0x15a5c80,0x15a55e0,0x1092b70,0xee1250}}
        # stop after a long run of non-code if we already have some code slots
        slots.append(rec)
        if i>=16 and not w and v>0x4000000:
            # maybe still a ptr; don't stop immediately
            pass
        # typical vtable ends when we hit another COL/vtable (rdata ptr) after code
    # trim trailing non-code after last code
    last=0
    for s in slots:
        if s['in_pdata'] or s['interesting']:
            last=s['i']
    slots=slots[:last+3]
    return {'vtable':hex(vr),'rtti':rtti(vr),'slots':slots,
            'hits':[s for s in slots if s['val'] in ('0x15a92f0','0x15a8cf0','0x15a8f00','0x15a85da') or s['interesting']]}

vts=[dump_vt(0x2a4b768), dump_vt(0x2a4b7a0), dump_vt(0x2a4b768-8, 8)]  # also peek before
# also check 32-bit rdata hits: are they unaligned?
for rva in (0x2fcfa10,0x2fcfa48,0x2fcfa88,0x2fcfa98):
    raw=pe.read_rva(rva-16, 48) or b''
    print('context', hex(rva), raw.hex())

print('VT 0x2a4b768 rtti', vts[0]['rtti'], 'n', len(vts[0]['slots']))
for s in vts[0]['slots']:
    mark=' **' if s['interesting'] or s['val']=='0x15a92f0' else ''
    print(f"  [{s['i']:2d}] +{s['off']} {s['val']} pdata={s['pdata_start']}{mark}")
print('HITS', vts[0]['hits'])
print('\nVT 0x2a4b7a0 rtti', vts[1]['rtti'], 'n', len(vts[1]['slots']))
for s in vts[1]['slots']:
    mark=' **' if s['interesting'] or s['val']=='0x15a92f0' else ''
    print(f"  [{s['i']:2d}] +{s['off']} {s['val']} pdata={s['pdata_start']}{mark}")

Path('research/t175_CReinforcementRequest_vtables.json').write_text(json.dumps({'primary':vts[0],'secondary_plus18':vts[1]},indent=2),encoding='utf-8')
print('done')
