from _t203_common import *
x=Runtime()
try:
 b=x.guard();out=[]
 for lo,hi in((0x1330000,0x1490000),(0xcc0000,0xd00000)):
  raw=x.code(lo,hi-lo)
  for mr in range(0x90,0x98):
   needle=bytes([0xff,mr])+struct.pack('<I',0x148);p=0
   while True:
    p=raw.find(needle,p)
    if p<0:break
    f=x.clip(lo+p);keys=[k for k,s in enumerate(f['asm'])if s.startswith(f'{lo+p:x} call ')and ' + 0x148]'in s]
    for k in keys:out.append({'site':hex(lo+p),'function':f['start'],'context':f['asm'][max(0,k-10):k+10]})
    p+=1
 assert x.guard()==b;(R/'research/t203_strength_virtual148_candidates.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
