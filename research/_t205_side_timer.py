from _t205_common import *
from _t205_flow import walk_flow
x=Runtime()
try:
 g=x.guard();r=x.reader();cp=r.array(x.gs+0x268,4096)[0];side=r.q(cp+0x28);r.require(side,'CLandCombatant');vt=r.q(side);lo,n=x.sections['.text'];out={'side':hex(side),'class':x.cls(side),'vtable':hex(vt-x.base),'methods':{},'flows':{}}
 for k in range(0,0x200,8):
  a=r.q(vt+k)-x.base
  if not lo<=a<lo+n:break
  out['methods'][hex(k)]=hex(a)
 for a,n in((0x1347fd0,0x1000),(0x1348d30,0x80),(0xc4e950,0x800)):
  f=walk_flow(x.cs,x.code(a,n),a);out['flows'][hex(a)]=f;(R/f'research/_t205_flow_{a:x}.txt').write_text('\n'.join(f['asm']),encoding='utf8')
 r.stable();out['guard_after']=x.guard();assert out['guard_after']==g;(R/'research/t205_side_callback_and_timer_dispatch.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('SIDE',out['class'],out['vtable'],out['methods']);print('FLOWS',[(a,z['reachable_instruction_count'],z['unresolved_edges'],z['external_tails'])for a,z in out['flows'].items()]);print('CHECK_END','\n'.join(out['flows']['0x1348d30']['asm']));d=json.loads((R/'research/t205_combat_callback_lifecycle.json').read_text(encoding='utf8'))['manager_update']['asm']
 for k,s in enumerate(d):
  if any(z in s for z in(' + 0x78]',' + 0x80]')):print('DISPATCH_CTX','\n'.join(d[max(0,k-9):k+7]))
finally:x.close()
