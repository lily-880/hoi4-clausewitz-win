from _t202_common import *
x=Runtime()
try:
 before=x.guard();out={'functions':{},'army_virtuals':{},'plan_type_links':[],'formatter_callers':[],'live_damage_counters':[]}
 for a in(0x147c240,0xd3d3c0,0xd39880,0x1349aa0):out['functions'][hex(a)]=x.clip(a)
 r=x.reader()
 for cp in r.array(x.gs+0x268,4096):
  for side,off in(('attacker',0x28),('defender',0x30)):
   bp=r.q(cp+off);rows=[]
   for ap in r.array(bp+0xe8,128):
    r.require(ap,'CArmy');vt=r.q(ap)
    for slot in(0xc0,0xf8,0x120,0x170):
     a=r.q(vt+slot)-x.base
     if hex(a)not in out['army_virtuals']:out['army_virtuals'][hex(a)]={'slot':hex(slot),'function':x.clip(a)}
    rows.append({'army_ptr':hex(ap),'typed_id_18':list(struct.unpack('<II',r.exact(ap+0x18,8)))})
   out['live_damage_counters'].append({'combat_id':r.i(cp+0x1c),'side':side,'field178':struct.unpack('<q',r.exact(bp+0x178,8))[0],'field180':struct.unpack('<q',r.exact(bp+0x180,8))[0],'armies':rows})
 seen=set();pending=[]
 for tp in r.array(x.country+0x168,64):
  for gp in r.array(tp+0x80,256):
   for off in(0x98,0xb0,0xc8):pending+=r.array(gp+off,256)
 while pending:
  ip=pending.pop(0)
  if ip in seen:continue
  seen.add(ip);assert len(seen)<=256;r.require(ip,'COrderInstance');links=[]
  for jp in r.array(ip+0x1e0,256):r.require(jp,'COrderInstance');links.append({'id':r.i(jp+0x244),'type_raw':r.i(jp+0x30)})
  out['plan_type_links'].append({'id':r.i(ip+0x244),'type_raw':r.i(ip+0x30),'links_1e0':links})
  for off in(0x1f8,0x2d0):pending+=r.array(ip+off,256)
 va,size=x.sections['.text'];text=x.code(va,size);pos=0
 while True:
  pos=text.find(b'\xe8',pos)
  if pos<0 or pos+5>len(text):break
  dest=va+pos+5+struct.unpack_from('<i',text,pos+1)[0]
  if dest==0x1739900:
   f=x.clip(va+pos);key=f'{va+pos:x} call 0x1739900'
   if key in f['asm']:
    k=f['asm'].index(key);out['formatter_callers'].append({'site':hex(va+pos),'function':f['start'],'context':f['asm'][max(0,k-24):k+4]})
  pos+=1
 r.stable();after=x.guard();assert before==after;out['guard_after']=after;(R/'research/t202_damage_parent_links.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print('FUNCTIONS',[(a,len(v['asm']))for a,v in out['functions'].items()]);print('ARMY_VIRTUALS',[(a,v['slot'],len(v['function']['asm']))for a,v in out['army_virtuals'].items()]);print('PARENT_LINKS',out['plan_type_links']);print('DAMAGE_COUNTERS',out['live_damage_counters']);print('FORMATTER',json.dumps(out['formatter_callers'],indent=2))
finally:x.close()
