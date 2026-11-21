
import sys,struct,json,bisect,os
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from mem import Proc,find_pid
from pe import PE as PE2
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
IMAGE=0x140000000
pd=next(s for s in pe.sections if s.name=='.pdata')
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
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

def find_qword(val):
    needle=struct.pack('<Q', val)
    hits=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        pos=0
        while True:
            i=blob.find(needle,pos)
            if i<0: break
            hits.append((s.name, s.virtual_address+i))
            pos=i+8
            if len(hits)>20: break
    return hits

# preferred-base function pointers
targets={
    '15a92c0': IMAGE+0x15a92c0,
    '15a93d0': IMAGE+0x15a93d0,
    '15a92f0': IMAGE+0x15a92f0,
    '15a8c20': IMAGE+0x15a8c20,
    '15a16a0': IMAGE+0x15a16a0,
}
for name,val in targets.items():
    hits=find_qword(val)
    print(name, 'abs hits', [(s,hex(r)) for s,r in hits])

# For each rdata hit, walk back to vtable start and name it
def dump_containing_vtable(hit_rva):
    # look back up to 64 slots for a COL (non-code qword then code)
    raw=pe.read_rva(hit_rva-64*8, 80*8) or b''
    base=hit_rva-64*8
    qs=[struct.unpack_from('<Q',raw,i)[0] for i in range(0,len(raw)-7,8)]
    # find start: last position <= hit where prev is not a function ptr
    hit_i=64
    start_i=hit_i
    for i in range(hit_i,0,-1):
        v=qs[i]
        prev=qs[i-1]
        rva=v-IMAGE if IMAGE<=v<IMAGE+0x8000000 else None
        prev_rva=prev-IMAGE if IMAGE<=prev<IMAGE+0x8000000 else None
        prev_is_func=bool(prev_rva and pdata(prev_rva))
        if not prev_is_func:
            start_i=i
            break
    vt=base+start_i*8
    slot=(hit_rva-vt)//8
    # dump 16 slots
    slots=[]
    for j in range(0,16):
        if start_i+j>=len(qs): break
        v=qs[start_i+j]
        rva=v-IMAGE if IMAGE<=v<IMAGE+0x8000000 else None
        slots.append({'i':j,'off':hex(j*8),'rva':hex(rva) if rva is not None else hex(v),
                      'pdata':hex(pdata(rva)[0]) if rva and pdata(rva) else None})
    return {'vtable':hex(vt),'rtti':rtti(vt),'slot_of_hit':slot,'slots':slots}

# 717410 full text
w=pdata(0x717410)
raw=pe.read_rva(0x717410, (w[1]-0x717410) if w else 0x160) or b''
ins=list(cs.disasm(raw,0x717410))
lines=[]
for i in ins:
    lines.append('%s  %s %s'%(hex(i.address),i.mnemonic,i.op_str))
    if i.mnemonic=='ret':
        break
Path('research/_t175_clip_717410.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n===== 717410 full =====')
print('\n'.join(lines))

# cb8e80: just prologue + first 80 ins and all call sites
w=pdata(0xcb8e80)
raw=pe.read_rva(0xcb8e80, min(0x600, (w[1]-0xcb8e80) if w else 0x600)) or b''
ins=list(cs.disasm(raw,0xcb8e80))
clines=[]
calls=[]
for i in ins:
    clines.append('%s  %s %s'%(hex(i.address),i.mnemonic,i.op_str))
    if i.mnemonic=='call':
        calls.append('%s  %s %s'%(hex(i.address),i.mnemonic,i.op_str))
    if i.mnemonic=='ret' and i.address>0xcb8e80+0x40:
        break
Path('research/_t175_clip_cb8e80_head.txt').write_text('\n'.join(clines[:120])+'\n',encoding='utf-8')
print('\ncb8e80 pdata', None if not w else (hex(w[0]),hex(w[1]),w[1]-w[0]), 'ins_dumped', len(clines))
print('prologue:')
print('\n'.join(clines[:50]))
print('calls:')
print('\n'.join(calls))

# vtable maps
vt_maps={}
for name,val in targets.items():
    hits=find_qword(val)
    vt_maps[name]=[]
    for sec,rva in hits:
        if sec=='.rdata':
            info=dump_containing_vtable(rva)
            vt_maps[name].append({'hit':hex(rva),'section':sec,**{k:info[k] for k in info}})
            print('\nVT for', name, 'at', hex(rva), 'vtable', info['vtable'], 'rtti', info['rtti'], 'slot', info['slot_of_hit'])
            for s in info['slots']:
                mark=' **' if s['i']==info['slot_of_hit'] else ''
                print('  ', s, mark)

Path('research/t175_offered_vtables.json').write_text(json.dumps({'717410_path':'research/_t175_clip_717410.txt','vtables':vt_maps},indent=2),encoding='utf-8')
print('static done')
