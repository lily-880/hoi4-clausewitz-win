raise SystemExit('ARCHIVED UNSAFE LIVE REPRO: t201 read-only phase; do not execute this historical writer')
import sys,json,struct,time,traceback
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
from command_receipt import retain_unpaused_risk
import _t197_setpath_zero_post as h
import _t196_scaffold_and_validate as old
out={'authorized_by':['pt183u']};h.close_gates();pid=h.mem_find_pid('hoi4.exe');assert pid==12948
p=h.Proc(pid);pe=h.PE(h.EXE);b=h.Backend();s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16)
def date():return (h.read_campaign_summary(p,gs).get('verified') or {}).get('date_full')
def snap():
 u=old.find_unit(p,co,1829);d=old.snap_unit(p,pe,u);d['progress_raw_u32']=struct.unpack('<I',p.read(u+0x240,4))[0];return d
def make(rva,vt,size,valid,writes):
 cmd,fr=h.factory_make(pid,b,rva,vt,size);assert cmd
 for off,data in writes:h.mo._write(pid,cmd+off,data)
 dry=h.dry_isvalid(pid,b,valid,cmd);assert dry['isvalid']==1
 return cmd,{'factory':fr,'dry':dry}
def post(cmd,note):
 r=h.do_post(pid,b,cmd,note);out.setdefault('posts',[]).append({'note':note,**r});health=h.process_health(pid);out['health']=health
 if r['wait']!=0 or not health['alive']:raise RuntimeError('POST_TIMEOUT_OR_DEAD_STOP')
 assert r['post_rax']==1
 return r
pausecmd=None;unpaused=False
try:
 assert p.read(idler+0x6c1,1)==b'\1';assert struct.unpack('<I',p.read(gs+0x4bc,4))[0]==0
 out['date_before']=date();out['before']=snap();gp,ins=h.find_group(p,pe,co,(53,1));out['plan1_before']=ins
 cmd,info=make(0x18d00e0,0x2a85d60,0x38,0x18defb0,[(0x28,struct.pack('<II',53,1)),(0x30,struct.pack('<I',1)),(0x34,b'\0\0')]);out['stop_execute_bind']=info
 post(cmd,'t198 plan1 execute_order=0 pt183u')
 out['plan1_stopped']=h.find_group(p,pe,co,(53,1))[1];assert out['plan1_stopped'][0]['can_execute_248']==0
 # verify all observed plans stopped
 for th in h.ptr_array(p,co+0x168,64):
  for g in h.ptr_array(p,th+0x80,256):
   for off in (0x98,0xb0,0xc8):
    for ip in h.ptr_array(p,g+off,256):assert p.read(ip+0x248,1)==b'\0'
 assert out['before']['path']==[8036], 'MOVE_CONTRAST_GONE_STOP'
 pausecmd,pinfo=make(0xe53a00,0x29e6e10,0x50,0x188d90,[(0x48,b'\1\0')]);out['repause_prepared']=pinfo
 uncmd,uinfo=make(0xe53a00,0x29e6e10,0x50,0x188d90,[(0x48,b'\0\0')]);out['unpause_prepared']=uinfo
 unpaused=True;post(uncmd,'t198 official 1x short move contrast pt183u')
 t=time.monotonic();tick0=out['date_before']['hour_tick'];polls=[]
 while time.monotonic()-t<8:
  d=snap();dt=date();polls.append({'elapsed':round(time.monotonic()-t,3),'date':dt,'unit':d})
  if d['commandlist_size'] or d['full_path'] or d['progress_raw_u32']!=out['before']['progress_raw_u32'] or dt['hour_tick']>tick0:break
  time.sleep(.05)
 post(pausecmd,'t198 restore official pause immediately pt183u')
 out['polls']=polls;out['after']=snap();out['date_after']=date();out['pause']=p.read(idler+0x6c1,1)[0]
 unpaused=retain_unpaused_risk(was_unpaused=unpaused,observed_pause=out['pause'])
 assert out['pause']==1
 out['gs_combats_pdx']=list(h.pdx(p,gs+0x268))
except Exception:
 out['exception']=traceback.format_exc()
 # The posted object's lifecycle has ended; never reuse its pointer.
 out['containment_required']=bool(unpaused)
 out['automatic_retry_disabled']=True
 # Offline audit only: no recovery actuator in the historical exception path.

finally:
 h.close_gates();out['allow_post']=h.allow_post();p.close();(R/'research/t198_order_sample.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
