import sys,struct,json
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,u64,cls,inspect
from gamestate import _pdx_array
out={'states':[],'fronts':[],'unit_formation_offsets':[]}
try:
 a=json.loads(Path('research/t156_objects.json').read_text(encoding='utf-8'));seen=set()
 for r in a['provinces']:
  pp=int(r['ptr'],16);sp=u64(pp+0xc0)
  if sp in seen:continue
  seen.add(sp);b=P.read(sp,0x400)
  row={'ptr':hex(sp),'state_id_58':P.u32(sp+0x58),'index44_hits':[hex(o) for o in range(0,len(b)-3,4) if struct.unpack_from('<i',b,o)[0]==44],'object':inspect(sp,0x400)}
  out['states'].append(row)
 th=int(a['theatres'][0]['ptr'],16);ar=_pdx_array(P,th+0x50)
 for i in range(min(ar['size'],12)):
  out['fronts'].append(inspect(u64(ar['data']+8*i),0x200))
 b=json.loads(Path('research/t156_current_probe.json').read_text(encoding='utf-8'))
 for u in b['units']:
  ap=int(u['ptr'],16);blob=P.read(ap+0x280,0x70)
  out['unit_formation_offsets'].append({'unit_id':u['unit_id'],'hex280_2f0':blob.hex()})
 Path('research/t156_states_fronts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('STATES',[(r['state_id_58'],r['index44_hits'],[(x['off'],x['size'],x['first_class']) for x in r['object']['arrays']],[(p['off'],p['class']) for p in r['object']['pointers']]) for r in out['states']])
 print('FRONTS',[(r['ptr'],r['class'],r['strings'],[(x['off'],x['size'],x['first_class']) for x in r['arrays']],[(p['off'],p['class']) for p in r['pointers']]) for r in out['fronts']])
finally:P.close()
