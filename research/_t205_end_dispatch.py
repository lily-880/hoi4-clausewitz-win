from _t205_common import *
x=Runtime()
try:
 b=x.guard();out={'virtual70_sites':[],'border_direct_caller':x.clip(0x148a4b0),'unit_leader_getter':x.clip(0xccb550),'observer_choice_writer':x.clip(0xd3a1e0)};lo=0x147c000;raw=x.code(lo,0xd000)
 for op in range(0x50,0x58):
  key=bytes([0xff,op,0x70]);p=0
  while True:
   p=raw.find(key,p)
   if p<0:break
   f=x.clip(lo+p);ks=[k for k,s in enumerate(f['asm'])if s.startswith(f'{lo+p:x} call ')and' + 0x70]'in s]
   for k in ks:out['virtual70_sites'].append({'site':hex(lo+p),'function':f['start'],'context':f['asm'][max(0,k-16):k+14]})
   p+=1
 d=json.loads((R/'research/t205_close_checksum_dispatch.json').read_text(encoding='utf8'));f=d['base_parser']['asm'];out['base_parser_offset_refs']=[f[max(0,k-6):k+9]for k,s in enumerate(f)if any(z in s for z in(' + 0x1e]',' + 0x1d]',' + 0x2e]'))];out['base_parser_tail']=f[-70:]
 assert x.guard()==b;(R/'research/t205_close_lifecycle_follow.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('VIRTUAL',json.dumps(out['virtual70_sites'],indent=2));print('BASE_OFFSETS',json.dumps(out['base_parser_offset_refs'],indent=2));print('BASE_TAIL',out['base_parser_tail']);print('SMALL',[(a,out[a]['asm'])for a in('unit_leader_getter','observer_choice_writer')])
finally:x.close()
