from __future__ import annotations
import os,sys,json,struct,bisect
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from pe import PE
from mem import Proc,find_pid
from gamestate import _rtti_name_from_vtable

def demangle(n):
    if not n: return None
    if n.startswith('.?A') and n.endswith('@@'):
        return n[4:-2].split('@')[0]
    return n
def cls(pe,P,addr):
    if not addr or not (0x10000000000 < addr < 0x7fffffffffff): return None
    b=P.try_read(addr,8)
    if not b or len(b)<8: return None
    vt=struct.unpack_from('<Q',b)[0]
    if not (P.base<=vt<P.base+P.image_size): return None
    try: return demangle(_rtti_name_from_vtable(pe,vt-P.base))
    except Exception: return None
def try_u64(P,a):
    b=P.try_read(a,8)
    return struct.unpack('<Q',b)[0] if b and len(b)==8 else None
def try_i32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<i',b)[0] if b and len(b)==4 else None

pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
print('a22c88 dest', hex(0xa22c8f+0x29baa21))

text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address
pd=next(s for s in pe.sections if s.name=='.pdata')
praw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',praw,o)[:2] for o in range(0,len(praw)-11,12)]
starts=[x[0] for x in functions]
def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

hits=[]
i=0
n=len(blob)
while i+6<=n and len(hits)<100:
    # locate opcode 80
    if blob[i]==0x80:
        start=i
        rex=False
        if i>=1 and blob[i-1] in range(0x40,0x50):
            start=i-1
            rex=True
        modrm=blob[i+1]
        if (modrm & 0x38)==0x38 and (modrm & 0xC0)==0x40:
            has_sib=((modrm & 7)==4)
            disp_i=i+3 if has_sib else i+2
            if disp_i+1<n and blob[disp_i]==0x10:
                imm=blob[disp_i+1]
                if imm in (0,1,2,3,4):
                    site=va+start
                    f=fn_of(site)
                    hits.append({'at':hex(site),'func':hex(f[0]) if f else None,'imm':imm,'sib':has_sib})
        i+=1
        continue
    i+=1
print('hits', len(hits))
for h in hits:
    print(h)

P=Proc(find_pid('hoi4.exe'))
try:
    cmap=try_u64(P, P.base+0x33e7700)
    print('CMap', hex(cmap), cls(pe,P,cmap))
    raw=P.try_read(cmap+0x200, 0x100) or b''
    print('CMap+0x200 qwords:')
    for o in range(0,len(raw)-7,8):
        q=struct.unpack_from('<Q',raw,o)[0]
        print(hex(0x200+o), hex(q), cls(pe,P,q), 'i32s', struct.unpack_from('<ii',raw,o))
    land_arr=try_u64(P,cmap+0x238)
    seas=[]
    buf=P.try_read(land_arr, 14000*4) or b''
    for pid in range(min(len(buf)//4,14000)):
        v=struct.unpack_from('<i',buf,pid*4)[0]
        if v==-1:
            seas.append(pid)
    print('sea ids count', len(seas), 'first30', seas[:30], 'last10', seas[-10:])
    Path('research/t180_cmp_b10.json').write_text(json.dumps({
        'a22c88_dest':hex(0xa22c8f+0x29baa21),'hits':hits,
        'sea_count_14000':len(seas),'seas_head':seas[:40],'seas_tail':seas[-20:]
    },indent=2),encoding='utf-8')
finally:
    P.close()
