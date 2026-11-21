"""Research-only pure reads reproducing E64C50; no official calls or schema emission."""
import struct
from input_observation import ObservationError

def scalar_array(r,a,stride,bound):
 p,cap,n=struct.unpack('<QII',r.exact(a,16))
 if not 0<=n<=cap<=bound or(n and p<0x10000):raise ObservationError('bad scalar array')
 return p,n

def tag_index(r,gs,tag):
 if tag==0:return 0
 p,n=scalar_array(r,gs+0x340,4,16384)
 if not 0<tag<n:raise ObservationError('tag bounds')
 v=r.i(p+tag*4)
 if not 0<=v<4096:raise ObservationError('country index bounds')
 return v

def robin_lookup(r,a,key,stride,probe_off,key_off,value_off,value64=False):
 p=r.q(a+0x28);mask=r.i(a+0x34);maxprobe=r.exact(a+0x38,1)[0]
 if mask<0 or mask>1048575 or mask&(mask+1)or p<0x10000:raise ObservationError('bad hash table')
 h=key&0xffffffff
 for _ in range(2):h=((h^(h>>16))*0x45d9f3b)&0xffffffff
 bucket=(h^(h>>16))&mask;distance=1;end=mask+maxprobe+1
 for _ in range(255):
  if bucket>=end:raise ObservationError('hash probe outside sentinel')
  row=p+bucket*stride;probe=r.exact(row+probe_off,1)[0]
  if distance>probe:return None
  if r.i(row+key_off)==key:
   return r.q(row+value_off)if value64 else r.i(row+value_off)
  bucket+=1;distance+=1
 raise ObservationError('hash probe bound')

def main_area(r,gs,country):
 sid=r.i(country+0x1018)
 if sid==0:return 0,{'capital_state_id':0}
 states=r.array(gs+0x2c8,8192)
 if not 1<=sid<len(states):raise ObservationError('capital state bounds')
 st=states[sid];r.require(st,'CState');owner=r.i(country+8);idx=tag_index(r,gs,owner);best=0;weight=0;ev=[]
 for pp in r.array(st+0x18,16384):
  r.require(pp,'CProvince');tag=r.i(pp+0x188)
  if tag!=owner and(not tag or not owner or tag_index(r,gs,tag)!=idx):continue
  area=r.q(pp+0xd0)
  if not area:continue
  r.require(area,'CControllerArea');w=r.i(area+0x3c);ev.append({'province':hex(pp),'area':hex(area),'weight':w})
  if w>weight:best=area;weight=w
 return best,{'capital_state_id':sid,'eligible_areas':ev,'main_area':hex(best)}

def delivery_possible(r,gs,army):
 r.require(army,'CArmy');special=r.q(army+0x2f8);cached=r.exact(army+0x2e,1)[0]
 if cached not in(0,1):raise ObservationError('nonboolean consumer flag')
 if special or cached:return True,{'branch':'special2f8'if special else 'flag2e','special2f8':hex(special),'flag2e':cached}
 pp=r.q(army+0x1f0);r.require(pp,'CProvince');area=r.q(pp+0xd0)
 if area:r.require(area,'CControllerArea')
 tag=r.i(army+0x1dc)
 if tag<=0:tag=r.i(army+0x1d8)
 idx=tag_index(r,gs,tag);countries=r.array(gs+0x310,4096)
 if not idx<len(countries):raise ObservationError('country bounds')
 country=countries[idx];r.require(country,'CCountry');main,ev=main_area(r,gs,country);ev.update({'country_index':idx,'area':hex(area)})
 if area==main:ev['branch']='main_area';return True,ev
 if not area:ev['branch']='no_area';return False,ev
 supply=r.q(gs+0x3d8);graph_table=r.q(supply+0x108);graph=r.q(graph_table+idx*8)
 if graph<0x10000:raise ObservationError('missing country supply graph')
 route_map=r.q(graph+0x80)
 if route_map<0x10000:raise ObservationError('missing delivery route map')
 ports=[];naval=r.q(gs+0x698)
 for port in r.array(area+0xb0,16384):
  r.require(port,'CProvince');pid=r.i(port+0xa4);present=robin_lookup(r,naval,pid,24,4,8,16,True)
  if not present:continue
  route=robin_lookup(r,route_map,pid,12,0,4,8);ports.append({'province_id':pid,'naval_base_ptr':hex(present),'route':route})
  if route is not None and route>=0:ev.update({'branch':'reachable_port','ports':ports});return True,ev
 ev.update({'branch':'blocked','ports':ports});return False,ev
