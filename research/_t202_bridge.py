from _t202_common import *
import re
x=Runtime()
try:
 before=x.guard();out={'functions':{},'renderer_callers':[],'combatant_140_references':[],'plan_group_binding':[]}
 for a in (0x133c240,0x147eb10,0xc53180,0xc70960,0xccb550,0x133a8e0):out['functions'][hex(a)]=x.clip(a)
 va,size=x.sections['.text'];text=x.code(va,size);pos=0
 while True:
  pos=text.find(b'\xe8',pos)
  if pos<0 or pos+5>len(text):break
  dest=va+pos+5+struct.unpack_from('<i',text,pos+1)[0]
  if dest==0x12e6e20:
   f=x.clip(va+pos);key=f'{va+pos:x} call 0x12e6e20'
   if key in f['asm']:
    k=f['asm'].index(key);out['renderer_callers'].append({'site':hex(va+pos),'function':f['start'],'context':f['asm'][max(0,k-22):k+4],'code_sha256':f['loaded_code_sha256']})
  pos+=1
 del text
 for st,en,u in x.fns:
  if not 0x133a000<=st<0x134d000:continue
  ins=list(x.cs.disasm(x.code(st,en-st),st));hits=[]
  for j,i in enumerate(ins):
   if re.search(r'\[(?!r[bsp]{2}\b)[^]]* \+ 0x140\]',i.op_str):hits.append({'site':hex(i.address),'context':[f'{z.address:x} {z.mnemonic} {z.op_str}'for z in ins[max(0,j-3):j+5]]})
  if hits:
   f=x.clip(st);out['combatant_140_references'].append({'function':f['start'],'hits':hits,'code_sha256':f['loaded_code_sha256']})
 r=x.reader();seen=set();pending=[]
 for tp in r.array(x.country+0x168,64):
  for gp in r.array(tp+0x80,256):
   for off in(0x98,0xb0,0xc8):pending+=r.array(gp+off,256)
 while pending:
  ip=pending.pop(0)
  if ip in seen:continue
  seen.add(ip);assert len(seen)<=256;r.require(ip,'COrderInstance');gp=r.q(ip+0x38);r.require(gp,'COrdersGroup');out['plan_group_binding'].append({'plan_id':r.i(ip+0x244),'orders_group_ptr38':hex(gp),'group_raw_u32_8':r.i(gp+8),'rtti':x.cls(gp)})
  for off in(0x1f8,0x2d0):pending+=r.array(ip+off,256)
 r.stable();after=x.guard();assert before==after;out['guard_before']=before;out['guard_after']=after
 (R/'research/t202_renderer_loss_bridge.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print('FUNCTIONS',[(a,len(f['asm']))for a,f in out['functions'].items()]);print('RENDERER_CALLERS',json.dumps(out['renderer_callers'],indent=2));print('RECORD_REFS',json.dumps(out['combatant_140_references'],indent=2));print('PLAN_GROUPS',out['plan_group_binding'])
finally:x.close()
