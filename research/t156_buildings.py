import sys,json
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,u64,cls,inspect
from gamestate import _pdx_array
out={'buildings':[]}
try:
 old=json.loads(Path('research/t156_states_fronts.json').read_text(encoding='utf-8'));seen=set()
 for state in old['states']:
  sp=int(state['ptr'],16)
  ar=_pdx_array(P,sp+0x158)
  if not ar or not 0<=ar['size']<=56:continue
  for i in range(ar['size']):
   bp=u64(ar['data']+8*i)
   if bp in seen:continue
   seen.add(bp)
   if cls(bp)!='.?AVCBuilding@@':continue
   row={'state_id':state['state_id_58'],'object':inspect(bp,0x90)}
   out['buildings'].append(row)
 Path('research/t156_buildings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,ensure_ascii=False,indent=2))
finally:P.close()
