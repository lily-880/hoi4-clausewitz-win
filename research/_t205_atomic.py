from _t205_common import *
from _t205_flow import walk_flow
import re
from capstone.x86 import X86_OP_MEM
from capstone import CS_AC_WRITE
x=Runtime()
try:
 before=x.guard();lo,n=x.sections['.text'];raw=x.code(lo,n);x.cs.detail=True
 patterns=[rb'[\x86\x08\x20\x30\xfe\xf6][\x40-\x7f][\x1e\x2e]',rb'[\x86\x08\x20\x30\xfe\xf6][\x80-\xbf][\x1e\x2e]\x00\x00\x00',rb'\x0f[\xb0\xc0][\x40-\x7f][\x1e\x2e]',rb'\x66[\x87\x09\x21\x31\xff\xf7][\x40-\x7f][\x1d\x2d]']
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
 leaf_windows=[]
 for a in(0xd9cca5,0x226c98a,0x23f1d9e,0x26dae1c):
  st=a&~15;rr=x.code(st,64);leaf_windows.append({'candidate':hex(a),'heuristic_aligned_start':hex(st),'boundary_proven':False,'bytes':rr.hex(),'asm':[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in x.cs.disasm(rr,st)]})
 out={'scope':'native loaded-text opcode-prefilter + pdata-boundary decode; byte1E/2E and word1D/2D only. Not exhaustive for aliases, bulk/vector writes, unknown leaf spans, indirect calls. No class/field semantics from offsets alone.','base':hex(x.base),'text_sha256':hashlib.sha256(raw).hexdigest(),'raw_hits':len(hits),'unbound_hits':unbound,'write_sites':found,'previous_unbound_windows':leaf_windows,'guard_after':x.guard()};assert out['guard_after']==before;(R/'research/t205_atomic_flag_write_candidates.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('COUNTS',len(hits),len(unbound),len(found));print('SITES',json.dumps(found,indent=2));print('LEAF_WINDOWS',json.dumps(leaf_windows,indent=2))
finally:x.close()
