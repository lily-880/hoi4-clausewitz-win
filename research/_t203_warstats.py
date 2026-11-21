from _t203_common import *
from _t203_delivery_reader import tag_index
x=Runtime()
try:
 b=x.guard();r=x.reader();own=set(r.array(x.country+0x290,2048));others=set()
 for cp in r.array(x.gs+0x268,4096):
  for off in(0x28,0x30):others.update(r.array(r.q(cp+off)+0xe8,128))
 tags=sorted({r.i(ap+off)for ap in others-own for off in(0x1d8,0x1dc,0x1e0)if r.i(ap+off)>0});d=r.q(x.country+0xf88);r.require(d,'CDiplomacyStatus');rels=r.array(d+8,4096);out=[]
 for tag in tags:
  idx=tag_index(r,x.gs,tag);assert idx<len(rels);rel=rels[idx];item={'opponent_tag':tag,'index':idx,'relation':hex(rel),'relation_class':x.cls(rel)};war=r.q(rel+0x2e8);item['war_ptr']=hex(war)
  if war:item.update({'war_class':x.cls(war),'side_tags':[r.i(war+0x10),r.i(war+0x14)],'flag49':r.exact(war+0x49,1)[0],'raw_u64_50_58':list(struct.unpack('<QQ',r.exact(war+0x50,16)))})
  out.append(item)
 r.stable();assert x.guard()==b;(R/'research/t203_existing_war_loss_candidates.json').write_text(json.dumps({'schema_emission':False,'records':out},indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
