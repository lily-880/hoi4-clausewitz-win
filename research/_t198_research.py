import sys,struct,json
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from pe import PE
from gamestate import _rtti_name_from_vtable
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
p=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe');cs=Cs(CS_ARCH_X86,CS_MODE_64)
def das(a,n):
 b=p.read_rva(a,n);return [f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(b,a)]
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
out={}
for target in (0x18d6660,0x18d1150):
 hits=[]
 for width in (4,8):
  for v in (target,0x140000000+target):
   if width==4 and v>0xffffffff:continue
   needle=v.to_bytes(width,'little');start=0
   while 1:
    i=p.data.find(needle,start)
    if i<0:break
    start=i+1;a=rv(i)
    if a is None:continue
    rec={'rva':hex(a),'width':width,'value':hex(v)}
    if width==8:
     for back in range(0,0xa0,8):
      try:name=_rtti_name_from_vtable(p,a-back)
      except:name=None
      if name:
       rec.update(vt=hex(a-back),name=name,back=back);break
    hits.append(rec)
 out[hex(target)]={'hits':hits,'disasm':das(target,0x400)}
(R/'research/t198_bind_research.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
for k,v in out.items():
 print(k,'HITS',v['hits']); print('\n'.join(v['disasm'][:100]))
