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
prev=json.loads((Q/'t235_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==json.loads((Q/'t237_fresh_guard.json').read_text(encoding='utf-8'))['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
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
 functions={hex(v):capture(v) for v in (0xb5bb40,0xb6b9e0,0xd73190,0xd3cb00)}
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';manager=r.q(rt.idler+0x7a8);manager_class=rt.cls(manager);name=r.string(manager+0x2b*0x468+0x410);assert name=='alert_battleplans_with_no_divs'
 head=manager+0x16950+0x2b*24;p,cap,n=struct.unpack('<QII',r.exact(head,16));assert 0<=n<=cap<=128
 rows=[]
 for j in range(min(n,4)):
  ep=p+j*0x468;keys=struct.unpack('<4Q',r.exact(ep+0x438,32));rows.append(dict(entry=hex(ep),key0=hex(keys[0]),key_group=hex(keys[1]),key2=hex(keys[2]),key3=hex(keys[3])))
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,functions=functions,manager_class=manager_class,descriptor_name=name,alert43=dict(pointer=hex(p),capacity=cap,count=n,inspected=len(rows),rows=rows),stable_dependencies=stable,own_plan_registries_read=0,plan_instances_inspected=0,promotions=[],scope='Exact alert43 cached-instance header and up to4keys only; no own-plan registry, no empty-plan polling, no per-plan positive/negative claims. Named updater subject/recursive child traversal and scheduling caller only.')
 (Q/'t237_plan_alert_subject_and_cached_control.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(at_est=out['at_est'],manager_class=manager_class,descriptor_name=name,alert43=out['alert43'],functions={k:dict(window_size=f['window_size'],literals=f['literals'],calls=f['calls'],unresolved_edges=f['unresolved_edges']) for k,f in functions.items()},stable_dependencies=stable),ensure_ascii=False,indent=2))
finally:rt.close()
