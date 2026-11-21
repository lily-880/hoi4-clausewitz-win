from _t204_common import *
x=Runtime()
try:
 b=x.guard();r=x.reader();out={'ui_owners':[],'supply':{},'token_registration':{}};lo,n=x.sections['.text'];hi=lo+n;rv,nr=x.sections['.rdata'];rd=x.code(rv,nr)
 for target in(0x17845a0,0x183c540,0x1939640,0x193aaf0):
  key=struct.pack('<Q',x.base+target);p=0
  while True:
   p=rd.find(key,p)
   if p<0:break
   st=rv+p
   for _ in range(192):
    value=x.q(x.base+st-8)-x.base
    if not lo<=value<hi:break
    st-=8
   try:
    col=x.q(x.base+st-8);sig,off,cd,td=struct.unpack('<IIII',x.pr.read(col,16));assert sig==1;name=x.code(td+0x10,160).split(b'\0')[0].decode();item={'method':hex(target),'class':name,'vtable':hex(st),'slot':hex(rv+p-st),'local_virtuals':{}}
    for k in range(0,0x600,8):
     t=x.q(x.base+st+k)-x.base
     if not lo<=t<hi:break
     if target&~0xffff==t&~0xffff:item['local_virtuals'][hex(k)]={'target':hex(t),'function':x.clip(t)}
    out['ui_owners'].append(item)
   except(AssertionError,UnicodeError):pass
   p+=1
 ap=r.array(x.country+0x290,256)[0];sc=ap+0x10;vt=r.q(sc);col=r.q(vt-8);sig,off,cd,td,chd,selfr=struct.unpack('<IIIIII',x.pr.read(col,24));assert sig==1 and off==0x10 and x.cls(sc)=='.?AVCArmy@@';count,bca=struct.unpack('<II',x.code(chd+8,8));assert 0<count<=64;names=[]
 for j in range(count):
  bc=struct.unpack('<I',x.code(bca+j*4,4))[0];tp=struct.unpack('<I',x.code(bc,4))[0];names.append(x.code(tp+0x10,160).split(b'\0')[0].decode())
 assert '.?AVCSupplyConsumer@@'in names;out['supply']={'complete_class':x.cls(sc),'subobject_offset':off,'base_hierarchy':names,'vtable':hex(vt-x.base),'slots':{},'vtable_refs':[]}
 for k in range(0,0x100,8):
  t=r.q(vt+k)-x.base
  if not lo<=t<hi:break
  out['supply']['slots'][hex(k)]={'target':hex(t),'function':x.clip(t)}
 raw=x.code(lo,n)
 for rex in(0x48,0x4c):
  for mr in range(5,0x40,8):
   needle=bytes([rex,0x8d,mr]);p=0
   while True:
    p=raw.find(needle,p)
    if p<0 or p+7>len(raw):break
    dst=lo+p+7+struct.unpack_from('<i',raw,p+3)[0]
    if dst==vt-x.base:
     f=x.clip(lo+p);out['supply']['vtable_refs'].append({'site':hex(lo+p),'function':f['start'],'asm':f['asm']})
    p+=1
 i=next(x.cs.disasm(x.code(0xf258e,15),0xf258e));target=i.address+i.size+int(i.op_str.split(' + ')[1][:-1],16);out['token_registration']={'instruction':f'{i.address:x} {i.mnemonic} {i.op_str}','constant_rva':hex(target),'value':struct.unpack('<I',x.code(target,4))[0],'name':'manpower_lost','name_rva':'0x2b69880','registration_call':'0xf25b1 ->2547630'}
 r.stable();assert x.guard()==b;(R/'research/t204_ui_supply_owner_bindings.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('UI',[(u['class'],u['method'],u['slot'],[(k,v['target'],len(v['function']['asm']))for k,v in u['local_virtuals'].items()])for u in out['ui_owners']]);print('SC SLOTS',[(k,v['target'])for k,v in out['supply']['slots'].items()]);print('SC CTORS',[(z['site'],z['function'])for z in out['supply']['vtable_refs']]);print('TOKEN',out['token_registration'])
finally:x.close()
