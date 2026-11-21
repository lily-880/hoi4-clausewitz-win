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
prev=json.loads((Q/'t240_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==json.loads((Q/'t241_fresh_guard.json').read_text(encoding='utf-8'))['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
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
 r=rt.reader();ins=rt.code(0x1a5743e,7);assert ins[:3]==bytes.fromhex('488b1d');root_rva=0x1a57445+struct.unpack('<i',ins[3:])[0];root=r.q(rt.base+root_rva);mp=root+0x48;sentinel=r.q(mp+8);mask=r.q(mp+0x30);buckets=r.q(mp+0x18);end=r.q(mp+0x20);assert mask+1<=4096 and (mask&(mask+1))==0 and end-buckets==(mask+1)*16
 data=r.q(root+0x30);count=r.i(root+0x3c);assert 0<count<=2048;countries=r.array(rt.gs+0x310,2048);remap=r.q(rt.gs+0x340)
 def canonical(ref):
  if ref==0:return 0
  assert 0<ref<len(countries);idx=r.i(remap+ref*4);assert 0<idx<len(countries);return idx
 def lookup(tag):
  h=0x811c9dc5
  for ch in tag.encode('ascii'):h=((h^ch)*0x1000193)&0xffffffff
  bucket=buckets+(h&mask)*16;first=r.q(bucket);node=r.q(bucket+8);visited=[];seen=set();result=None
  if node!=sentinel:
   while True:
    assert node not in seen and len(seen)<32;seen.add(node);key=r.string(node+0x10);visited.append(key)
    if key==tag:
     idx=r.i(node+0x30);assert 0<=idx<count;raw=r.i(data+idx*4);ci=canonical(raw);cc=countries[ci];r.require(cc,'CCountry');actual=country_tag(r,rt.gs,ci,cc);result=dict(dictionary_index=idx,country_ref_raw=raw,canonical_index=ci,current_country_tag=actual,country_pointer=cc);break
    if node==first:break
    node=r.q(node+8)
  return dict(requested_tag=tag,fnv1a32=hex(h),bucket_index=h&mask,visited_bucket_keys=visited,result=result)
 entries=[lookup(t) for t in ['MAN','JAP','SOV','QZQ']];by={v['requested_tag']:v for v in entries};pairs=[]
 if by['MAN']['result'] and by['JAP']['result']:
  for source,target in [('MAN','JAP'),('JAP','MAN')]:
   sc=by[source]['result'];tc=by[target]['result'];status=r.q(sc['country_pointer']+0xf88);r.require(status,'CDiplomacyStatus');parent=r.i(status+0x188);level=r.q(status+0x3b8);definition=r.q(level+0x28) if level else 0;flag=r.exact(definition+0x2e,1)[0] if definition else 0;relations=r.q(status+8);rel=r.q(relations+tc['canonical_index']*8);r.require(rel,'CRelationStatus');dep=r.q(rel+0x288);di=dict(present=bool(dep));subject=False
   if dep:
    typ=r.i(dep+8);dr=r.i(dep+0x10);rr=r.i(rel+0x50);di.update(type_token=typ,dependency_country_ref=dr,relation_country_ref=rr);subject=typ==0x30d1 and (dr==rr or bool(dr and rr and canonical(dr)==canonical(rr)))
   targetref=tc['country_ref_raw'];same=parent==targetref or bool(parent and targetref and canonical(parent)==canonical(targetref));puppet=same and bool(flag)
   pairs.append(dict(source_named_tag=source,target_named_tag=target,source_current_tag=sc['current_country_tag'],target_current_tag=tc['current_country_tag'],source_canonical_index=sc['canonical_index'],target_canonical_index=tc['canonical_index'],source_parent_ref=parent,target_country_ref=targetref,source_level_present=bool(level),source_definition_present=bool(definition),source_puppet_flag=flag,relation_dependency_inputs=di,derived_native_puppet_of_projection=puppet,derived_native_subject_of_projection=subject,projection_not_raw_schema_field=True))
 for e in entries:
  if e['result']:e['result'].pop('country_pointer')
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,lookup_root_rva=hex(root_rva),mask=mask,dictionary_count=count,targeted_lookups=entries,directional_pairs=pairs,stable_dependencies=stable,native_calls=0,new_visibility_checks=0,schema_visible_relation_emitted=False,promotions=[],scope='Four bounded named hash-bucket lookups only, MAX32 chain nodes each, MAN/JAP both-direction raw operands if present. No whole-country objects census, repeated D04 or own unary negatives, visible-unit inference, native invocation or schema output. Derived bools explicitly offline native-contract projections, not raw fields.')
 (Q/'t241_targeted_subject_controls.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:rt.close()
