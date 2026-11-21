from _t205_common import *
from capstone.x86 import X86_OP_MEM,X86_REG_RIP
x=Runtime()
try:
 b=x.guard();lo,n=x.sections['.text'];raw=x.code(lo,n);cs=x.cs;cs.detail=True;hits=[]
 for op in list(range(0x50,0x58))+list(range(0x60,0x68)):
  key=bytes([0xff,op,0x70]);p=0
  while True:
   p=raw.find(key,p)
   if p<0:break
   hits.append(lo+p);p+=1
 cache={};out=[];unbound=[]
 for a in sorted(set(hits)):
  j=bisect.bisect_right(x.starts,a)-1
  if j<0 or not x.fns[j][0]<=a<x.fns[j][1]:unbound.append(hex(a));continue
  st,en,_=x.fns[j]
  if st not in cache:
   ins=list(cs.disasm(x.code(st,en-st),st));literals=[]
   for z in ins:
    if z.mnemonic!='lea':continue
    for o in z.operands:
     if o.type!=X86_OP_MEM or o.mem.base!=X86_REG_RIP:continue
     pa=z.address+z.size+o.mem.disp
     if not 0<pa<x.pr.image_size-160:continue
     s=x.code(pa,160).split(b'\0')[0]
     if b'combat'in s.lower():
      try:literals.append({'instruction':hex(z.address),'rva':hex(pa),'value':s.decode('ascii')})
      except UnicodeDecodeError:pass
   cache[st]=(ins,literals)
  ins,literals=cache[st]
  for k,i in enumerate(ins):
   if i.address<=a<i.address+i.size and i.mnemonic in('call','jmp')and' + 0x70]'in i.op_str:out.append({'site':hex(i.address),'pdata_fragment':hex(st),'combat_literals':literals,'context':[f'{z.address:x} {z.mnemonic} {z.op_str}'for z in ins[max(0,k-15):k+13]]})
 d={'scope':'global loaded-text short-displacement vcall70 pattern candidates; not semantic receiver binding or exhaustive alias/callback coverage','raw_hits':len(hits),'unbound_hits':unbound,'candidates':out,'guard_after':x.guard()};assert d['guard_after']==b;(R/'research/t205_v70_global_dispatch_candidates.json').write_text(json.dumps(d,indent=2),encoding='utf8');print('TOTAL',len(hits),len(out),len(unbound));print('COMBAT-LITERAL MATCHES',json.dumps([z for z in out if z['combat_literals']],indent=2))
finally:x.close()
