import os,sys,json,struct,time
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0';os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
from mem import Proc,find_pid
from pe import PE
import offsets as O
from gamestate import _rtti_name_from_vtable,detect_session,read_campaign_summary,resolve_player_country,_pdx_array
p=Proc(find_pid('hoi4.exe'));pe=PE(p.image_path)
def ptr(x):return isinstance(x,int) and 0x10000<x<0x7fffffffffff
def cls(a):
 if not ptr(a):return None
 b=p.try_read(a,8)
 if not b:return None
 vt=struct.unpack('<Q',b)[0]
 if not p.base<=vt<p.base+p.image_size:return None
 try:return _rtti_name_from_vtable(pe,vt-p.base)
 except Exception:return None
def view(a,n):
 blob=p.try_read(a,n) or b''
 out=[]
 for off in range(0,len(blob)-7,8):
  v=struct.unpack_from('<Q',blob,off)[0]
  if ptr(v):
   nm=cls(v)
   if nm and nm.startswith(('.?AV','.?AU')):out.append({'offset':hex(off),'ptr':hex(v),'class':nm})
 return out
out={'pid':p.pid,'version':'1.19.5.0.7c6c','read_only':True,'complete_input':False}
try:
 out['session']=detect_session(p,pe)
 if not out['session']['in_game']:raise RuntimeError('not in game')
 gs=p.u64(p.base+O.WINDOWS_GLOBALS['G_GAMESTATE'])
 out['gs_class']=cls(gs)
 samples=[]
 for i in range(3):
  samples.append({'tick':p.u32(gs+0x468),'progress':struct.unpack('<f',p.read(gs+0x4b8,4))[0],'speed_index':struct.unpack('<i',p.read(gs+0x4bc,4))[0]})
  if i<2:time.sleep(.7)
 out['clock_samples']=samples
 if any(s['speed_index']!=0 for s in samples):raise RuntimeError('setting not 1x: stop; no speed changes')
 out['clock_stable_observed']=len({(s['tick'],s['progress']) for s in samples})==1
 out['summary']=read_campaign_summary(p,gs)
 res=resolve_player_country(p,gs);out['player']=res
 if not res['ok'] or not res['source'].startswith('gs_0x520'):raise RuntimeError('no current player proof')
 co=int(res['country_ptr'],16);out['country_class']=cls(co)
 arr=_pdx_array(p,co+0x290);out['armies_array']=arr
 if not arr or not 0<=arr['size']<=4096:raise RuntimeError('invalid array')
 units=[]
 for i in range(arr['size']):
  ap=p.u64(arr['data']+8*i)
  blob=p.read(ap,0x690)
  rec={'ptr':hex(ap),'class':cls(ap),'vtable_rva':hex(struct.unpack_from('<Q',blob)[0]-p.base),'unit_id':struct.unpack_from('<I',blob,0x1c)[0],'handle_type':struct.unpack_from('<I',blob,0x18)[0],'province_id':struct.unpack_from('<I',blob,0x28)[0],'owner':struct.unpack_from('<i',blob,0x1e0)[0],'fixed':{hex(o):struct.unpack_from('<i',blob,o)[0]/100000 for o in (0x40,0x420,0x428,0x468,0x4a0,0x4f0)},'leader_id':struct.unpack_from('<i',blob,0x564)[0]}
  pp=struct.unpack_from('<Q',blob,0x1f0)[0];rec['province_class']=cls(pp);rec['province_crosscheck']=p.u32(pp+0xa4) if ptr(pp) else None
  rec['pointers']=view(ap,0x690) if i<3 else []
  rec['path_array']=_pdx_array(p,ap+0x200)
  units.append(rec)
 out['units']=units
 out['country_pointers']=view(co,0x700)
 out['combats']=_pdx_array(p,gs+0x268)
 out['theatres']=_pdx_array(p,co+0x168)
 out['templates']=_pdx_array(p,co+0x1b8)
 out['country_blob_hex']=p.read(co,0x700).hex()
 out['gs_blob_hex']=p.read(gs,0x700).hex()
 out['clock_tick_after']=p.u32(gs+0x468)
except Exception as e:out['error']=str(e)
finally:
 p.close();Path('research/t156_current_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in out.items() if k not in ('country_blob_hex','gs_blob_hex','summary','units','country_pointers')},ensure_ascii=False,indent=2))
 if 'units' in out:print('UNITS',json.dumps(out['units'],ensure_ascii=False,indent=2))
 if 'country_pointers' in out:print('COUNTRY_PTRS',json.dumps(out['country_pointers'],ensure_ascii=False,indent=2))
