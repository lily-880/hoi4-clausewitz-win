import os,sys,json,hashlib,struct,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,'calling')
import offsets as O
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,read_campaign_summary,resolve_player_country,_pdx_array
from input_observation import observe_own_divisions
out={'captured_at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5),'EST')).isoformat(),'complete_input':False,'read_only':True}
p=Proc(find_pid('hoi4.exe'))
try:
 out.update(pid=p.pid,base=hex(p.base),exe=p.image_path)
 h=hashlib.sha256()
 with open(p.image_path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 out['sha256']=h.hexdigest().upper()
 out['version_matches']=out['sha256']==O.TARGET['exe_sha256_1_19_4']
 if not out['version_matches']:raise RuntimeError('executable fingerprint changed')
 pe=PE(p.image_path)
 out['session']=detect_session(p,pe)
 if not out['session']['in_game']:raise RuntimeError('not in campaign map; no gameplay reads performed')
 gs=p.u64(p.base+O.WINDOWS_GLOBALS['G_GAMESTATE'])
 out['gs']=hex(gs)
 out['summary']=read_campaign_summary(p,gs)
 resolved=resolve_player_country(p,gs)
 out['player']=resolved
 if not resolved['ok'] or not resolved['source'].startswith('gs_0x520'):raise RuntimeError('current player not reliably resolved')
 samples=[]
 for i in range(3):
  raw=p.read(gs+0x468,0x5c)
  samples.append({'hour_tick':struct.unpack_from('<I',raw)[0],'progress':struct.unpack_from('<f',raw,0x50)[0],'speed_index':struct.unpack_from('<i',raw,0x54)[0]})
  if i<2:time.sleep(0.8)
 out['clock_samples']=samples
 out['clock_observed_stable']=len({(s['hour_tick'],s['progress']) for s in samples})==1
 out['speed_claim']='unresolved_pause; setting_only'
 if any(s['speed_index']!=0 for s in samples):raise RuntimeError('UI speed setting exceeds 1x; not modified; stop live research')
 before=p.read(gs+0x468,0x60)
 co=int(resolved['country_ptr'],16)
 out['observation']=observe_own_divisions(p.read,co,resolved['player_index'],carmy_vtable=p.base+O.PROVEN_STATIC['CArmy_vtable'],version_verified=True)
 after=p.read(gs+0x468,0x60)
 out['clock_header_consistent']=before==after
 out['current_counts']={'divisions':len(out['observation']['world']['own_units'])}
 for name,addr in [('theatres',co+O.HYPOTHESIS_STRUCT['CO_THEATRES']),('templates',co+O.HYPOTHESIS_STRUCT['CO_DIV_TEMPLATES']),('combats',gs+O.HYPOTHESIS_STRUCT['GS_COMBATS'])]:
  out[name]=_pdx_array(p,addr)
 out['status']='live_core_collector_accepted' if out['clock_header_consistent'] else 'inconsistent_clock_rejected'
except Exception as e:
 out['error']=str(e)
 out['status']='stopped'
finally:
 p.close()
 Path('research/t156_live_preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in out.items() if k not in ('summary','observation')},ensure_ascii=False,indent=2))
 if 'observation' in out: print(json.dumps(out['observation']['world'],ensure_ascii=False,indent=2))
