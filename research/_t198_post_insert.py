import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
import _t197_setpath_zero_post as h
out={'authorized_by':['pt183u']};h.close_gates();pid=h.mem_find_pid('hoi4.exe');assert pid==12948
p=h.Proc(pid);pe=h.PE(h.EXE);b=h.Backend();s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16)
assert p.read(idler+0x6c1,1)==b'\1'
rec=json.loads((R/'research/t198_insertfront_dry.json').read_text());cmd=int(rec['cmd'],16)
assert h.mo._u64(b,cmd)-b.image_base==0x2a852e0
assert p.read(cmd+0x28,8)==struct.pack('<II',53,411)
assert h.pdx(p,cmd+0x30)[2]==0
assert struct.unpack('<I',p.read(cmd+0x78,4))[0]==2
out['before']=h.find_group(p,pe,co,(53,411))[1]
out['dry']=h.dry_isvalid(pid,b,0x18df2a0,cmd);assert out['dry']['isvalid']==1
try:
 out['post']=h.do_post(pid,b,cmd,'t198 InsertFront on army411 plan2 authorized pt183u')
 out['health']=h.process_health(pid)
 if out['post']['wait']!=0 or not out['health']['alive']:out['stop']='POST_TIMEOUT_OR_DEAD'
 else:
  out['after']=h.find_group(p,pe,co,(53,411))[1]
  out['pause']=p.read(idler+0x6c1,1)[0]
finally:
 h.close_gates();out['allow_post']=h.allow_post();p.close();(R/'research/t198_insertfront_post.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
