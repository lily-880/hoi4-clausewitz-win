import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P
from gamestate import _pdx_array
out=[]
try:
 for u in json.loads(Path('research/t156_current_probe.json').read_text(encoding='utf-8'))['units']:
  ap=int(u['ptr'],16);r={'unit_id':u['unit_id']}
  for label,off in [('army_manpower_value',0x3e0),('army_manpower_need',0x400)]:
   ar=_pdx_array(P,ap+off);assert ar and ar['size']<=32
   r[label]=[{'country_index':ci,'amount':n} for ci,n in struct.iter_unpack('<ii',P.read(ar['data'],ar['size']*8))]
  out.append(r)
 Path('research/t165_manpower_value_need_live.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out[:5],indent=2));print('CURRENT_SUM',sum(x['amount'] for r in out for x in r['army_manpower_value']),'NEED_SUM',sum(x['amount'] for r in out for x in r['army_manpower_need']))
finally:P.close()
