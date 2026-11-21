import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls,inspect
out={'country_pointers':[],'gs_pointers':[],'manpower':{}}
try:
 gs=u64(P.base+0x33dd6b0);co=int(json.loads(Path('research/t156_current_probe.json').read_text(encoding='utf-8'))['player']['country_ptr'],16)
 for label,base,size in [('country_pointers',co,0x1710),('gs_pointers',gs,0x750)]:
  b=P.read(base,size)
  for o in range(0,size-7,8):
   v=struct.unpack_from('<Q',b,o)[0]
   if not 0x10000<v<0x7fffffffffff:continue
   cn=cls(v)
   if cn and any(s in cn for s in ('Leader','Army','War','Character','Equipment','Supply','Manpower')):
    out[label].append({'off':hex(o),'ptr':hex(v),'class':cn})
 mp=co+0x328;vt=u64(mp);out['manpower']={'ptr':hex(mp),'class':cls(mp),'hex':P.read(mp,0x28).hex(),'functions':[hex(u64(vt+i*8)-P.base) for i in range(8)]}
 Path('research/t163_country_managers.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:P.close()
