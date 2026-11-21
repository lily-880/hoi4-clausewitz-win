from __future__ import annotations
import os,sys,json,struct,bisect
from pathlib import Path
from collections import Counter
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
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
def try_u32(P,a):
    b=P.try_read(a,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None

pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name=='.pdata')
praw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',praw,o)[:2] for o in range(0,len(praw)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address
def fn_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None
def lea_xrefs(dest):
    hits=[]; i=0; n=len(blob)
    while i+7<=n:
        b0=blob[i]
        if b0 in (0x48,0x4c,0x49,0x4d) and i+1<n and blob[i+1]==0x8d:
            modrm=blob[i+2]
            if (modrm & 0xC7)==0x05:
                rel=struct.unpack_from('<i',blob,i+3)[0]
                if va+i+7+rel==dest:
                    hits.append(va+i)
        i+=1
    return hits
def disasm(start,end,maxb=0x2000):
    size=min(max(end-start,0),maxb)
    raw=pe.read_rva(start,size) or b''
    out=[]
    for ins in cs.disasm(raw,start):
        out.append(f"0x{ins.address:x}  {ins.mnemonic} {ins.op_str}".strip())
        if ins.address+ins.size>=start+size: break
    return out

for name,dest in {'river':0x29bb790,'river_large':0x29bb798,'adjacencies_token':0x2b47d70,'inland_sea':0x2b47d98,
                  'ProvEdges':0x2a54610,'CalculateAdjacencies':0x29bb558,'is_coastal_bitmap':0x29bba20}.items():
    xs=lea_xrefs(dest)
    print(name, [hex(x) for x in xs], 'funcs', [hex(fn_of(x)[0]) if fn_of(x) else None for x in xs])

# disassemble ef2c80 around cmp 1/2
for fn,end in ((0xef2c80,0xef2fc0),(0xef2fc0,0xef31ee)):
    f=fn_of(fn)
    end=f[1] if f else end
    lines=disasm(fn,end,0x800)
    Path(f'research/_t180_clip_{hex(fn)}.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('====', hex(fn), 'ins', len(lines), 'end', hex(end) if isinstance(end,int) else end)
    # print around cmp 1/2 and any strings
    for l in lines:
        if any(k in l for k in ('0x10','call ','lea r','rip','cmp byte','test ','je ','jne ','+ 8','0x30')):
            print(l)

# lea strings in ef2c80
raw=pe.read_rva(0xef2c80, 0x400) or b''
print('--- lea strings ef2c80 ---')
for ins in cs.disasm(raw,0xef2c80):
    if ins.mnemonic=='lea' and 'rip' in ins.op_str:
        dest=ins.address+ins.size+ins.operands[1].mem.disp
        b=pe.read_rva(dest,80) or b''
        z=b.find(b'\x00')
        if z>=3 and all(32<=c<127 for c in b[:z]):
            print(hex(ins.address), b[:z].decode())
