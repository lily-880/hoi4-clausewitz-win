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
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';witness=[]
 for cp in r.array(rt.gs+0x268,4096):
  if r.i(cp+0x1c)!=3072:continue
  r.require(cp,'CLandCombat');side=r.q(cp+0x30);r.require(side,'CLandCombatant');assert r.q(side+0x18)==cp
  for up in r.array(side+0xe8,128):
   r.require(up,'CArmy')
   if r.i(up+0x1c)==399:witness.append(up)
 assert len(witness)==1;up=witness[0];raw_owner=r.i(up+0x1d8);stored_index=r.i(up+0x1e0);remap=r.q(rt.gs+0x340);countries=r.array(rt.gs+0x310,2048);assert 0<raw_owner<len(countries);owner_index=r.i(remap+raw_owner*4);assert owner_index==stored_index and 0<owner_index<len(countries);owner=countries[owner_index];r.require(owner,'CCountry');owner_tag=country_tag(r,rt.gs,owner_index,owner)
 status=r.q(owner+0xf88);r.require(status,'CDiplomacyStatus');overlord_ref=r.i(status+0x188);relations=r.q(status+8);rel=r.q(relations+rt.index*8);r.require(rel,'CRelationStatus');dep=r.q(rel+0x288);inputs=dict(dependency_present=bool(dep))
 if dep:inputs.update(dependency_type=r.i(dep+8),dependency_country_ref=r.i(dep+0x10),relation_country_ref=r.i(rel+0x50))
 assert r.exact(rt.base+0x368f570,1)==b'\x01';count=r.i(rt.base+0x368f574);assert count>0x30d1;tokenbase=r.q(rt.base+0x368f5a0);token=r.string(tokenbase+0x30d1*32)
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,current_combat_owner_bridge=dict(combat_id=3072,side='defender',unit_id=399,class_name='CArmy',owner_ref_raw=raw_owner,owner_index_field=stored_index,canonical_owner_index=owner_index,owner_country_tag=owner_tag,player_index=rt.index,owner_overlord_ref_raw=overlord_ref,relation_to_player_inputs=inputs,current_visibility_revalidated=False,schema_visible_relation_emitted=False),exact_consumed_token=dict(id=0x30d1,name=token),stable_dependencies=stable,promotions=[],scope='One already-encountered unit399 rebound via current combat/side roots, current owner canonicalization and source-owner->player relation operands only. No visible-feed/gate/tier rescan or fresh spotted claim, no positive relation manufactured, no native calls. Exact one consumed native token, not token discovery scan.')
 (Q/'t240_current_owner_directional_operands.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:rt.close()
