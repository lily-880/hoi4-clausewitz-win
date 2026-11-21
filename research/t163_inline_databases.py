import sys,struct,json
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,PEFILE,u64,cls
from gamestate import _pdx_array,_rtti_name_from_vtable
out={'countries':[],'gamestate_inline':[]};cache={}
def inline(blob):
 result=[]
 for o in range(0,len(blob)-7,8):
  vt=struct.unpack_from('<Q',blob,o)[0]
  if not P.base<=vt<P.base+P.image_size:continue
  if vt not in cache:
   try:n=_rtti_name_from_vtable(PEFILE,vt-P.base)
   except Exception:n=None
   cache[vt]=n if n and n.startswith(('.?AV','.?AU')) and n.endswith('@@') else None
  if cache[vt]:result.append({'off':hex(o),'class':cache[vt],'vtable_rva':hex(vt-P.base)})
 return result
try:
 gs=u64(P.base+0x33dd6b0);cs=_pdx_array(P,gs+0x310)
 for idx in (44,0,20):
  co=u64(cs['data']+idx*8)
  if cls(co)!='.?AVCCountry@@':continue
  out['countries'].append({'index':idx,'ptr':hex(co),'inline':inline(P.read(co,0x3000))})
 out['gamestate_inline']=inline(P.read(gs,0x1800))
 Path('research/t163_inline_databases.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print(json.dumps(out,indent=2))
finally:P.close()
