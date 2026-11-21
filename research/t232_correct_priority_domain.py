# Restart-safe machine-specific read-only research. No native/game calls or mutations.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
session=json.loads((Q/'t232_initial_session_rebind.json').read_text());assert session['safe_to_research']
rt=Runtime()
try:
 g=rt.guard();assert g==session['before']
 assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==session['native_controls'][hex(va)]
 for name,h in session['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
 pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz);ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
 def bounds(va):
  lo,hi=0,len(ranges)
  while lo<hi:
   m=(lo+hi)//2;s,e,u=ranges[m]
   if va<s:hi=m
   elif va>=e:lo=m+1
   else:return s,e,u
  return None
 cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 def capture(va):
  pr=bounds(va)
  assert not pr or pr[1]-pr[0]<=0x8000
  s,e,u=pr if pr else (va,va+512,0)
  raw=rt.code(s,e-s);f=walk_flow(cs,raw,s);f.update(raw_hex=raw.hex(),sha256=H(raw),pdata=[hex(x) for x in pr] if pr else None,entry_source='current live vtable pointer' if not pr else 'unwind entry');lits=[]
  reachable={int(x.split()[0],16) for x in f['asm']}
  rv,rs=rt.sections['.rdata']
  for ins in cs.disasm(raw,s):
   if ins.address not in reachable or ins.mnemonic!='lea' or len(ins.operands)<2:continue
   o=ins.operands[1]
   if o.type!=X86_OP_MEM or o.mem.base!=X86_REG_RIP:continue
   t=ins.address+ins.size+o.mem.disp
   if not rv<=t<rv+rs:continue
   b=rt.code(t,160).split(b'\0')[0]
   if 2<=len(b)<160 and all(32<=v<127 for v in b):lits.append({'site':hex(ins.address),'rva':hex(t),'text':b.decode()})
  f['reachable_literals']=lits;return f
 # The pointer addresses are DERIVED from current loaded table, not from t231 heap.
 table=rt.code(0x2affbe0,24);col,method0,method1=struct.unpack('<QQQ',table)
 assert method0-rt.base==0x1eeff60 and method1-rt.base==0x1eefb08
 hdr=rt.pr.read(col,24);sig,off,cd,td,chd,selfrva=struct.unpack('<6I',hdr)
 assert sig==1 and selfrva==col-rt.base
 name=rt.code(td+16,160).split(b'\0')[0].decode();assert name=='.?AVCNavyTheaterGroupItem@@'
 fs={hex(method0-rt.base):capture(method0-rt.base),hex(method1-rt.base):capture(method1-rt.base)}
 # Scoped alert_level token candidates. Actual immediate instructions only, bounded distinct unwind bodies.
 token=19364;needle=struct.pack('<I',token);tv,ts=rt.sections['.text'];text=rt.code(tv,ts);at=0;candidate_refs=[];seen=set()
 while True:
  i=text.find(needle,at)
  if i<0:break
  at=i+1;site=tv+i;pr=bounds(site)
  if not pr or pr[0] in seen or pr[1]-pr[0]>0x10000:continue
  s,e,u=pr;candidate_refs.append({'match_rva':hex(site),'pdata':[hex(x) for x in pr]});seen.add(s)
  if len(candidate_refs)>=24:break
 # Only collect domains/literals; token byte matches are not named semantic proof.
 candidates={}
 for row in candidate_refs:
  s=int(row['pdata'][0],16);e=int(row['pdata'][1],16)
  if e-s<=0x8000:candidates[hex(s)]=capture(s)
 # No repeated unit or notes scan: bind only current country/tag for session correctness.
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'current_table_hex':table.hex(),'current_col_hex':hdr.hex(),'class':name,'method0_rva':hex(method0-rt.base),'method1_rva':hex(method1-rt.base),'method1_recomputed_from_current_pointer':True,'rejected_t231_rva':'0x1eafb08','functions':fs,'alert_level_token_byte_candidates':candidate_refs,'candidate_functions':candidates,'stable_dependencies':stable,'scope':'Two-slot COL+function table independently checked on new base. Domain still needs method1 semantics; no schema severity mapping or field promotion from this class. Token-byte candidates are provisional, not evidence until exact parser use.'}
 (Q/'t232_correct_priority_domain.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'at_est':out['at_est'],'class':name,'method1_rva':out['method1_rva'],'functions':{k:{kk:f.get(kk) for kk in ('window_size','reachable_instruction_count','unresolved_edges','external_tails','sha256','reachable_literals')} for k,f in fs.items()},'method1_asm':fs[hex(method1-rt.base)]['asm'],'token_candidates':[{'rva':k,'literals':f['reachable_literals'],'size':f['window_size']} for k,f in candidates.items()]},ensure_ascii=False,indent=2))
finally:rt.close()
