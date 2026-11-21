"""t202 read-only loaded-image analysis. No disk-image, save, Post or remote call."""
import sys,os,json,struct,bisect,hashlib
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from gamestate import resolve_player_country,read_campaign_summary
from input_loaded_fields import LoadedReader,own_plans
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
class Runtime:
 def __init__(self):
  os.environ['CLAUSEWITZ_ALLOW_POST']='0';os.environ['CLAUSEWITZ_ALLOW_WRITE']='0';self.pr=Proc(find_pid('hoi4.exe'));assert self.pr.pid==12948;self.base=self.pr.base;self.profile=json.loads((R/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'));self.gs=self.q(self.base+self.profile['globals']['G_GAMESTATE']);self.idler=self.q(self.base+self.profile['globals']['G_IDLER']);assert self.cls(self.gs)=='.?AVCCurrentGameState@@'and self.cls(self.idler)=='.?AVCInGameIdler@@';self.country=int(resolve_player_country(self.pr,self.gs)['country_ptr'],16)
  h=self.pr.read(self.base,4096);assert h[:2]==b'MZ';nt=struct.unpack_from('<I',h,0x3c)[0];assert h[nt:nt+4]==b'PE\0\0';num=struct.unpack_from('<H',h,nt+6)[0];optional=struct.unpack_from('<H',h,nt+20)[0];self.sections={}
  for j in range(num):
   off=nt+24+optional+j*40;name=h[off:off+8].split(b'\0')[0].decode();size,va=struct.unpack_from('<II',h,off+8);self.sections[name]=(va,size)
  va,size=self.sections['.pdata'];data=self.code(va,size);self.fns=sorted(x for x in struct.iter_unpack('<III',data[:size//12*12])if 0<x[0]<x[1]<self.pr.image_size);self.starts=[x[0]for x in self.fns];self.cs=Cs(CS_ARCH_X86,CS_MODE_64)
 def q(self,a):return struct.unpack('<Q',self.pr.read(a,8))[0]
 def cls(self,a):
  vt=self.q(a);assert self.base<=vt<self.base+self.pr.image_size;col=self.q(vt-8);assert self.base<=col<self.base+self.pr.image_size;sig,off,cd,td=struct.unpack('<IIII',self.pr.read(col,16));assert sig==1;assert 0<td<self.pr.image_size;return self.pr.read(self.base+td+0x10,160).split(b'\0')[0].decode('ascii')
 def reader(self):return LoadedReader(self.pr.read,self.cls)
 def code(self,rva,n):assert 0<=rva<rva+n<=self.pr.image_size;return self.pr.read(self.base+rva,n)
 def clip(self,a):
  j=bisect.bisect_right(self.starts,a)-1;parts=[]
  if j<0 or not self.fns[j][0]<=a<self.fns[j][1]:st=a;end=a+512;leaf=True
  else:
   first=self.fns[j];st,end=first[:2];parts=[first];leaf=False
   for row in self.fns[j+1:j+12]:
    if row[0]!=end:break
    u=row[2]&~3;h=self.code(u,4)
    if not(h[0]>>3)&4:break
    chain=struct.unpack('<III',self.code(u+((4+2*h[2]+3)&~3),12))
    if chain[0]!=st:break
    parts.append(row);end=row[1]
  raw=self.code(st,end-st);ls=[]
  for i in self.cs.disasm(raw,st):
   if leaf and i.mnemonic=='int3':break
   ls.append(f'{i.address:x} {i.mnemonic} {i.op_str}')
  (R/f'research/_t202_clip_{st:x}.txt').write_text('\n'.join(ls),encoding='utf-8');return {'start':hex(st),'end':hex(end),'unwind_parts':parts,'loaded_code_sha256':hashlib.sha256(raw).hexdigest(),'asm':ls}
 def guard(self):
  r=self.reader();plans,ev=own_plans(r,self.country);d={'pid':self.pr.pid,'base':hex(self.base),'pause':self.pr.read(self.idler+0x6c1,1)[0],'speed_slot':struct.unpack('<I',self.pr.read(self.gs+0x4bc,4))[0],'date':read_campaign_summary(self.pr,self.gs)['fields']['date_full'],'plans':[{'id':x['plan_id'],'executing':x['executing']}for x in plans],'gate_open':(R/'research/safe_land_tool_gate.OPEN').exists()};r.stable();assert d['pause']==1 and d['speed_slot']==0 and not d['gate_open']and all(not x['executing']for x in plans);return d
 def close(self):self.pr.close()
