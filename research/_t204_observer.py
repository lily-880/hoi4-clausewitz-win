from _t204_common import *
x=Runtime()
try:
 b=x.guard();r=x.reader();cp=r.array(x.gs+0x268,4096)[0];sp=r.q(cp+0x28);obs=sp+0x1d0;r.require(obs,'CStatsObserver@NCombatLog');vt=r.q(obs);vlo=vt-x.base;lo,n=x.sections['.text'];hi=lo+n;out={'vtable_rva':hex(vlo),'slots':{},'vtable_lea_refs':[],'guard_before':b}
 for off in range(0,0x140,8):
  target=r.q(vt+off)-x.base
  if not lo<=target<hi:out['vtable_end']={'offset':hex(off),'raw':hex(target+x.base)};break
  f=x.clip(target);out['slots'][hex(off)]={'target':hex(target),'function':f}
 raw=x.code(lo,n)
 for rex in(0x48,0x4c):
  for mr in range(5,0x40,8):
   needle=bytes([rex,0x8d,mr]);p=0
   while True:
    p=raw.find(needle,p)
    if p<0 or p+7>len(raw):break
    dst=lo+p+7+struct.unpack_from('<i',raw,p+3)[0]
    if dst==vlo:
     f=x.clip(lo+p);key=f'{lo+p:x} lea '
     ks=[k for k,s in enumerate(f['asm'])if s.startswith(key)]
     for k in ks:out['vtable_lea_refs'].append({'site':hex(lo+p),'function':f['start'],'context':f['asm'][max(0,k-8):k+25]})
    p+=1
 r.stable();out['guard_after']=x.guard();assert out['guard_after']==b;(R/'research/t204_statsobserver_vtable_lifecycle.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('SLOTS',[(k,v['target'],len(v['function']['asm']))for k,v in out['slots'].items()]);print('REFS',json.dumps(out['vtable_lea_refs'],indent=2))
finally:x.close()
