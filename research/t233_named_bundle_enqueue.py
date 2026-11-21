# Machine-dependent strictly read-only native validator investigation.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t232_final_seal.json').read_text());rt=Runtime()
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
  pr=bounds(va);s,e,u=pr if pr else (va,va+512,0);assert e-s<0x12000;raw=rt.code(s,e-s);f=walk_flow(cs,raw,s);f.update(raw_hex=raw.hex(),sha256=H(raw),pdata=[hex(s),hex(e),hex(u)]);reach={int(x.split()[0],16) for x in f['asm']};l=[]
  rv,rs=rt.sections['.rdata']
  for ins in cs.disasm(raw,s):
   if ins.address not in reach or ins.mnemonic!='lea' or len(ins.operands)<2:continue
   o=ins.operands[1]
   if o.type!=X86_OP_MEM or o.mem.base!=X86_REG_RIP:continue
   t=ins.address+ins.size+o.mem.disp
   if not rv<=t<rv+rs:continue
   b=rt.code(t,256).split(b'\0')[0]
   if 2<=len(b)<256 and all(32<=x<127 for x in b):l.append(dict(site=hex(ins.address),rva=hex(t),text=b.decode()))
  f['literals']=l;return f
 seed=0xf7b940;functions={hex(v):capture(v) for v in [seed,0xf6fc70]}
 tv,ts=rt.sections['.text'];text=rt.code(tv,ts);callers=[];at=0
 while True:
  i=text.find(b'\xe8',at)
  if i<0:break
  at=i+1
  if i+5>len(text):continue
  if tv+i+5+struct.unpack_from('<i',text,i+1)[0]!=seed:continue
  pr=bounds(tv+i)
  if pr and pr[1]-pr[0]<0x12000:
   f=capture(tv+i)
   if any(x.startswith(hex(tv+i)[2:]+' ') and 'call' in x for x in f['asm']):
    callers.append(dict(site=hex(tv+i),function=hex(pr[0])));functions[hex(pr[0])]=f
  assert len(callers)<=32
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';own=[];tokens={};bundles=[]
 # Roots independently derived from the exact two LEA instructions at named EndBundle consumer.
 for site in [0xf71f81,0xf71f8d]:
  raw=rt.code(site,7);assert raw[:3]==b'\x48\x8d\x0d';v=site+7+struct.unpack('<i',raw[3:])[0];a=rt.base+v
  # Counts/flags ONLY; empty scopes are not schema false samples and no event replay.
  bundles.append(dict(named_consumer_site=hex(site),rva=hex(v),country_count=r.i(a+12),secondary_count=r.i(a+0x24),active_nesting=r.i(a+0x60),mode_byte=r.exact(a+0x64,1)[0],locked=r.exact(a+0x65,1)[0]))
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(bundles=bundles,tokens=tokens,at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,seed=hex(seed),functions=functions,callers=callers,own_theatres=own,stable_dependencies=stable,promotions=[],scope='Exact current own-theatre fronts only. Native functions inspected as bytes, never invoked; diagnostics not schema flag.')
 (Q/'t233_named_bundle_enqueue.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='functions'},indent=2));print(json.dumps({k:{kk:f.get(kk) for kk in ['window_size','sha256','literals','calls','external_tails','unresolved_edges']} for k,f in functions.items()},indent=2))
finally:rt.close()
