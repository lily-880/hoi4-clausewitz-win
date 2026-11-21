import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,cls,u64
from gamestate import _pdx_array
out={'country_arrays':[],'own_province_membership':[]}
try:
 a=json.loads(Path('research/t156_current_probe.json').read_text(encoding='utf-8'));co=int(a['player']['country_ptr'],16)
 for off in range(0x500,0x5a1,8):
  ar=_pdx_array(P,co+off)
  if not ar or not 0<ar['size']<=ar['capacity']<=5000:continue
  first=u64(ar['data'])
  cn=cls(first)
  if cn:out['country_arrays'].append({'off':hex(off),'size':ar['size'],'class':cn,'first':hex(first)})
 for off in (0x548,0x560):
  ar=_pdx_array(P,co+off)
  if not ar or not 0<ar['size']<=100:continue
  for i in range(ar['size']):
   area=u64(ar['data']+8*i);cn=cls(area)
   if cn not in ('.?AVCControllerArea@@','.?AVCOwnerArea@@'):continue
   provinces=_pdx_array(P,area+0x30)
   if not provinces or not 0<provinces['size']<=1000:continue
   ids=[]
   for j in range(provinces['size']):
    pp=u64(provinces['data']+8*j)
    if cls(pp)!='.?AVCProvince@@':raise RuntimeError('not province member')
    ids.append(P.u32(pp+0xa4))
   out['own_province_membership'].append({'off':hex(off),'area':hex(area),'class':cn,'count':len(ids),'province_ids':ids})
 Path('research/t156_country_areas.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,ensure_ascii=False,indent=2))
finally:P.close()
