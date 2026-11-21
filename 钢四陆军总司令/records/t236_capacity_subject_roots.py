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
 raw=rt.code(0x133e540,512);f=walk_flow(cs,raw,0x133e540);f.update(raw_hex=raw.hex(),sha256=H(raw),window_start='0x133e540',window_size=512,literals=[])
 functions={'0x133e540_full':f};r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';subjects=[]
 # Current manager roots, exact three previously qualified own combats only; never stale pointers or history bridge.
 for cp in r.array(rt.gs+0x268,4096):
  cid=r.i(cp+0x1c)
  if cid not in (3072,3096,3097):continue
  r.require(cp,'CLandCombat');vt=r.q(cp);widthget=r.q(vt+0xd0)-rt.base;functions[hex(widthget)]=capture(widthget)
  sides=[];has_own=False
  for sideoff in (0x28,0x30):
   bp=r.q(cp+sideoff);r.require(bp,'CLandCombatant');back=r.q(bp+0x18);assert back==cp
   us=r.array(bp+0xe8,128);members=[]
   for up in us:
    r.require(up,'CArmy');owner=r.i(up+0x1e0);has_own=has_own or owner==rt.index
    ug=r.q(r.q(up)+0x170)-rt.base;functions[hex(ug)]=capture(ug)
    members.append(dict(unit_id=r.i(up+0x1c),owner_index=owner,pointer=hex(up),width_getter=hex(ug)))
   sides.append(dict(pointer=hex(bp),class_name='CLandCombatant',active_count=len(us),active_members=members))
  assert has_own
  subjects.append(dict(combat_id=cid,pointer=hex(cp),class_name='CLandCombat',width_getter=hex(widthget),sides=sides))
 assert len(subjects)==3
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,functions=functions,subjects=subjects,stable_dependencies=stable,promotions=[],scope='Three previously qualified current own combats and six sides only, no history/result inference or full unit feed. Bind capacity input virtual getter code; never invoke natives.')
 (Q/'t236_capacity_subject_roots.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(at_est=out['at_est'],subjects=subjects,functions={k:{kk:f.get(kk) for kk in ['window_start','window_size','asm','calls','unresolved_edges','external_tails']} for k,f in functions.items()},stable_dependencies=stable),ensure_ascii=False,indent=2))
finally:rt.close()
