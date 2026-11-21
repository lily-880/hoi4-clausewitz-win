from _t203_common import *
x=Runtime()
try:
 before=x.guard();out={'functions':{},'unit_area_samples':[],'manpower_method_candidates':[]}
 for a in(0xeef634,0xc07bf0,0xc08790):out['functions'][hex(a)]=x.clip(a)
 r=x.reader()
 for ap in r.array(x.country+0x290,2048):
  r.require(ap,'CArmy');pp=r.q(ap+0x1f0);area=r.q(pp+0xd0);d={'army_id':r.i(ap+0x1c),'province':hex(pp),'area':hex(area),'special2f8':r.q(ap+0x2f8),'special2e':r.exact(ap+0x2e,1)[0],'raw_country_tags':list(struct.unpack('<ii',r.exact(ap+0x1d8,8)))}
  if area:
   try:d['area_rtti']=x.cls(area)
   except AssertionError:d['area_rtti']=None
   d['raw_u32_3c']=r.i(area+0x3c)
  out['unit_area_samples'].append(d)
 # Static enumerate established CArmyManpower code neighborhood, not heap sweep.
 for st,en,u in x.fns:
  if not 0xcc6400<=st<0xcc8000:continue
  ins=list(x.cs.disasm(x.code(st,en-st),st));writes=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in ins if i.mnemonic in('mov','sub','add')and '['in i.op_str.split(',')[0]and not any(z in i.op_str.split(',')[0]for z in('[rsp','[rbp'))]
  if writes:
   f=x.clip(st);out['manpower_method_candidates'].append({'start':f['start'],'count':len(f['asm']),'writes':writes[:40]})
 r.stable();out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_area_mp_methods.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('FUNCTIONS',[(a,len(v['asm']))for a,v in out['functions'].items()]);print('AREAS',json.dumps(out['unit_area_samples'],indent=2));print('MP_WRITERS',json.dumps(out['manpower_method_candidates'],indent=2))
finally:x.close()
