from _t202_common import *
import re
x=Runtime()
try:
 before=x.guard();out={'functions':{},'ui_reason4_candidates':[],'guard_before':before}
 for a in(0x737f50,0x7362c0,0xeef530,0x12b6690,0x173d7d0,0x173c990,0x173e840):out['functions'][hex(a)]=x.clip(a)
 for st,en,u in x.fns:
  if not 0x1738000<=st<0x1745000:continue
  ins=list(x.cs.disasm(x.code(st,en-st),st))
  for j,i in enumerate(ins):
   if i.mnemonic=='mov'and re.search(r', 4$',i.op_str):
    f=x.clip(st);out['ui_reason4_candidates'].append({'site':hex(i.address),'function':f['start'],'context':[f'{z.address:x} {z.mnemonic} {z.op_str}'for z in ins[max(0,j-7):j+8]]})
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t202_delivery_reason_branch.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('FUNCTIONS',[(a,len(f['asm']))for a,f in out['functions'].items()]);print('REASON4',json.dumps(out['ui_reason4_candidates'],indent=2))
finally:x.close()
