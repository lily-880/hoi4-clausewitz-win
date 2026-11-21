import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls
from gamestate import _pdx_array
out={'read_only':True,'research_only_foreign_objects_not_exported':True,'theatres':0,'groups':[],'nonempty_counts':{},'bounds':{'countries':512,'theatres_per_country':8,'groups_per_theatre_kind':128,'detailed_samples':24},'errors':[]}
try:
 gs=u64(P.base+0x33dd6b0);ar=_pdx_array(P,gs+0x310);assert ar and ar['size']<=512
 for ci in range(ar['size']):
  co=u64(ar['data']+8*ci)
  if cls(co)!='.?AVCCountry@@':continue
  th=_pdx_array(P,co+0x168)
  if not th or not 0<=th['size']<=8:continue
  for j in range(th['size']):
   tp=u64(th['data']+j*8)
   if cls(tp)!='.?AVCTheatre@@':out['errors'].append({'country':ci,'bad_theatre':hex(tp or 0)});continue
   out['theatres']+=1
   for label,off in [('orders_group',0x80),('field_marshal_group',0x98),('theater_group',0xc8)]:
    gr=_pdx_array(P,tp+off)
    if not gr or not 0<=gr['size']<=128:continue
    out['nonempty_counts'][label]=out['nonempty_counts'].get(label,0)+gr['size']
    for k in range(min(gr['size'],24-len(out['groups']))):
     gp=u64(gr['data']+k*8);vt=u64(gp)
     out['groups'].append({'country_index':ci,'theatre_ptr':hex(tp),'kind':label,'ptr':hex(gp),'class':cls(gp),'vtable':hex(vt-P.base),'functions':[hex(x[0]-P.base) for x in struct.iter_unpack('<Q',P.read(vt,0x48))]})
 out['combat_array']=_pdx_array(P,gs+0x268);out['pid']=P.pid
 Path('research/t165_world_formation_inventory.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:P.close()
