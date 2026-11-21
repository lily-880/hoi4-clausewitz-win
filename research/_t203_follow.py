from _t203_common import *
import re
x=Runtime()
try:
 before=x.guard();out={'ui_control_strings':{},'functions':{},'orders_group_deployment':[],'manpower_virtuals':[]}
 for a in(0x175d940,0x1739900,0x1755d90):
  f=x.clip(a);rows=[]
  for j,line in enumerate(f['asm'][:-1]):
   m=re.search(r'lea [^,]+, \[rip ([+-]) 0x([0-9a-f]+)\]',line)
   if not m:continue
   na=int(f['asm'][j+1].split()[0],16);dest=na+int(m.group(2),16)*(1 if m.group(1)=='+'else-1)
   if not 0<dest<x.pr.image_size-160:continue
   b=x.code(dest,160).split(b'\0')[0]
   if len(b)>=3 and all(32<=v<127 for v in b):rows.append({'site':line.split()[0],'rva':hex(dest),'text':b.decode()})
  out['ui_control_strings'][hex(a)]=rows
 for a in(0x737f50,0x7362c0,0xeef530,0x12b6690,0xcc64c0,0xcc6570,0x19c9c80):out['functions'][hex(a)]=x.clip(a)
 r=x.reader()
 for tp in r.array(x.country+0x168,64):
  for gp in r.array(tp+0x80,256):
   r.require(gp,'COrdersGroup');dp=r.q(gp+0x188);d={'id':r.i(gp+0xc),'group':hex(gp),'deployment_ptr188':hex(dp)}
   if dp:
    try:d['rtti']=x.cls(dp)
    except AssertionError:d['rtti']=None
    d['raw_88_8c']=list(struct.unpack('<ii',r.exact(dp+0x88,8)))
   out['orders_group_deployment'].append(d)
 # Reuse already existing combat participants only, to bind actual CArmyManpower methods.
 cp=r.array(x.gs+0x268,4096)[0];bp=r.q(cp+0x30);ap=r.array(bp+0xe8,128)[0];mp=ap+0x3d0;r.require(mp,'CArmyManpower');vt=r.q(mp)
 for slot in range(0,0x90,8):
  target=r.q(vt+slot)-x.base
  if not x.sections['.text'][0]<=target<sum(x.sections['.text']):break
  f=x.clip(target);out['manpower_virtuals'].append({'slot':hex(slot),'target':hex(target),'function':f})
 r.stable();out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_delivery_manpower_semantics.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('STRINGS',json.dumps(out['ui_control_strings'],indent=2));print('DEPLOY',out['orders_group_deployment']);print('MPVT',[(p['slot'],p['target'],len(p['function']['asm']))for p in out['manpower_virtuals']])
finally:x.close()
