from _t205_common import *
from _t205_flow import walk_flow
from capstone.x86 import X86_OP_MEM,X86_REG_RSP
from capstone import CS_AC_WRITE
x=Runtime()
try:
 g=x.guard();cs=x.cs;cs.detail=True;out={'ranges':[(0xc4e000,0xc4f000),(0xe60000,0xe70000),(0xf30000,0xf60000)],'scope':'new overlapping scalar/vector writes and address-taken candidates within declared pdata ranges; offsets alone never establish CSupplyConsumer ownership; not global alias/leaf coverage','packed_write_candidates':[],'address_taken_candidates':[],'removal_callback_flow':walk_flow(cs,x.code(0x147f6c0,0x500),0x147f6c0),'direct_removal_callers':[]}
 for st,en,u in x.fns:
  if not any(lo<=st<hi for lo,hi in out['ranges']):continue
  ins=list(cs.disasm(x.code(st,en-st),st))
  for k,i in enumerate(ins):
   for o in i.operands:
    if o.type!=X86_OP_MEM or o.mem.base==X86_REG_RSP:continue
    m=o.mem
    if (o.access&CS_AC_WRITE and any(m.disp<=t<m.disp+o.size for t in(0x1e,0x2e))and o.size>2)or(i.mnemonic=='lea'and m.disp in(0x1e,0x2e)):
     row={'site':hex(i.address),'pdata_start':hex(st),'size':o.size,'instruction':f'{i.mnemonic} {i.op_str}','context':[f'{z.address:x} {z.mnemonic} {z.op_str}'for z in ins[max(0,k-6):k+7]]};out['address_taken_candidates'if i.mnemonic=='lea'else'packed_write_candidates'].append(row)
 lo,n=x.sections['.text'];raw=x.code(lo,n)
 for op in(0xe8,0xe9):
  p=0
  while True:
   p=raw.find(bytes([op]),p)
   if p<0:break
   a=lo+p
   if p+5<=n and a+5+struct.unpack_from('<i',raw,p+1)[0]==0x147f6c0:
    f=x.clip(a);ks=[k for k,s in enumerate(f['asm'])if s.startswith(f'{a:x} ')and s.endswith('0x147f6c0')]
    for k in ks:out['direct_removal_callers'].append({'site':hex(a),'function':f['start'],'context':f['asm'][max(0,k-16):k+10]})
   p+=1
 out['guard_after']=x.guard();assert out['guard_after']==g;(R/'research/t205_packed_supply_and_removal_upstream.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('PACKED_WRITES',len(out['packed_write_candidates']),'ADDR_TAKEN',len(out['address_taken_candidates']));print('PACKED',[(z['site'],z['pdata_start'],z['instruction'])for z in out['packed_write_candidates']]);print('ADDRESS',out['address_taken_candidates']);print('REMOVAL_CALLERS',out['direct_removal_callers']);print('REMOVAL_FLOW',out['removal_callback_flow']['reachable_instruction_count'],out['removal_callback_flow']['unresolved_edges'],out['removal_callback_flow']['external_tails']);print('REMOVAL_HEAD',out['removal_callback_flow']['asm'][:16])
finally:x.close()
