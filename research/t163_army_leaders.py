import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,PEFILE,u64,cls,inspect
from gamestate import _pdx_array,_rtti_name_from_vtable
out={'leaders':[]}
try:
 cc=int(json.loads(Path('research/t163_country_characters.json').read_text(encoding='utf-8'))['ptr'],16);ar=_pdx_array(P,cc+0x70)
 for i in range(min(ar['size'],20)):
  lp=u64(ar['data']+8*i);r=inspect(lp,0x300);r['inline']=[];r['functions']=[hex(u64(u64(lp)+8*k)-P.base) for k in range(8)]
  for off in range(0,0x300,8):
   vt=u64(lp+off)
   if not P.base<=vt<P.base+P.image_size:continue
   try:n=_rtti_name_from_vtable(PEFILE,vt-P.base)
   except Exception:n=None
   if n and n.startswith(('.?AV','.?AU')) and n.endswith('@@'):r['inline'].append({'off':hex(off),'class':n,'vtable_rva':hex(vt-P.base)})
  out['leaders'].append(r)
 Path('research/t163_army_leaders.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 for r in out['leaders'][:5]:print(r['ptr'],r['class'],'STRINGS',r['strings'],'INLINE',r['inline'],'PTRS',[(p['off'],p['class'],p['strings']) for p in r['pointers']],'ARRAYS',[(a['off'],a['size'],a['first_class']) for a in r['arrays']],'FUNCTIONS',r['functions'])
 print('COUNT',len(out['leaders']))
finally:P.close()
