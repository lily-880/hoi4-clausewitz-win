import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,cls,u64,inspect
from handle import resolve_handle
class B:
 image_base=P.base
 def read(self,a,n):return P.read(a,n)
out={'terrains':[],'handle_results':[],'definitions':[]}
try:
 old=json.loads(Path('research/t156_template_map_links.json').read_text(encoding='utf-8'));seen=set()
 for r in old['province_links']:
  a=int(r['b8']['ptr'],16);tp=u64(a+0xa8)
  if tp not in seen:out['terrains'].append(inspect(tp,0x180));seen.add(tp)
  row={'province_id':r['province_id'],'definition_ptr':hex(a),'prefix_words':{hex(i):hex(P.u64(a+i)) for i in range(0,0xc0,8)},'arrays':r['b8']['arrays']}
  out['definitions'].append(row)
 for r in old['templates']:
  try:
   resolved=resolve_handle(B(),r['handle_type'],r['template_id'],P.base)
   out['handle_results'].append({'id':r['template_id'],'object':r['ptr'],'resolved':hex(resolved) if resolved else None,'delta':resolved-int(r['ptr'],16) if resolved else None,'class':cls(resolved)})
  except Exception as e:out['handle_results'].append({'error':str(e)})
 Path('research/t156_terrain_handle.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('TERRAIN',json.dumps([{'ptr':r['ptr'],'class':r['class'],'strings':r['strings'],'pointers':r['pointers']} for r in out['terrains']],ensure_ascii=False,indent=2))
 print('HANDLES',out['handle_results']);print('DEFS',json.dumps(out['definitions'][:2],indent=2))
finally:P.close()
