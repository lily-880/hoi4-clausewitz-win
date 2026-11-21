import os,sys,struct,json
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0';os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from mem import Proc,find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable,_pdx_array
P=Proc(find_pid('hoi4.exe')); PEFILE=PE(P.image_path)
def ptr(x):return isinstance(x,int) and 0x10000<x<0x7fffffffffff
def u64(a):
 b=P.try_read(a,8);return struct.unpack('<Q',b)[0] if b and len(b)==8 else None
def cls(a):
 if not ptr(a):return None
 vt=u64(a)
 if not vt or not P.base<=vt<P.base+P.image_size:return None
 try:
  n=_rtti_name_from_vtable(PEFILE,vt-P.base)
  return n if n and n.startswith(('.?AV','.?AU')) and n.endswith('@@') else None
 except Exception:return None
def strings(a,n):
 b=P.try_read(a,n) or b''; result=[]
 import re
 for m in re.finditer(rb'[\x20-\x7e]{4,}\x00',b):
  if any(65<=v<=90 or 97<=v<=122 for v in m.group()):result.append({'off':hex(m.start()),'text':m.group()[:-1].decode('ascii')})
 return result
def inspect(a,n):
 b=P.try_read(a,n) or b''; result={'ptr':hex(a),'class':cls(a),'hex':b.hex(),'strings':strings(a,n),'pointers':[],'arrays':[]}
 for off in range(0,len(b)-7,8):
  v=struct.unpack_from('<Q',b,off)[0]
  if ptr(v):
   nm=cls(v)
   if nm and 'Allocator' not in nm:result['pointers'].append({'off':hex(off),'ptr':hex(v),'class':nm,'strings':strings(v,0x80)})
  if off+16<=len(b):
   cap,size=struct.unpack_from('<II',b,off+8)
   if ptr(v) and 0<size<=cap<=10000:
    if size>128:continue
    elems=P.try_read(v,min(size*8,512))
    if elems:
     first=struct.unpack_from('<Q',elems)[0] if len(elems)>=8 else None
     result['arrays'].append({'off':hex(off),'data':hex(v),'size':size,'cap':cap,'first_class':cls(first),'hex':elems.hex()})
 return result
if __name__=='__main__':
 a=json.loads(Path('research/t156_current_probe.json').read_text(encoding='utf-8'))
 out={'pid':P.pid,'complete_input':False,'theatres':[],'templates':[],'provinces':[],'officers':[],'subunits':[],'units':[]}
 try:
  for kind in ('theatres','templates'):
   ar=a[kind]
   for i in range(min(ar['size'],16)):out[kind].append(inspect(u64(ar['data']+8*i),0x380))
  seen=set();sd=set()
  for u in a['units']:
   ap=int(u['ptr'],16)
   pp=u64(ap+0x1f0)
   if pp not in seen:out['provinces'].append(inspect(pp,0x500));seen.add(pp)
   op=u64(ap+0x568)
   if u['leader_id']>=0:out['officers'].append({'unit_id':u['unit_id'],'leader_id':u['leader_id'],'object':inspect(op,0x120)})
   sp=u64(ap+0x138)
   if sp not in sd:out['subunits'].append(inspect(sp,0x300));sd.add(sp)
   if len(out['units'])<3:out['units'].append(inspect(ap,0x690))
  Path('research/t156_objects.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
  brief={k:[{kk:vv for kk,vv in r.items() if kk not in ('hex','arrays')} for r in out[k]] for k in ('theatres','templates')}
  brief['provinces']=[{'ptr':r['ptr'],'pointers':r['pointers'],'strings':r['strings']} for r in out['provinces']]
  brief['officers']=out['officers']
  print(json.dumps(brief,ensure_ascii=False,indent=2))
 finally:P.close()
