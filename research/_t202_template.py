from _t202_common import *
import re
x=Runtime()
try:
 before=x.guard();va,n=x.sections['.rdata'];raw=x.code(va,n);dva,dn=x.sections['.data'];types=x.code(dva,dn);out={'rtti_matches':[],'tables':[]}
 for m in re.finditer(rb'\.\?A[UV][ -~]{1,200}?@@\x00',types):
  name=m.group()[:-1].decode('ascii')
  if not('Template'in name and any(s in name for s in('Change','Convert','Unit','Army'))):continue
  td=dva+m.start()-16;out['rtti_matches'].append({'name':name,'type_descriptor':hex(td)})
  needle=struct.pack('<I',td);p=0
  while True:
   p=raw.find(needle,p)
   if p<0:break
   co=p-12;p+=1
   if co<0 or co+24>len(raw):continue
   sig,off,cd,t,cl,sl=struct.unpack_from('<IIIIII',raw,co)
   if sig!=1 or sl!=va+co:continue
   vp=0;vneedle=struct.pack('<Q',x.base+va+co)
   while True:
    vp=raw.find(vneedle,vp)
    if vp<0:break
    v=va+vp+8;vp+=1;slots=[]
    for slot in range(0,0x90,8):
     target=struct.unpack_from('<Q',raw,v-va+slot)[0]-x.base
     if not x.sections['.text'][0]<=target<sum(x.sections['.text']):break
     f=x.clip(target);slots.append({'slot':hex(slot),'target':hex(target),'start':f['start'],'instructions':len(f['asm'])})
    out['tables'].append({'name':name,'col_offset':off,'vtable':hex(v),'slots':slots})
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t202_template_reason_sources.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:x.close()
