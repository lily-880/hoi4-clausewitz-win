import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls
out=[]
try:
 for row in json.loads(Path('research/t156_current_probe.json').read_text(encoding='utf-8'))['units']:
  ap=int(row['ptr'],16);a=ap+0x3d0;r={'unit_id':row['unit_id'],'class':cls(a),'hex':P.read(a,0x48).hex(),'ratio610':struct.unpack('<q',P.read(ap+0x610,8))[0]/100000,'max_supply600':struct.unpack('<q',P.read(ap+0x600,8))[0]/100000}
  if not out and r['class']:r['functions']=[hex(x[0]-P.base) for x in struct.iter_unpack('<Q',P.read(u64(a),0x48))]
  out.append(r)
 Path('research/t165_army_manpower_supply.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out[:2],indent=2));print('RATIOS',sorted(set(r['ratio610'] for r in out)))
finally:P.close()
