from _t204_common import *
x=Runtime()
try:
 b=x.guard();out=[]
 for st,en,u in x.fns:
  if not any(lo<=st<hi for lo,hi in((0xe60000,0xe70000),(0xf40000,0xf50000))):continue
  f=x.clip(st)
  for k,s in enumerate(f['asm']):
   if any(z in s for z in(' + 0x1e]',' + 0x2e]'))and 'byte ptr ['in s:out.append({'function':f['start'],'instruction':s,'context':f['asm'][max(0,k-12):k+8]})
 assert x.guard()==b;(R/'research/t204_delivery_shortcut_flag_xrefs.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
