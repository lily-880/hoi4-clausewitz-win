from _t202_common import *
x=Runtime()
try:
 before=x.guard();out={'callers':[]};va,n=x.sections['.text'];raw=x.code(va,n);p=0
 while True:
  p=raw.find(b'\xe8',p)
  if p<0 or p+5>len(raw):break
  dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
  if dst==0xe64c50:
   f=x.clip(va+p);key=f'{va+p:x} call 0xe64c50'
   if key in f['asm']:
    k=f['asm'].index(key);out['callers'].append({'site':hex(va+p),'function':f['start'],'context':f['asm'][max(0,k-8):k+11]})
  p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t202_delivery_callers.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COUNT',len(out['callers']));print(json.dumps(out['callers'],indent=2))
finally:x.close()
