from _t204_common import *
x=Runtime()
try:
 b=x.guard();out=[]
 for lo,hi in((0xc4e000,0xc4f000),(0xf50000,0xf60000)):
  raw=x.code(lo,hi-lo);ls=[i for i in x.cs.disasm(raw,lo)]
  for k,i in enumerate(ls):
   if any(t in i.op_str for t in(' + 0x1e]',' + 0x1d]',' + 0x2e]'))and i.mnemonic not in('lea',):out.append({'instruction':f'{i.address:x} {i.mnemonic} {i.op_str}','context':[f'{z.address:x} {z.mnemonic} {z.op_str}'for z in ls[max(0,k-10):k+9]],'scope':'bounded linear decode including leaf funcs; not global absence proof'})
 assert x.guard()==b;(R/'research/t204_supply_leaf_flag_candidates.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
