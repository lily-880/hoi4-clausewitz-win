from _t205_common import *
x=Runtime()
try:
 before=x.guard();out={'edges':[],'base_parser':x.clip(0xc58600),'virtual_bindings':[]};va,n=x.sections['.text'];raw=x.code(va,n)
 for opcode,mnem in((b'\xe8','call'),(b'\xe9','jmp')):
  p=0
  while True:
   p=raw.find(opcode,p)
   if p<0 or p+5>len(raw):break
   dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
   if dst in(0x1349260,0xf42ad0,0xd3f020,0xd3f4d0,):
    f=x.clip(va+p);key=f'{va+p:x} {mnem} {hex(dst)}'
    if key in f['asm']:
     k=f['asm'].index(key);out['edges'].append({'site':hex(va+p),'target':hex(dst),'kind':mnem,'function':f['start'],'context':f['asm'][max(0,k-20):k+12]})
   p+=1
 r=x.reader();roots=[('combat',r.array(x.gs+0x268,4096)[0]),('supply_system',r.q(x.gs+0x3d8))];lo,n=x.sections['.text']
 for kind,obj in roots:
  vt=r.q(obj);v={'kind':kind,'object':hex(obj),'class':x.cls(obj),'vtable':hex(vt-x.base),'methods':{}}
  for off in range(0,0x200,8):
   t=r.q(vt+off)-x.base
   if not lo<=t<lo+n:break
   v['methods'][hex(off)]=hex(t)
  out['virtual_bindings'].append(v)
 r.stable();out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t205_close_checksum_dispatch.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('EDGES',json.dumps(out['edges'],indent=2));print('BINDINGS',json.dumps(out['virtual_bindings'],indent=2));print('BASEPARSE_HEAD',out['base_parser']['asm'][:25])
finally:x.close()
