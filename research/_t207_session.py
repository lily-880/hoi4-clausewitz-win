"""t207 host-specific, memory-only new-session binding. No disk image or game calls."""
import os,sys,json,struct,hashlib,datetime
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0';os.environ['CLAUSEWITZ_ALLOW_POST']='0'
from mem import Proc,find_pid
from input_loaded_fields import LoadedReader,country_tag
class Runtime:
 def __init__(self):
  self.pr=Proc(find_pid('hoi4.exe'));self.base=self.pr.base;self.profile=json.loads((R/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'))
  h=self.pr.read(self.base,4096);assert h[:2]==b'MZ';nt=struct.unpack_from('<I',h,0x3c)[0];assert h[nt:nt+4]==b'PE\0\0';assert struct.unpack_from('<H',h,nt+4)[0]==0x8664
  n=struct.unpack_from('<H',h,nt+6)[0];op=struct.unpack_from('<H',h,nt+20)[0];self.sections={}
  for j in range(n):
   o=nt+24+op+j*40;name=h[o:o+8].split(b'\0')[0].decode();size,va=struct.unpack_from('<II',h,o+8);self.sections[name]=(va,size)
  self.gs=self.q(self.base+self.profile['globals']['G_GAMESTATE']);self.idler=self.q(self.base+self.profile['globals']['G_IDLER'])
  assert self.cls(self.gs)=='.?AVCCurrentGameState@@' and self.cls(self.idler)=='.?AVCInGameIdler@@'
  self.index=self.i(self.gs+0x520);a=self.pr.read(self.gs+0x310,16);data,cap,count=struct.unpack('<Qii',a);assert 0<=self.index<count<=2000 and count<=cap<=5000
  self.country=self.q(data+self.index*8);assert self.cls(self.country)=='.?AVCCountry@@'
 def q(self,a):return struct.unpack('<Q',self.pr.read(a,8))[0]
 def i(self,a):return struct.unpack('<i',self.pr.read(a,4))[0]
 def cls(self,a):
  vt=self.q(a);assert self.base<=vt<self.base+self.pr.image_size;col=self.q(vt-8);assert self.base<=col<self.base+self.pr.image_size;sig,off,cd,td=struct.unpack('<IIII',self.pr.read(col,16));assert sig==1 and 0<td<self.pr.image_size;return self.pr.read(self.base+td+0x10,160).split(b'\0')[0].decode('ascii')
 def reader(self):return LoadedReader(self.pr.read,self.cls)
 def code(self,rva,n):assert 0<=rva<rva+n<=self.pr.image_size;return self.pr.read(self.base+rva,n)
 def guard(self):
  t=struct.unpack('<I',self.pr.read(self.gs+0x468,4))[0];year=self.i(self.gs+0x478);day=self.i(self.gs+0x484)
  return {'pid':self.pr.pid,'base':hex(self.base),'gs':hex(self.gs),'idler':hex(self.idler),'country':hex(self.country),'country_index':self.index,'pause':self.pr.read(self.idler+0x6c1,1)[0],'speed_slot':self.i(self.gs+0x4bc),'year':year,'day_index':day,'ui_date':str(datetime.date(year,1,1)+datetime.timedelta(days=day)),'ui_hour':t%24+1,'hour_tick':t,'markers':{n:(R/'research'/n).exists() for n in ('safe_land_tool_gate.OPEN','strategic_only_tool_gate.OPEN')}}
 def close(self):self.pr.close()
def main():
 rt=Runtime()
 try:
  before=rt.guard();versions=[]
  if '.rsrc' in rt.sections:
   va,size=rt.sections['.rsrc'];assert size<16*1024*1024;blob=rt.code(va,size);p=0
   while True:
    p=blob.find(b'\xbd\x04\xef\xfe\x00\x00\x01\x00',p)
    if p<0:break
    if p+52<=len(blob):
     x=struct.unpack_from('<13I',blob,p);fmt=lambda a,b:f'{a>>16}.{a&65535}.{b>>16}.{b&65535}';versions.append({'rva':hex(va+p),'file_version':fmt(x[2],x[3]),'product_version':fmt(x[4],x[5]),'file_type':x[9]})
    p+=1
  r=rt.reader();tag=country_tag(r,rt.gs,rt.index,rt.country);r.stable();after=rt.guard()
  out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'guard_equal':before==after,'country_tag':tag,'resource_version_candidates':versions,'image_size':rt.pr.image_size,'sections':rt.sections,'classes':{'gs':rt.cls(rt.gs),'idler':rt.cls(rt.idler),'country':rt.cls(rt.country)},'production_fingerprint_verified':False,'full_capture_run':False,'constraint':'loaded-image/session narrow research only; no denied disk image access; no production gate relaxation','new_segment_baseline':40.5,'stop_threshold':50.5}
  p=R/'research/t207_new_session.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
 finally:rt.close()
if __name__=='__main__':main()