import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,PEFILE,ptr,u64,cls,inspect
from gamestate import _pdx_array
from handle import resolve_handle
out={'templates':[],'province_links':[],'area_objects':[]}
class Backend:
 image_base=P.base
 def read(self,a,n):return P.read(a,n)
def text(a):
 b=P.try_read(a,32)
 if not b or len(b)!=32:return None
 size,cap=struct.unpack_from('<QQ',b,16)
 if size>1024 or cap<size:return None
 raw=b[:size] if cap<=15 else (P.try_read(struct.unpack_from('<Q',b)[0],size) if size else b'')
 if raw is None or len(raw)!=size:return None
 try:
  s=raw.decode('utf-8');return s if all(x.isprintable() for x in s) else None
 except Exception:return None
try:
 old=json.loads(Path('research/t156_objects.json').read_text(encoding='utf-8'))
 for r in old['templates']:
  a=int(r['ptr'],16);b=P.read(a,0x200);ty,idx=struct.unpack_from('<II',b,8)
  item={'ptr':r['ptr'],'handle_type':ty,'template_id':idx,'name':text(a+0x20),'handle_resolves_back':False,'battalion_slots':[],'support_slots':[]}
  try:item['handle_resolves_back']=resolve_handle(Backend(),ty,idx,P.base)==a
  except Exception as e:item['handle_error']=str(e)
  for offset,label in [(0x68,'battalion_slots'),(0x88,'support_slots')]:
   ar=_pdx_array(P,a+offset)
   if ar and 0<ar['size']<=25:
    for i in range(ar['size']):
     sp=u64(ar['data']+8*i)
     item[label].append({'slot':i,'ptr':hex(sp),'class':cls(sp),'name18':text(sp+0x18) if ptr(sp) else None,'category68':text(sp+0x68) if ptr(sp) else None})
  out['templates'].append(item)
 for r in old['provinces']:
  pp=int(r['ptr'],16);pid=P.u32(pp+0xa4)
  link={'province_id':pid,'terrain_enum38':P.u32(pp+0x38),'a8':inspect(u64(pp+0xa8),0x180),'b8':inspect(u64(pp+0xb8),0x180)}
  out['province_links'].append(link)
 pp=int(old['provinces'][0]['ptr'],16)
 for off in (0xc0,0xd0,0xd8):out['area_objects'].append({'offset':hex(off),'object':inspect(u64(pp+off),0x280)})
 Path('research/t156_template_map_links.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('TEMPLATES',json.dumps(out['templates'],ensure_ascii=False,indent=2))
 print('MAP',json.dumps([{'id':r['province_id'],'enum':r['terrain_enum38'],'a8_strings':r['a8']['strings'],'a8_pointers':r['a8']['pointers'],'b8_strings':r['b8']['strings'],'b8_pointers':r['b8']['pointers']} for r in out['province_links']],ensure_ascii=False,indent=2))
 print('AREAS',json.dumps([{'off':r['offset'],'class':r['object']['class'],'strings':r['object']['strings'],'pointers':r['object']['pointers'],'arrays':[(a['off'],a['size'],a['first_class']) for a in r['object']['arrays']]} for r in out['area_objects']],ensure_ascii=False,indent=2))
finally:P.close()
