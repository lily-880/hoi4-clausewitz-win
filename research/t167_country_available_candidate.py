import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls
from gamestate import _pdx_array
out={}
try:
 gs=u64(P.base+0x33dd6b0);ca=_pdx_array(P,gs+0x310);co=u64(ca['data']+44*8);ar=_pdx_array(P,co+0x460);out={'country':hex(co),'array':ar,'states':[],'central_current':P.u32(co+0x334)};assert ar and ar['size']<=1000
 for j in range(ar['size']):
  sp=u64(ar['data']+j*8);r={'ptr':hex(sp),'class':cls(sp),'state_id':P.u32(sp+0x58),'state848':P.u32(sp+0x848)}
  if not out['states']:
   r['vtable_functions']=[hex(x[0]-P.base) for x in struct.iter_unpack('<Q',P.read(u64(sp),0x48))]
  out['states'].append(r)
 out['computed_d5dae0']=out['central_current']+sum(x['state848'] for x in out['states']);Path('research/t167_country_available_candidate.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:P.close()
