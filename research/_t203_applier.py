from _t203_common import *
x=Runtime()
try:
 before=x.guard();out={'edges':[],'functions':{hex(a):x.clip(a)for a in(0xce7310,0xce84d0)}};va,n=x.sections['.text'];raw=x.code(va,n)
 for opcode,mnem in((b'\xe8','call'),(b'\xe9','jmp')):
  p=0
  while True:
   p=raw.find(opcode,p)
   if p<0 or p+5>len(raw):break
   dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
   if dst in(0xce7310,0xce84d0,):
    f=x.clip(va+p);key=f'{va+p:x} {mnem} {hex(dst)}'
    if key in f['asm']:
     k=f['asm'].index(key);out['edges'].append({'site':hex(va+p),'target':hex(dst),'kind':mnem,'function':f['start'],'context':f['asm'][max(0,k-20):k+12]})
   p+=1
 out['literals']=[]
 for key,f in out['functions'].items():
  for z in f['asm']:
   if 'lea rdx, [rip + 'in z:
    a=int(z.split(' ')[0],16);i=next(x.cs.disasm(x.code(a,15),a));q=a+i.size+int(i.op_str.split(' + ')[1][:-1],16)
    try:
     v=x.code(q,200).split(b'\0')[0].decode('ascii')
     if v and all(c.isprintable()or c in '\n\t'for c in v):out['literals'].append({'function':key,'site':hex(a),'literal':v})
    except(UnicodeError,AssertionError):pass
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_loss_applier_callers.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({'edges':out['edges'],'literals':out['literals']},indent=2))
finally:x.close()
