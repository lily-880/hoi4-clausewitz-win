from _t205_common import *
from _t205_flow import walk_flow
x=Runtime()
try:
 b=x.guard();r=x.reader();cp=r.array(x.gs+0x268,4096)[0];out={'combat':hex(cp),'callback_secondary_bases':[],'manager_update':walk_flow(x.cs,x.code(0xc0c660,0x1000),0xc0c660)};lo,n=x.sections['.text']
 for off in(0,8,0x10,0x18,0x20):
  p=cp+off;vt=r.q(p)
  if not x.base<=vt<x.base+x.pr.image_size:continue
  try:cls=x.cls(p)
  except(Exception)as e:out['callback_secondary_bases'].append({'offset':hex(off),'not_rtti':type(e).__name__});continue
  col=r.q(vt-8);sig,co,cd,td,ch=struct.unpack('<IIIII',x.pr.read(col,20));d={'offset':hex(off),'class':cls,'COL_offset':co,'vtable':hex(vt-x.base),'methods':{},'hierarchy':[]};chp=x.base+ch;num,arr=struct.unpack('<II',x.pr.read(chp+8,8))
  assert num<64
  for j in range(num):
   desc=x.base+struct.unpack('<I',x.pr.read(x.base+arr+j*4,4))[0];t=struct.unpack('<I',x.pr.read(desc,4))[0];d['hierarchy'].append(x.pr.read(x.base+t+16,180).split(b'\0')[0].decode('ascii'))
  for k in range(0,0x100,8):
   fn=r.q(vt+k)-x.base
   if not lo<=fn<lo+n:break
   d['methods'][hex(k)]=hex(fn)
  out['callback_secondary_bases'].append(d)
 r.stable();out['guard_after']=x.guard();assert out['guard_after']==b;(R/'research/t205_combat_callback_lifecycle.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('BASES',json.dumps(out['callback_secondary_bases'],indent=2));f=out['manager_update'];print('UPDATE_CFG',f['reachable_instruction_count'],f['unresolved_edges'],f['external_tails']);a=f['asm']
 for k,s in enumerate(a):
  if s.startswith('c0cb00 ')or any(z in s for z in(' + 0x468]',' + 0x478]',' + 0x484]')):print('UPDATE_CTX','\n'.join(a[max(0,k-15):k+9]))
finally:x.close()
