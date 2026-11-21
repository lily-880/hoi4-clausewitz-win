import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable
from input_loaded_fields import LoadedReader
pr=Proc(find_pid('hoi4.exe'))
try:
 assert pr.pid==12948;pe=PE(pr.image_path);se=detect_session(pr,pe);gs=int(se['signals']['gs_ptr'],16);idle=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(pr,gs)['country_ptr'],16);r=LoadedReader(pr.read,lambda a:_rtti_name_from_vtable(pe,struct.unpack('<Q',pr.read(a,8))[0]-pr.base));assert pr.read(idle+0x6c1,1)==b'\1';clock=pr.read(gs+0x468,0x24);rows=[];seen=set();queue=[]
 for tp in r.array(co+0x168,64):
  for gp in r.array(tp+0x80,256):
   for off in(0x98,0xb0,0xc8):queue +=[(ip,None,'group:'+hex(off))for ip in r.array(gp+off,256)]
 while queue:
  ip,parent,source=queue.pop(0)
  if ip in seen:continue
  seen.add(ip);assert len(seen)<=256;r.require(ip,'COrderInstance');data,cap,n=struct.unpack('<QII',r.exact(ip+0x70,16));assert 0<=n<=cap<=65536;path=list(struct.unpack('<'+'I'*n,r.exact(data,n*4)))if n else[];children={}
  for off in(0x1f8,0x2d0):
   ch=r.array(ip+off,256);children[hex(off)]=[r.i(x+0x244)for x in ch];queue +=[(x,r.i(ip+0x244),'child:'+hex(off))for x in ch]
  rows.append({'id':r.i(ip+0x244),'parent_id':parent,'source':source,'vt_rva':hex(r.q(ip)-pr.base),'type_raw':r.i(ip+0x30),'path_raw':path,'fallback':r.exact(ip+0x298,1)[0],'special119':r.exact(ip+0x119,1)[0],'executing':bool(r.exact(ip+0x248,1)[0]),'children':children})
 assert clock==pr.read(gs+0x468,0x24)and pr.read(idle+0x6c1,1)==b'\1';r.stable();out={'rows':rows,'all_observed_including_children_stopped':all(not x['executing']for x in rows),'pause':1,'clock_unchanged':True,'new_read_only_sample':True,'warning':'COrderInstance child is not automatically a schema Plan; establish axis semantics before emitting a row.'};(R/'research/t201_recursive_plan_sample.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:pr.close()
