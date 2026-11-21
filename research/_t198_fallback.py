import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
import _t197_setpath_zero_post as h
out={'authorized_by':['pt183u'],'helper':'18d9030 tail-jumps 18d1150; NewFallback','path':[2072,7944]};h.close_gates();pid=h.mem_find_pid('hoi4.exe');assert pid==12948
p=h.Proc(pid);pe=h.PE(h.EXE);b=h.Backend();s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16)
assert p.read(idler+0x6c1,1)==b'\1'
gp,ins=h.find_group(p,pe,co,(53,411));assert gp
cmd,fr=h.factory_make(pid,b,0x18d0330,0x2a85520,0x60);assert cmd
h.mo._write(pid,cmd+0x28,struct.pack('<II',53,411));buf=h.mo._game_malloc(pid,8);h.mo._write(pid,buf,struct.pack('<II',2072,7944));h.mo._write(pid,cmd+0x48,struct.pack('<QII',buf,2,2))
assert h.pdx(p,cmd+0x30)[2]==0
out['factory']=fr;out['dry']=h.dry_isvalid(pid,b,0x18df520,cmd)
try:
 if out['dry']['isvalid']==1:
  out['post']=h.do_post(pid,b,cmd,'t198 official NewFallback path2072,7944 army411 pt183u')
  out['health']=h.process_health(pid)
  if out['post']['wait']==0 and out['health']['alive']:
   out['arrays']={hex(off):[h.snap_inst(p,pe,ip) for ip in h.ptr_array(p,gp+off,256)] for off in (0x98,0xb0,0xc8)}
  else:out['stop']='POST_TIMEOUT_OR_DEAD'
 out['pause']=p.read(idler+0x6c1,1)[0]
finally:
 h.close_gates();out['allow_post']=h.allow_post();p.close();(R/'research/t198_fallback_post.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
