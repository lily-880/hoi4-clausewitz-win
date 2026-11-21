from _t203_common import *
x=Runtime()
try:
 before=x.guard();out={'edges':[],'wrapper':x.clip(0xcec270)};va,n=x.sections['.text'];raw=x.code(va,n)
 for opcode,mnem in((b'\xe8','call'),(b'\xe9','jmp')):
  p=0
  while True:
   p=raw.find(opcode,p)
   if p<0 or p+5>len(raw):break
   dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
   if dst in(0xcec270,):
    f=x.clip(va+p);key=f'{va+p:x} {mnem} {hex(dst)}'
    if key in f['asm']:
     k=f['asm'].index(key);out['edges'].append({'site':hex(va+p),'target':hex(dst),'kind':mnem,'function':f['start'],'context':f['asm'][max(0,k-20):k+12]})
   p+=1
 r=x.reader();ap=r.array(x.country+0x290,256)[0];vt=x.q(ap);rv,nr=x.sections['.rdata'];rd=x.code(rv,nr);needle=struct.pack('<Q',x.base+0xcec270);p=0;out['rdata_refs']=[]
 while True:
  p=rd.find(needle,p)
  if p<0:break
  out['rdata_refs'].append({'rva':hex(rv+p),'relative_to_army_vtable':hex(x.base+rv+p-vt)});p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_loss_army_callers.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:x.close()
