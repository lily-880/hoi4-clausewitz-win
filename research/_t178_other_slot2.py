
import sys,struct,bisect,json,re
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

# E8 of key funcs
targets={
    'd71b60':0xd71b60,
    'd71810':0xd71810,
    'd6f140':0xd6f140,
    '1095760':0x1095760,
    '72f220':0x72f220,
    '15a93d0':0x15a93d0,
    'cb8e80':0xcb8e80,
    '15a16a0':0x15a16a0,
    '140b9c0':0x140b9c0,
    '140b810':0x140b810,
    'ce4fc0':0xce4fc0,
    '15a26f0':0x15a26f0,  # request ctor / need init from earlier
}
e8={}
for n,t in targets.items():
    h=e8_callers(t)
    e8[n]={'count':len(h),'funcs':sorted({x['func'] for x in h if x['func']}),'sites':h[:40]}
    print('E8', n, 'count', len(h), 'funcs', e8[n]['funcs'][:20], ('...' if len(e8[n]['funcs'])>20 else ''))

# strings of interest in rdata/data
needles=[
    b'deployment.daily',
    b'deployment.hourly',
    b'deployment.hour',
    b'gamestate.daily',
    b'gamestate.hourly',
    b'gamestate.hour',
    b'reinforcement',
    b'Reinforcement',
    b'deployment.',
    b'.hourly',
    b'.daily',
]
# scan all sections for these as cstrings; record rva and nearby xrefs later
def find_cstr(needle):
    hits=[]
    for s in pe.sections:
        data=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        start=0
        while True:
            j=data.find(needle, start)
            if j<0: break
            # extend to full string if this is a prefix
            end=data.find(b'\x00', j)
            if end<0: end=min(len(data), j+80)
            sbytes=data[j:end]
            # only if starts at string boundary (prev is 0 or section start) or mid-string mention
            prev=data[j-1] if j>0 else 0
            try:
                text=sbytes.decode('utf-8')
            except Exception:
                text=sbytes.decode('latin1','replace')
            hits.append({'section':s.name,'rva':hex(s.virtual_address+j),'s':text[:120],'at_start':prev==0})
            start=j+1
    return hits

str_hits={}
for n in [b'deployment.', b'gamestate.daily', b'gamestate.hourly', b'gamestate.hour',
          b'.hourly', b'reinforcement.', b'Reinforcement', b'hourly tick', b'hour_tick']:
    str_hits[n.decode()] = find_cstr(n)

# more precise: all strings starting with deployment. or containing reinforcement. as identifier
# print interesting
for k,v in str_hits.items():
    interesting=[h for h in v if h['at_start'] or k.startswith('deployment') or 'hour' in h['s'].lower() or 'reinforc' in h['s'].lower()]
    print('STR', k, 'n', len(v), 'show', [h['s'] for h in interesting[:25]])

Path('research/t178_e8_and_strings.json').write_text(json.dumps({
    'e8':{k:{'count':v['count'],'funcs':v['funcs'],'sites':v['sites']} for k,v in e8.items()},
    'strings':str_hits,
},indent=2,ensure_ascii=False),encoding='utf-8')
