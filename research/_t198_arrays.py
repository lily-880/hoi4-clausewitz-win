import json,sys,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
import _t197_setpath_zero_post as h
pid=h.mem_find_pid('hoi4.exe');assert pid==12948
p=h.Proc(pid);pe=h.PE(h.EXE);s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16)
out={}
for th in h.ptr_array(p,co+0x168,64):
 for gp in h.ptr_array(p,th+0x80,256):
  handle=h.handle_at(p,gp+8);rec={}
  for off in (0x98,0xb0,0xc8):
   rec[hex(off)]=[h.snap_inst(p,pe,ip) for ip in h.ptr_array(p,gp+off,256)]
  out[str(handle)]=rec
print(json.dumps(out,indent=2));(R/'research/t198_all_plan_arrays.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
d=json.loads((R/'research/t194_bind_cmds.json').read_text());print('FALLBACK_BIND',json.dumps(d['cmds']['COrderNewFallbackCommand']))
p.close()
