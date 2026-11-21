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
prev=json.loads((Q/'t234_final_seal.json').read_text(encoding='utf-8'))
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
 functions={hex(v):capture(v) for v in (0x78a470,0x78a480,0x78a490)}
 # All meaningful army-intel C-strings beyond define metadata; independent category, no NNavy flood.
 import re
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs);names=[];pivot=[]
 for m in re.finditer(rb'[\x20-\x7e]{5,}\x00',rd):
  t=m.group()[:-1].decode();u=t.upper()
  if any(x in t for x in ['Error reading','Warning for define','no lua object','not a lua table','NNavy']):continue
  if ('INTEL' in u or 'INTELLIGENCE' in u) and any(x in u for x in ['ARMY','DIVISION','UNIT']) and not u.startswith(('NINTEL::','NGRAPHICS::')):
   names.append(dict(rva=hex(rv+m.start()),text=t))
  # Distinct remaining memory target: exact manpower/front hold names only, not desired-force or garrison REQ_DIVS.
  if (('MANPOWER' in u or 'REINFORCE' in u) and any(x in u for x in ['FRONT','HOLD','COLLAPSE'])):
   pivot.append(dict(rva=hex(rv+m.start()),text=t))
 assert len(names)<256 and len(pivot)<128
 # Inspect direct RIP accesses in independently named define getters; xrefs global data for later exact consuming function.
 define_refs={}
 for k,f in functions.items():
  refs=[]
  for ins in cs.disasm(bytes.fromhex(f['raw_hex']),int(f['window_start'],16)):
   for o in ins.operands:
    if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP:
     refs.append(dict(site=hex(ins.address),target=hex(ins.address+ins.size+o.mem.disp),asm=ins.mnemonic+' '+ins.op_str))
  define_refs[k]=refs
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,functions=functions,define_refs=define_refs,army_intel_names=names,front_manpower_pivot_names=pivot,promotions=[],stable_dependencies=stable,scope='Named NIntel template-unit-count getters and remaining non-flooded army-intel names only. Define names/values are not unit confidence. Distinct manpower-front name presence is not a front-hold value. No tier/opacity scans.')
 (Q/'t235_template_count_domain.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:rt.close()
