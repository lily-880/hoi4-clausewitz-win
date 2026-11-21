from _t205_common import *
from capstone.x86 import X86_OP_MEM,X86_REG_RIP
from _t205_flow import walk_flow
x=Runtime()
try:
 b=x.guard();helper=walk_flow(x.cs,x.code(0x153750,64),0x153750);hs='\n'.join(helper['asm']);assert 'mov dword ptr [rcx], edx'in hs and'mov rax, rcx'in hs and not helper['calls'] and not helper['unresolved_edges']
 lo,n=x.sections['.text'];raw=x.code(lo,n);target=0x2547630;wanted={0x3750,0x4de7,0x4cf2,0x28b7,0x3751,0x3753,0x375c,0x3850,0x4cb2,0x3754,0x3755,0x376b,0x30ab,0x2b05,0x2f04,0xe3};cs=x.cs;cs.detail=True;hits=[];p=0;cache={};out=[]
 while True:
  p=raw.find(b'\xe8',p)
  if p<0:break
  a=lo+p
  if p+5<=n and a+5+struct.unpack_from('<i',raw,p+1)[0]==target:hits.append(a)
  p+=1
 for a in hits:
  j=bisect.bisect_right(x.starts,a)-1
  if j<0 or not x.fns[j][0]<=a<x.fns[j][1]:continue
  st,en,_=x.fns[j]
  if st not in cache:
   ins=list(cs.disasm(x.code(st,en-st),st));cache[st]=(ins,{z.address:k for k,z in enumerate(ins)})
  ins,idx=cache[st]
  if a not in idx:continue
  k=idx[a];window=ins[max(0,k-15):k];c=None;d=None
  for i in reversed(window):
   if i.mnemonic=='call'and i.op_str!='0x153750':break
   if c is None and i.mnemonic=='mov'and i.op_str.startswith('edx, dword ptr [rip '):
    m=i.operands[1].mem;pa=i.address+i.size+m.disp;c=(struct.unpack('<I',x.code(pa,4))[0],pa)
   if d is None and i.mnemonic=='lea'and i.op_str.startswith('r8, [rip '):d=i.address+i.size+i.operands[1].mem.disp
  if c and c[0]in wanted:
   name=None
   if d is not None and 0<d<x.pr.image_size-160:
    try:name=x.code(d,160).split(b'\0')[0].decode('ascii')
    except UnicodeDecodeError:pass
   out.append({'call':hex(a),'token':hex(c[0]),'token_rva':hex(c[1]),'name':name,'name_rva':hex(d)if d is not None else None,'context':[f'{v.address:x} {v.mnemonic} {v.op_str}'for v in window]})
 assert any(z['token']=='0x3750'and z['name']=='manpower_lost'for z in out),'Known native positive control missing'
 d={'verified_identity_ctor':helper,'initial_attempts':'v1 used wrong ECX/RDX; v2 EDX/R8 stopped at identity ctor153750 and failed positive control; neither accepted as names/absence proof','scope':'only direct native registration calls (EDX token/R8 name; known positive control required) with constant RIP setup through statically verified identity ctor153750 before last call; no save access or function invocation','registration_call_candidates':len(hits),'matched':out,'guard_after':x.guard()};assert d['guard_after']==b;(R/'research/t205_supply_native_keyword_names_v5.json').write_text(json.dumps(d,indent=2),encoding='utf8');print(json.dumps(d,indent=2))
finally:x.close()
