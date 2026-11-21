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
 import re
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';controls=[]
 for cp in r.array(rt.gs+0x268,4096):
  cid=r.i(cp+0x1c)
  if cid not in (3072,3096,3097):continue
  r.require(cp,'CLandCombat')
  for off in (0x28,0x30):
   bp=r.q(cp+off);r.require(bp,'CLandCombatant');assert r.q(bp+0x18)==cp;active=r.array(bp+0xe8,128);rows=[]
   for up in active:
    r.require(up,'CArmy');tp=r.q(up+0x3b8);r.require(tp,'CReferencedDivisionTemplate');p,cap,n=struct.unpack('<QII',r.exact(tp+0xc0,16));assert 0<=n<=cap<=64;parts=[];base=0
    for i in range(n):
     entry=r.exact(p+i*16,16);unit=struct.unpack_from('<Q',entry)[0];q=struct.unpack_from('<i',entry,8)[0];r.require(unit,'CSubUnitDefinition');w=struct.unpack('<q',r.exact(unit+0x58,8))[0];assert 0<=q<=100 and 0<=w<=100000000;parts.append(dict(count=q,width_raw=w));base+=q*w
    rows.append(dict(unit_id=r.i(up+0x1c),owner_index=r.i(up+0x1e0),base_width_raw=base,template_parts=parts))
   controls.append(dict(combat_id=cid,side_offset=hex(off),active_count=len(active),combat_modifier_a0=struct.unpack('<q',r.exact(cp+0xa0,8))[0],units=rows,base_width_sum_raw=sum(x['base_width_raw'] for x in rows),effective_width_sum_unproved=True,native_boolean_unproved=True))
 assert len(controls)==6
 # Distinct next remaining candidate: named plan status entrance only; no own-plan registry or empty-plan scan.
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs);hits=[]
 pat=re.compile(r'(BATTLE.?PLAN|OFFENSIVE.?PLAN|PLAN_EXECUT|PLAN_ACTIV|PLAN_BLOCK|PLAN_INVALID)',re.I)
 for m in re.finditer(rb'[\x20-\x7e]{5,}\x00',rd):
  t=m.group()[:-1].decode()
  if pat.search(t) and not any(x in t for x in ['Error reading','Warning for define','::']):
   hits.append(dict(rva=hex(rv+m.start()),text=t))
 assert len(hits)<256
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,controls=controls,plan_status_names=hits,stable_dependencies=stable,promotions=[],scope='Six already qualified current own-combat sides, nine raw unit template width inputs only. Country/leader10F modifiers and effective terrain capacity remain unproved, so no native boolean samples. Named plan-status pivot only, not empty plans.')
 (Q/'t236_raw_capacity_controls_and_plan_pivot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(at_est=out['at_est'],controls=[{k:v for k,v in x.items() if k!='units'} for x in controls],plan_status_names=hits,stable_dependencies=stable),ensure_ascii=False,indent=2))
finally:rt.close()
