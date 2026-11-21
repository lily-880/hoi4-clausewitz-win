from _t205_common import *
from _t205_flow import walk_flow
x=Runtime()
try:
 before=x.guard();out={'edges':[],'remove_manager_flow':walk_flow(x.cs,x.code(0xc0dca0,0x500),0xc0dca0),'army_removal_observer':x.clip(0x133e700),'result_dispatch':x.clip(0xd3cd30),'air_factor_setter':x.clip(0xd3ef90)};va,n=x.sections['.text'];raw=x.code(va,n)
 for opcode,mnem in((b'\xe8','call'),(b'\xe9','jmp')):
  p=0
  while True:
   p=raw.find(opcode,p)
   if p<0 or p+5>len(raw):break
   dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
   if dst in(0xc0dca0,0x133e700,):
    f=x.clip(va+p);key=f'{va+p:x} {mnem} {hex(dst)}'
    if key in f['asm']:
     k=f['asm'].index(key);out['edges'].append({'site':hex(va+p),'target':hex(dst),'kind':mnem,'function':f['start'],'context':f['asm'][max(0,k-20):k+12]})
   p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t205_ordinary_battle_close_lifetime.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('EDGES',json.dumps(out['edges'],indent=2));print('MANAGER FLOW',out['remove_manager_flow']['reachable_instruction_count'],out['remove_manager_flow']['unresolved_edges']);print('MANAGER HEAD',out['remove_manager_flow']['asm'][:20]);print('OTHERS',[(a,out[a]['asm'])for a in('army_removal_observer','result_dispatch','air_factor_setter')])
finally:x.close()
