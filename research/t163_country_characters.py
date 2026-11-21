import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,PEFILE,u64,cls,inspect
from gamestate import _rtti_name_from_vtable
try:
 a=json.loads(Path('research/t163_country_managers.json').read_text(encoding='utf-8'));cp=int(next(x['ptr'] for x in a['country_pointers'] if 'CCountryCharacters' in x['class']),16)
 r=inspect(cp,0x500);r['inline']=[]
 for o in range(0,0x500,8):
  vt=u64(cp+o)
  if not P.base<=vt<P.base+P.image_size:continue
  try:n=_rtti_name_from_vtable(PEFILE,vt-P.base)
  except Exception:n=None
  if n and n.startswith(('.?AV','.?AU')) and n.endswith('@@'):r['inline'].append({'off':hex(o),'class':n})
 Path('research/t163_country_characters.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print('COUNTRY_CHARACTERS',r['inline'],r['strings'],[(p['off'],p['class']) for p in r['pointers']],[(a['off'],a['size'],a['first_class']) for a in r['arrays']])
finally:P.close()
