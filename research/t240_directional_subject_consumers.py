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
prev=json.loads((Q/'t239_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==json.loads((Q/'t240_fresh_guard.json').read_text(encoding='utf-8'))['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
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
 import re
 r=rt.reader();status=r.q(rt.country+0xf88);assert status>0x10000;own=dict(country_tag=country_tag(r,rt.gs,rt.index,rt.country),subject_ref_raw=r.i(status+0x188));level=r.q(status+0x3b8);own['level_present']=bool(level)
 if level:
  definition=r.q(level+0x28);own['definition_present']=bool(definition)
  if definition:own['puppet_flag_2e_raw']=r.exact(definition+0x2e,1)[0]
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs);tv,ts=rt.sections['.text'];wanted={'TRIGGER_IS_PUPPET_OF','TRIGGER_IS_NOT_PUPPET_OF','TRIGGER_IS_SUBJECT_OF','TRIGGER_IS_NOT_SUBJECT_OF','is_puppet_of','is_subject_of'};names=[]
 for m in re.finditer(rb'[\x20-\x7e]{3,}\x00',rd):
  t=m.group()[:-1].decode()
  if t in wanted:names.append(dict(rva=hex(rv+m.start()),text=t))
 targets={int(x['rva'],16):x['text'] for x in names};text=rt.code(tv,ts);refs=[];functions={};tables=[]
 for m in re.finditer(rb'[\x48-\x4f]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',text,re.S):
  site=tv+m.start();target=site+7+struct.unpack_from('<i',m.group(),3)[0]
  if target not in targets:continue
  ins=next(cs.disasm(m.group(),site),None)
  if not ins or ins.mnemonic!='lea':continue
  pr=bounds(site);refs.append(dict(site=hex(site),name=targets[target],rva=hex(target),pdata=[hex(x) for x in pr] if pr else None))
  if pr and pr[1]-pr[0]<0x8000 and len(functions)<6:functions[hex(pr[0])]=capture(pr[0])
 for tooltip in [int(k,16) for k in functions]:
  needle=struct.pack('<Q',rt.base+tooltip);p=0
  while True:
   p=rd.find(needle,p)
   if p<0:break
   ref=rv+p;p+=1
   if ref%8:continue
   vt=ref-21*8
   if vt-8<rv:continue
   col=struct.unpack_from('<Q',rd,vt-8-rv)[0]-rt.base
   if not rv<=col<=rv+rs-24:continue
   sig,off,cd,td,chd,selfrva=struct.unpack('<6I',rt.code(col,24))
   if sig!=1 or selfrva!=col or not 0<=td+16<=rt.pr.image_size-160:continue
   name=rt.code(td+16,160).split(b'\0')[0].decode('ascii',errors='replace');slots=struct.unpack('<24Q',rt.code(vt,192));eva=slots[22]-rt.base
   if not (name.startswith('.?A') and tv<=eva<tv+ts):continue
   tables.append(dict(tooltip=hex(tooltip),tooltip_slot=21,vtable_rva=hex(vt),class_name=name,col_offset=off,evaluator_slot=22,evaluator_rva=hex(eva)));functions[hex(eva)]=capture(eva)
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,own_native_inputs=own,names=names,references=refs,tables=tables,functions=functions,stable_dependencies=stable,promotions=[],scope='Actual own unary raw inputs only; exact directional *_OF named consumer discovery/table binding, no foreign/faction/unit census, no unary-as-relative relation or game invocation.')
 (Q/'t240_directional_subject_consumers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(at_est=out['at_est'],own_native_inputs=own,names=names,references=refs,tables=tables,functions={k:{kk:f[kk] for kk in ['window_size','asm','calls','literals','unresolved_edges','external_tails']} for k,f in functions.items()}),ensure_ascii=False,indent=2))
finally:rt.close()
