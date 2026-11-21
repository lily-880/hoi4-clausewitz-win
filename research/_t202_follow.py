from _t202_common import *
import re
x=Runtime()
try:
 before=x.guard();out={'combatant_vmethods':{},'constructor_callers':[],'renderer_arg_sources':{}}
 r=x.reader();combats=r.array(x.gs+0x268,4096);assert combats
 for cp in combats:
  r.require(cp,'CLandCombat')
  for off in(0x28,0x30):
   bp=r.q(cp+off);r.require(bp,'CLandCombatant');vt=r.q(bp)
   for slot in(0x70,0x98,0xb0,0x100):
    a=r.q(vt+slot)-x.base
    if hex(a)not in out['combatant_vmethods']:out['combatant_vmethods'][hex(a)]={'slot':hex(slot),'vt_rva':hex(vt-x.base),'function':x.clip(a)}
 f=json.loads((R/'research/t202_initial_chains.json').read_text())['functions']['0x12e6e20']['asm'];points=[int(s.split()[0],16)for s in f if any(t in s for t in('rbp + 0x290]','rbp + 0x298]','r14 + 0x70]','r14 + 0x280]','r14 + 0x1f8]','r14 + 0x2d0]'))];out['renderer_arg_sources']={'arg5_path_arg6_instance_contexts':[[s for s in f if a-55<=int(s.split()[0],16)<=a+90]for a in points]}
 va,size=x.sections['.text'];data=x.code(va,size)
 for m in re.finditer(b'\xe8',data):
  j=m.start()
  if j+5>len(data):continue
  a=va+j
  if a+5+struct.unpack_from('<i',data,j+1)[0]!=0x133a150:continue
  d=x.clip(a)
  if not any(s.startswith(f'{a:x} call 0x133a150')for s in d['asm']):continue
  out['constructor_callers'].append({'at':hex(a),'function':d})
 r.stable();after=x.guard();assert before==after;out['guard_after']=after;(R/'research/t202_follow_chains.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print('COMBATANT_VMETHODS',[(a,d['slot'],len(d['function']['asm']))for a,d in out['combatant_vmethods'].items()]);print('CTOR_CALLERS',[(d['at'],d['function']['start'],len(d['function']['asm']))for d in out['constructor_callers']]);print('RENDER_ARGS',json.dumps(out['renderer_arg_sources'],indent=2))
 for a,d in out['combatant_vmethods'].items():print('METHOD_CALLS',a,sorted(set(s.split(' call ')[1]for s in d['function']['asm']if ' call 0x'in s)))
finally:x.close()
