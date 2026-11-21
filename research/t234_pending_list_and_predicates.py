# Read the exact D56B10 global pending list once, and name 748490/DA37F0 predicates. Readonly.
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
  pr=bounds(va);s,e,u=pr if pr else (va,va+512,0);assert e-s<0x8000
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
 def rip_disp(site,size,off):
  raw=rt.code(site,size);return site+size+struct.unpack_from('<i',raw,off)[0]
 # Exact instructions from the completed D56B10 body.
 list_obj=rip_disp(0xd56b16,7,3)
 count_rva=rip_disp(0xd56b2e,7,3)
 data_rva=rip_disp(0xd56b3a,7,3)
 functions={hex(v):capture(v) for v in (0x748490,0xda37f0,0x1bd5a0,0x12e040)}
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 # One current pending-list observation only; not a schema true/false and not an empty-scope rescan.
 count=r.i(rt.base+count_rva);data=r.q(rt.base+data_rva)
 assert 0<=count<=10000
 members=[];player_listed=False
 for i in range(count):
  p=r.q(data+i*8);cls=None
  try:cls=rt.cls(p)
  except Exception as e:cls='unproved:'+type(e).__name__
  is_player=(p==rt.country);player_listed=player_listed or is_player
  rec=dict(index=i,pointer=hex(p),cls=cls,is_player=is_player)
  if cls=='.?AVCCountry@@':
   rec['tag']=country_tag(r,rt.gs,None,p) if False else None
   # country_tag may need index; do not invent. Leave tag only for proved class, skip if API needs index.
  members.append(rec)
 # Avoid country_tag(None) mistakes: only compare pointers for player membership.
 for rec in members:
  rec.pop('tag',None)
 pending=dict(list_object_rva=hex(list_obj),count_rva=hex(count_rva),data_rva=hex(data_rva),count=count,data=hex(data),player_country=hex(rt.country),player_listed=player_listed,members=members)
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,pending=pending,functions=functions,promotions=[],stable_dependencies=stable,
  scope='One-shot D56B10 global list membership and predicate-function literals. Pending count is not a schema front_invalidated value. No F6A071/empty EndBundle counter reuse. Never invoked.')
 (Q/'t234_pending_list_and_predicates.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 meta={k:{kk:f.get(kk) for kk in ('window_size','sha256','literals','calls','unresolved_edges','pdata')} for k,f in functions.items()}
 print(json.dumps(dict(at_est=out['at_est'],pending={k:v for k,v in pending.items() if k!='members'}|{'member_count':len(members),'member_classes':[x['cls'] for x in members]},function_meta=meta,stable_dependencies=stable),ensure_ascii=False,indent=2))
finally:rt.close()
