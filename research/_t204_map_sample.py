from _t204_common import *
from _t203_delivery_reader import tag_index,robin_lookup
from input_observation import ObservationError
x=Runtime()
try:
 b=x.guard();r=x.reader();aps=set(r.array(x.country+0x290,2048))
 for cp in r.array(x.gs+0x268,4096):
  for o in(0x28,0x30):aps.update(r.array(r.q(cp+o)+0xe8,128))
 pairs=set()
 for ap in aps:
  pp=r.q(ap+0x1f0);r.require(pp,'CProvince');tag=r.i(ap+0x1dc);tag=tag if tag>0 else r.i(ap+0x1d8);pairs.add((tag,r.q(pp+0xd0)))
 out={'scope':'independent current-area port/map structure reads, NOT forcing delivery_possible branch or changing game','pairs':[],'errors':[],'schema_emission':False};naval=r.q(x.gs+0x698);supply=r.q(x.gs+0x3d8);tab=r.q(supply+0x108)
 for tag,area in sorted(pairs):
  try:
   r.require(area,'CControllerArea');idx=tag_index(r,x.gs,tag);graph=r.q(tab+idx*8);route_map=r.q(graph+0x80);assert route_map>=0x10000;row={'tag':tag,'area':hex(area),'graph':hex(graph),'route_map':hex(route_map),'mask':r.i(route_map+0x34),'ports':[],'provinces_checked':0}
   for pp in r.array(area+0xb0,16384):
    r.require(pp,'CProvince');pid=r.i(pp+0xa4);row['provinces_checked']+=1;ptr=robin_lookup(r,naval,pid,24,4,8,16,True)
    if ptr:row['ports'].append({'province_id':pid,'naval_base_ptr':hex(ptr),'route':robin_lookup(r,route_map,pid,12,0,4,8)})
   out['pairs'].append(row)
  except(AssertionError,ObservationError)as e:out['errors'].append({'tag':tag,'area':hex(area),'error':str(e)})
 r.stable();out['guard_after']=x.guard();assert out['guard_after']==b;(R/'research/t204_existing_port_map_audit.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
