# Machine-dependent strictly read-only: independently named unit intel/confidence consumer.
# No native calls or game mutations. No opacity/tier/confidence substitutions.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t235_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==prev['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 pv,ps=rt.sections['.pdata'];pd=rt.code(pv,ps);ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
 def bounds(va):
  lo,hi=0,len(ranges)
  while lo<hi:
   m=(lo+hi)//2;s,e,u=ranges[m]
   if va<s:hi=m
   elif va>=e:lo=m+1
   else:return s,e,u
 cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 def capture(va):
  pr=bounds(va);s,e,u=pr if pr else (va,va+512,0);assert e-s<0x20000
  raw=rt.code(s,e-s);f=walk_flow(cs,raw,s)
  f.update(raw_hex=raw.hex(),sha256=H(raw),pdata=[hex(x) for x in pr] if pr else None,window_start=hex(s),window_size=e-s)
  reach={int(x.split()[0],16) for x in f['asm']};l=[];rv,rs=rt.sections['.rdata']
  for ins in cs.disasm(raw,s):
   if ins.address not in reach or ins.mnemonic!='lea' or len(ins.operands)<2:continue
   o=ins.operands[1]
   if o.type!=X86_OP_MEM or o.mem.base!=X86_REG_RIP:continue
   t=ins.address+ins.size+o.mem.disp
   if not rv<=t<rv+rs:continue
   b=rt.code(t,256).split(b'\0')[0]
   if 2<=len(b)<256 and all(32<=x<127 for x in b):l.append(dict(site=hex(ins.address),rva=hex(t),text=b.decode()))
  f['literals']=l;return f
 # Factory493900 installs this exact vtable; bind COL before considering consecutive code entries.
 vt=0x2832d50;col=struct.unpack('<Q',rt.code(vt-8,8))[0];sig,offset,cd,td,chd,selfrva=struct.unpack('<6I',rt.pr.read(col,24));assert sig==1 and rt.base+selfrva==col
 cls=rt.code(td+16,160).split(b'\0')[0].decode();tv,ts=rt.sections['.text'];slots=[];functions={}
 words=struct.unpack('<16Q',rt.code(vt,128))
 for i,p in enumerate(words):
  va=p-rt.base;iscode=tv<=va<tv+ts
  slots.append(dict(index=i,rva=hex(va),in_text=iscode))
  if not iscode:break
  if len(functions)<12:
   pr=bounds(va)
   if not pr or pr[1]-pr[0]<0x8000:functions[hex(va)]=capture(va)
 # These entries are candidate vtable code only; no class-wide slot-count claim or native invocation.
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,vtable_rva=hex(vt),col_rva=hex(col-rt.base),col_offset=offset,class_name=cls,slots=slots,functions=functions,stable_dependencies=stable,promotions=[],scope='Factory-derived current vtable/COL and consecutive .text candidates only, stops at first noncode metadata word. No adjacent descriptor4slot claim; candidates need dispatch/dataflow proof.')
 (Q/'t236_frontage_evaluator_bind.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(at_est=out['at_est'],class_name=cls,slots=slots,functions={k:{kk:f.get(kk) for kk in ['window_size','asm','literals','calls','unresolved_edges','external_tails']} for k,f in functions.items()},stable_dependencies=stable),ensure_ascii=False,indent=2))
finally:rt.close()
