import sys,json,struct,time
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
import _t197_setpath_zero_post as h
pid=h.mem_find_pid('hoi4.exe');assert pid==12948;p=h.Proc(pid);pe=h.PE(h.EXE);b=h.Backend();s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16)
out={'before':p.read(idler+0x6c1,1)[0]};h.close_gates()
try:
 if out['before']!=1:
  cmd,fr=h.factory_make(pid,b,0xe53a00,0x29e6e10,0x50);assert cmd
  h.mo._write(pid,cmd+0x48,b'\1\0');out['factory']=fr;out['raw']=p.read(cmd,0x50).hex();out['dry']=h.dry_isvalid(pid,b,0x188d90,cmd);assert out['dry']['isvalid']==1
  out['post']=h.do_post(pid,b,cmd,'t198 official pause after observed previous pause no effect pt183u')
  out['health']=h.process_health(pid)
  if out['post']['wait']==0 and out['health']['alive']:
   t=time.monotonic()
   while time.monotonic()-t<3:
    if p.read(idler+0x6c1,1)==b'\1':break
    time.sleep(.1)
 out['after']=p.read(idler+0x6c1,1)[0];out['date']=(h.read_campaign_summary(p,gs).get('verified')or{}).get('date_full')
finally:
 h.close_gates();out['allow_post']=h.allow_post();(R/'research/t198_pause_recovery.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2));p.close()
