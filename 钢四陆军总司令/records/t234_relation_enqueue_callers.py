# Machine-dependent strictly read-only: named diplomatic/war enqueue into 33EB090.
# Never invoke natives; do not treat empty scopes or F6A071 as schema values.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t233_final_seal.json').read_text(encoding='utf-8'))
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
 def lea_target(site):
  raw=rt.code(site,7)
  # 48 8d 0d disp32  or 4c/etc; accept rex+lea rcx,[rip+disp]
  assert raw[0] in (0x48,0x4c,0x4d) and raw[1]==0x8d
  return site+7+struct.unpack_from('<i',raw,3)[0]
 # Exact live LEA destinations already present in the three wrappers and controller path.
 lea_sites=dict(
  f7bb20_enqueue=0xf7bbc1,f7bb20_process=0xf7bbd5,
  f7bce0_enqueue=0xf7bd98,f7bce0_process=0xf7bdac,
  f7e1c0_enqueue=0xf7e25c,f7e1c0_process=0xf7e271,
  f7b940_enqueue=0xf7b94a,f7b940_process=0xf7b95f,
 )
 lea_targets={k:hex(lea_target(v)) for k,v in lea_sites.items()}
 assert all(lea_targets[k]=='0x33eb090' for k in lea_targets if k.startswith(('f7bb20','f7bce0','f7e1c0')))
 assert lea_targets['f7b940_enqueue']==lea_targets['f7b940_process']=='0x33eb020'
 seeds=[0xf6f9b0,0xf79110,0xf6f6c0,0xd598f0,0xd56b10,0xd59900]
 functions={hex(v):capture(v) for v in seeds}
 # Direct CALL xrefs to the three 33EB090 wrappers only; not a general empty-scope or diagnostic rescan.
 tv,ts=rt.sections['.text'];text=rt.code(tv,ts)
 wrappers=(0xf7bb20,0xf7bce0,0xf7e1c0)
 callers=[]
 for dest in wrappers:
  at=0
  while True:
   i=text.find(b'\xe8',at)
   if i<0:break
   at=i+1
   if i+5>len(text):continue
   if tv+i+5+struct.unpack_from('<i',text,i+1)[0]!=dest:continue
   site=tv+i;pr=bounds(site)
   entry=pr[0] if pr else None
   if entry and pr[1]-pr[0]<0x20000:
    functions[hex(entry)]=capture(site)
   callers.append(dict(site=hex(site),dest=hex(dest),function=hex(entry) if entry else None))
   assert len(callers)<=64
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 # Named literals already captured; no empty-scope counter reread as a schema sample.
 named=[]
 for k,f in functions.items():
  for lit in f.get('literals') or []:
   t=lit['text'].lower()
   if any(w in t for w in ('war','peace','diplo','relation','declare','ally','faction','surrender','white peace','justify','wargoal','truce','non-aggression','puppet','annex','independence')):
    named.append(dict(function=k,**lit))
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,
  lea_targets=lea_targets,callers=callers,named_literals=named,functions=functions,
  promotions=[],stable_dependencies=stable,
  scope='33EB090 enqueue wrappers and their direct callers only. LEA arithmetic is independent of empty current scope counters. F6A071/front+70 mismatch/NotifyControllerChanged are not war-change evidence. Functions inspected as bytes, never invoked.')
 (Q/'t234_relation_enqueue_callers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 summary={k:v for k,v in out.items() if k!='functions'}
 summary['function_meta']={k:{kk:f.get(kk) for kk in ('window_size','sha256','literals','calls','external_tails','unresolved_edges','pdata')} for k,f in functions.items()}
 print(json.dumps(summary,ensure_ascii=False,indent=2))
finally:rt.close()
