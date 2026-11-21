from _t205_common import *
from _t205_flow import walk_flow
x=Runtime()
try:
 g=x.guard();out={'functions':{},'getter':walk_flow(x.cs,x.code(0xcc64c0,0x400),0xcc64c0),'scope':'inspect new packed-copy candidates; neither offset overlap nor same vslot implies CSupplyConsumer/Combatant ownership'}
 for a in(0xc4e890,0xf3c760,0xf404b0,0xf46724):out['functions'][hex(a)]=x.clip(a)
 out['guard_after']=x.guard();assert out['guard_after']==g;(R/'research/t205_packed_copy_owner_candidates_v2.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('MANPOWER_GETTER','\n'.join(out['getter']['asm']))
 for a,d in out['functions'].items():print(a,'\n'.join(d['asm']))
finally:x.close()
