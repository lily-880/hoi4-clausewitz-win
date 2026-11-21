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
 # Separate budgets avoid the t234 NNavy define flood; no token table or renderer scan.
 import re
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs)
 patterns={
 'confidence':re.compile(r'confiden',re.I),
 'unit_intel':re.compile(r'(unit|division).{0,60}(intel|intelligen|recon)|(intel|intelligen|recon).{0,60}(unit|division)',re.I),
 'army_intel':re.compile(r'(army|land).{0,60}(intel|intelligen)|(intel|intelligen).{0,60}(army|land)',re.I),
 'recon_accuracy':re.compile(r'(recon|intel).{0,50}(accura|estimat)|(accura|estimat).{0,50}(recon|intel)',re.I),
 }
 hits={k:[] for k in patterns};totals={k:0 for k in patterns}
 for m in re.finditer(rb'[\x20-\x7e]{5,}\x00',rd):
  text=m.group()[:-1].decode()
  if any(x in text for x in ['Error reading','Warning for define','no lua object','not a lua table','NNavy','INTEL_DIVISION_REVEALED']):continue
  for k,pat in patterns.items():
   if pat.search(text):
    totals[k]+=1
    if len(hits[k])<24:hits[k].append(dict(rva=hex(rv+m.start()),text=text))
 # Exact LEA xrefs to confidence and unit-intel names only; cap per name, not a flood-prone global budget.
 targets={int(x['rva'],16):[] for k in ('confidence','unit_intel') for x in hits[k]}
 tv,ts=rt.sections['.text'];text=rt.code(tv,ts)
 for rex in (0x48,0x4c):
  for modrm in (5,13,21,29,53,61):
   pre=bytes((rex,0x8d,modrm));at=0
   while True:
    i=text.find(pre,at)
    if i<0:break
    at=i+1
    if i+7>len(text):continue
    dst=tv+i+7+struct.unpack_from('<i',text,i+3)[0]
    if dst in targets and len(targets[dst])<8:targets[dst].append(hex(tv+i))
 for rows in hits.values():
  for x in rows:x['xrefs']=targets.get(int(x['rva'],16),[])
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,hits=hits,total_eligible=totals,per_category_cap=24,stable_dependencies=stable,promotions=[],scope='Named C-string discovery and LEA entrance only, not semantics or schema confidence. Excludes NNavy define flood and closed reveal-gate; no tier/opacity or token scans.')
 (Q/'t235_named_intel_entrances.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:rt.close()
