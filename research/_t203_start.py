from _t203_common import *
import re
x=Runtime()
try:
 before=x.guard();out={'guard_before':before,'functions':{},'callers':[],'ui_labels':{}}
 targets=(0xc4a420,0xcc64c0,0xcc6bf0,0xcc6c40,0x19c9ac0,0x19c9a20,0x19c9c80,0x19c9a10,0x15a6510,0x15a6e40,0x159fb30,0x1755d90,0x175d940)
 for a in targets:
  f=x.clip(a);out['functions'][hex(a)]=f;labels=[]
  for j,line in enumerate(f['asm'][:-1]):
   m=re.search(r'lea [^,]+, \[rip ([+-]) 0x([0-9a-f]+)\]',line)
   if not m:continue
   na=int(f['asm'][j+1].split()[0],16);dest=na+int(m.group(2),16)*(1 if m.group(1)=='+'else-1)
   if not 0<dest<x.pr.image_size-160:continue
   b=x.code(dest,160).split(b'\0')[0]
   if re.fullmatch(rb'[A-Z][A-Z0-9_ .#~()/-]{5,159}',b):labels.append({'instruction':line,'rva':hex(dest),'text':b.decode()})
  out['ui_labels'][hex(a)]=labels
 for a in(0x2a4bd78,0x2a4bd50):out['ui_labels'][hex(a)]=x.code(a,160).split(b'\0')[0].decode('ascii',errors='replace')
 va,n=x.sections['.text'];raw=x.code(va,n);p=0
 while True:
  p=raw.find(b'\xe8',p)
  if p<0 or p+5>len(raw):break
  dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
  if dst in(0xc4a420,0x19c9a20,0x15a6e40):
   f=x.clip(va+p);key=f'{va+p:x} call {hex(dst)}'
   if key in f['asm']:
    k=f['asm'].index(key);out['callers'].append({'site':hex(va+p),'target':hex(dst),'function':f['start'],'context':f['asm'][max(0,k-14):k+10]})
  p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_initial_chains.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 (R/'research/t203_checkpoint.md').write_text('# t203 checkpoint\n\n## 块1：续接与新链开段\n会话已只读重绑，PID12948/base7FF7A91C0000，官方pause1/speed0/tick60759398，六计划均false，闸门关闭。0Post/0游戏写/0远程调用，不推进、不碰存档、不commit/push、不访问D。只读已加载代码/.pdata，生产exe磁盘指纹门未绕过。\n已开始深查C4A420的CC6BF0上下文与19C9A20接收者，以及159FB30/15A6E40/1755D90的配送状态消费者；证据t203_initial_chains.json。当前本地74/42，D最后72/44未同步；新升格须独立证明。\n',encoding='utf-8')
 print('FUNCTIONS',[(a,len(v['asm']))for a,v in out['functions'].items()]);print('CALLERS',json.dumps(out['callers'],indent=2));print('LABELS',json.dumps(out['ui_labels'],indent=2))
finally:x.close()
