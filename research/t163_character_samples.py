import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls,inspect
from gamestate import _pdx_array
try:
 gs=u64(P.base+0x33dd6b0);cm=u64(gs+0x6a8);out={'manager':hex(cm),'class':cls(cm),'arrays':{},'samples':[]}
 for off in (0x10,0x28):out['arrays'][hex(off)]=_pdx_array(P,cm+off)
 ar=out['arrays']['0x28']
 for i in range(min(ar['size'],8)):
  cp=u64(ar['data']+i*8);out['samples'].append(inspect(cp,0x200))
 Path('research/t163_character_samples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('MANAGER',out['class'],out['arrays']);print('SAMPLES',[(r['ptr'],r['class'],r['strings'],[(p['off'],p['class'],p['strings']) for p in r['pointers']],[(x['off'],x['size'],x['first_class']) for x in r['arrays']]) for r in out['samples']])
finally:P.close()
