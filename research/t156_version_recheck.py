import os,sys,re,json,struct
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0';os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from mem import Proc,find_pid
from pe import PE
import offsets as O
from gamestate import _rtti_name_from_vtable,detect_session
p=Proc(find_pid('hoi4.exe'))
try:
 pe=PE(p.image_path)
 out={'pid':p.pid,'pe':pe.summary(),'strings':[],'static_rtti':{},'globals':{}}
 for match in re.finditer(rb'(?:1\.(?:19|20)\.[0-9]+(?:\.[0-9]+)?|Operation Postern)',pe.data):
  if len(out['strings'])>=40:break
  a=max(0,match.start()-35);b=min(len(pe.data),match.end()+50)
  out['strings'].append({'offset':hex(match.start()),'context':pe.data[a:b].decode('ascii','backslashreplace')})
 for name in ('CGameState_vtable','CCurrentGameState_vtable','CArmy_vtable','CInGameIdler_vtable','CFrontEndIdler_vtable','CArmyGroup_vtable'):
  rva=O.PROVEN_STATIC[name]
  try:out['static_rtti'][name]={'rva':hex(rva),'class':_rtti_name_from_vtable(pe,rva)}
  except Exception as e:out['static_rtti'][name]={'error':str(e)}
 for name in ('G_GAMESTATE','G_IDLER'):
  rva=O.WINDOWS_GLOBALS.get(name)
  if not isinstance(rva,int):continue
  ptr=p.u64(p.base+rva)
  row={'rva':hex(rva),'ptr':hex(ptr)}
  if 0x10000<ptr<0x7fffffffffff:
   b=p.try_read(ptr,8)
   if b:
    vt=struct.unpack('<Q',b)[0];row['vtable']=hex(vt);row['vtable_rva']=hex(vt-p.base)
    if p.base<vt<p.base+p.image_size:
     try:row['class']=_rtti_name_from_vtable(pe,vt-p.base)
     except Exception as e:row['error']=str(e)
  out['globals'][name]=row
 # Classification only: no campaign reads when new binary layouts differ.
 if out['globals'].get('G_IDLER',{}).get('class'):
  out['session']=detect_session(p,pe)
 Path('research/t156_version_recheck.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in out.items() if k!='pe'},ensure_ascii=False,indent=2))
 print('PE',pe.size_of_image,len(pe.data))
finally:p.close()
