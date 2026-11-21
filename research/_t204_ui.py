from _t204_common import *
x=Runtime()
try:
 b=x.guard();targets={0x2a6b1f0:'atk_lost_manpower',0x2a6b208:'def_lost_manpower',0x2a7a470:'lost_manpower',0x2a8c958:'attacker_casualty',0x2a8c9f8:'defender_casualty',0x2b69880:'manpower_lost'};out={'ui_literal_refs':[],'keyword_pointer_refs':[]};lo,n=x.sections['.text'];raw=x.code(lo,n)
 for rex in(0x48,0x4c):
  for mr in range(5,0x40,8):
   needle=bytes([rex,0x8d,mr]);p=0
   while True:
    p=raw.find(needle,p)
    if p<0 or p+7>len(raw):break
    dst=lo+p+7+struct.unpack_from('<i',raw,p+3)[0]
    if dst in targets:
     f=x.clip(lo+p);ks=[k for k,s in enumerate(f['asm'])if s.startswith(f'{lo+p:x} lea ')]
     for k in ks:out['ui_literal_refs'].append({'label':targets[dst],'site':hex(lo+p),'function':f['start'],'context':f['asm'][max(0,k-12):k+32]})
    p+=1
 rv,nr=x.sections['.rdata'];rd=x.code(rv,nr);key=struct.pack('<Q',x.base+0x2b69880);p=0
 while True:
  p=rd.find(key,p)
  if p<0:break
  out['keyword_pointer_refs'].append({'rva':hex(rv+p),'nearby_u64':[hex(v[0])for v in struct.iter_unpack('<Q',rd[p-16:p+24])]});p+=1
 assert x.guard()==b;(R/'research/t204_stats_manpower_ui_consumers.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
