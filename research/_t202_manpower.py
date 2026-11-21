from _t202_common import *
from input_loaded_fields import unit_current_manpower
x=Runtime()
try:
 before=x.guard();out={'functions':{},'removal_callers':[],'frontline_manpower':[]}
 for a in(0xcc6bf0,0xcc6c40):out['functions'][hex(a)]=x.clip(a)
 va,n=x.sections['.text'];raw=x.code(va,n);p=0
 while True:
  p=raw.find(b'\xe8',p)
  if p<0 or p+5>len(raw):break
  dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
  if dst in(0xcc6bf0,0xcc6c40):
   f=x.clip(va+p);key=f'{va+p:x} call {hex(dst)}'
   if key in f['asm']:
    k=f['asm'].index(key);out['removal_callers'].append({'site':hex(va+p),'target':hex(dst),'function':f['start'],'context':f['asm'][max(0,k-10):k+14]})
  p+=1
 r=x.reader();seen=set()
 for cp in r.array(x.gs+0x268,4096):
  for side,off in(('attacker',0x28),('defender',0x30)):
   for ap in r.array(r.q(cp+off)+0xe8,128):
    if ap in seen:continue
    seen.add(ap);r.require(ap,'CArmy');value,ev=unit_current_manpower(r,ap);out['frontline_manpower'].append({'army_id':r.i(ap+0x1c),'combat_id':r.i(cp+0x1c),'side':side,'current':value,'engine_need_total':ev['engine_need_total'],'difference_is_not_combat_casualties':ev['engine_missing_formula']})
 r.stable();out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t202_manpower_removal_chain.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('FUNCTIONS',[(a,len(f['asm']))for a,f in out['functions'].items()]);print('CALLERS',json.dumps(out['removal_callers'],indent=2));print('MANPOWER',out['frontline_manpower'])
finally:x.close()
