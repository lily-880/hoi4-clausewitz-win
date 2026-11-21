from _t204_common import *
x=Runtime()
try:
 before=x.guard();out={'edges':[],'unit_constructor':x.clip(0xc4e5d0)};va,n=x.sections['.text'];raw=x.code(va,n)
 for opcode,mnem in((b'\xe8','call'),(b'\xe9','jmp')):
  p=0
  while True:
   p=raw.find(opcode,p)
   if p<0 or p+5>len(raw):break
   dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
   if dst in(0x17845a0,0x183c540,0x1939640,0x193aaf0,0xd3b6d0,):
    f=x.clip(va+p);key=f'{va+p:x} {mnem} {hex(dst)}'
    if key in f['asm']:
     k=f['asm'].index(key);out['edges'].append({'site':hex(va+p),'target':hex(dst),'kind':mnem,'function':f['start'],'context':f['asm'][max(0,k-20):k+12]})
   p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t204_ui_close_dispatch_edges.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('EDGES',json.dumps(out['edges'],indent=2));print('UNIT CTOR HEAD',out['unit_constructor']['asm'][:60])
finally:x.close()
