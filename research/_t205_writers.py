from _t205_common import *
from _t205_flow import walk_flow
import re
from capstone.x86 import X86_OP_MEM
from capstone import CS_AC_WRITE
x=Runtime()
try:
 before=x.guard();lo,n=x.sections['.text'];raw=x.code(lo,n);x.cs.detail=True
 patterns=[rb'[\x88\xc6\x80][\x40-\x7f][\x1e\x2e]',rb'[\x88\xc6\x80][\x80-\xbf][\x1e\x2e]\x00\x00\x00',rb'\x0f[\x90-\x9f][\x40-\x7f][\x1e\x2e]',rb'\x66[\x89\xc7\x81\x83][\x40-\x7f][\x1d\x2d]',rb'[\x88\xc6\x80][\x44\x4c\x54\x5c\x64\x6c\x74\x7c].[\x1e\x2e]',rb'\x66[\x89\xc7\x81\x83][\x44\x4c\x54\x5c\x64\x6c\x74\x7c].[\x1d\x2d]']
 hits=sorted(set(lo+m.start()for pat in patterns for m in re.finditer(pat,raw,re.S)));rows={};unbound=[]
 for hit in hits:
  j=bisect.bisect_right(x.starts,hit)-1
  if j<0 or not x.fns[j][0]<=hit<x.fns[j][1]:unbound.append(hex(hit));continue
  st,en,_=x.fns[j];rows[st]=(en,rows.get(st,(en,[]))[1]+[hit])
 found=[]
 for st,(en,hs)in sorted(rows.items()):
  code=x.code(st,en-st);ins=list(x.cs.disasm(code,st))
  for k,i in enumerate(ins):
   if not any(i.address<=h<i.address+i.size for h in hs):continue
   ops=[o for o in i.operands if o.type==X86_OP_MEM and o.access&CS_AC_WRITE and(o.mem.disp,o.size)in((0x1e,1),(0x2e,1),(0x1d,2),(0x2d,2))]
   if not ops:continue
   found.append({'site':hex(i.address),'pdata_start':hex(st),'pdata_end':hex(en),'instruction':f'{i.mnemonic} {i.op_str}','context':[f'{v.address:x} {v.mnemonic} {v.op_str}'for v in ins[max(0,k-6):k+7]],'fragment_sha256':hashlib.sha256(code).hexdigest()})
 v70=[]
 for op in list(range(0x90,0x98))+list(range(0xa0,0xa8)):
  pat=bytes([0xff,op,0x70,0,0,0]);p=0
  while True:
   p=raw.find(pat,p)
   if p<0:break
   a=lo+p;j=bisect.bisect_right(x.starts,a)-1
   if j>=0 and x.fns[j][0]<=a<x.fns[j][1]:
    st,en,_=x.fns[j];ins=list(x.cs.disasm(x.code(st,en-st),st))
    for k,i in enumerate(ins):
     if i.address<=a<i.address+i.size and i.mnemonic in('call','jmp')and'+ 0x70]'in i.op_str:v70.append({'site':hex(i.address),'fragment':hex(st),'context':[f'{z.address:x} {z.mnemonic} {z.op_str}'for z in ins[max(0,k-7):k+7]]})
   p+=1
 out={'scope':'native loaded-text opcode-prefilter + pdata-boundary decode; byte1E/2E and word1D/2D only. Not exhaustive for aliases, bulk/vector writes, unknown leaf spans, indirect calls. No class/field semantics from offsets alone.','base':hex(x.base),'text_sha256':hashlib.sha256(raw).hexdigest(),'raw_hits':len(hits),'unbound_hits':unbound,'write_sites':found,'v70_disp32_sites':v70,'remove_flow':walk_flow(x.cs,x.code(0x147d480,0x400),0x147d480),'guard_after':x.guard()};assert out['guard_after']==before;(R/'research/t205_global_flag_write_candidates.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('COUNTS',len(hits),len(unbound),len(found),'V70_DISP32',len(v70));print('SITES',[(z['site'],z['pdata_start'],z['instruction'])for z in found]);print('V70',json.dumps(v70,indent=2));print('REMOVE','\n'.join(out['remove_flow']['asm']))
finally:x.close()
