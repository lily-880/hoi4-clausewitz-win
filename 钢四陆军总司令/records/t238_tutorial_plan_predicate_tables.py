# Machine-dependent strictly read-only: exact named battleplan alert entrance.
# No native calls or game mutations. No opacity/tier/confidence substitutions.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t237_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==json.loads((Q/'t238_fresh_guard.json').read_text(encoding='utf-8'))['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
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
 functions={};tables=[];tv,ts=rt.sections['.text']
 for label,site in [('frontline',0x1a5c669),('offensive_order',0x1a5c6f8)]:
  raw=rt.code(site,7);assert raw[:3]==b'\x48\x8d\x05';vt=site+7+struct.unpack_from('<i',raw,3)[0]
  col=struct.unpack('<Q',rt.code(vt-8,8))[0]-rt.base;sig,off,cd,td=struct.unpack('<IIII',rt.code(col,16));assert sig==1;name=rt.code(td+0x10,160).split(b'\0')[0].decode();slots=[]
  for j,ptr in enumerate(struct.unpack('<8Q',rt.code(vt,64))):
   va=ptr-rt.base;intext=tv<=va<tv+ts;slots.append(dict(index=j,rva=hex(va),in_text=intext))
   if not intext:break
   if hex(va) not in functions:functions[hex(va)]=capture(va)
  tables.append(dict(label=label,constructor_site=hex(site),vtable_rva=hex(vt),col_rva=hex(col),col_offset=off,class_name=name,slots=slots))
 after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,tables=tables,functions=functions,promotions=[],scope='Exact frontline/offensive_order tutorial predicate constructor tables, sampled first8entries only; RTTI and methods not plan type/axis by classname. No tutorial/native method invoked, no current plan or UI read.')
 (Q/'t238_tutorial_plan_predicate_tables.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(at_est=out['at_est'],tables=tables,functions={k:dict(window_size=f['window_size'],literals=f['literals'],calls=f['calls'],unresolved_edges=f['unresolved_edges']) for k,f in functions.items()}),ensure_ascii=False,indent=2))
finally:rt.close()
