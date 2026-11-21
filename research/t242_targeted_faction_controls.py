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
prev=json.loads((Q/'t241_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==json.loads((Q/'t242_fresh_guard.json').read_text(encoding='utf-8'))['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
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
 entries=[lookup(t) for t in ['SOV','MON','JAP']];by={v['requested_tag']:v for v in entries};sources={};pairs=[]
 for tag,e in by.items():
  if not e['result']:continue
  status=r.q(e['result']['country_pointer']+0xf88);r.require(status,'CDiplomacyStatus');faction=r.q(status+0x2d8);sources[tag]=dict(canonical_index=e['result']['canonical_index'],current_country_tag=e['result']['current_country_tag'],faction_pointer=hex(faction),faction_nonnull=bool(faction))
 for source,target in [('SOV','MON'),('MON','SOV'),('SOV','JAP'),('JAP','SOV')]:
  if source not in sources or target not in sources:continue
  left=sources[source];right=sources[target];projection=left['faction_nonnull'] and right['faction_nonnull'] and left['faction_pointer']==right['faction_pointer'];pairs.append(dict(source=source,target=target,source_canonical_index=left['canonical_index'],target_canonical_index=right['canonical_index'],source_faction_pointer=left['faction_pointer'],target_faction_pointer=right['faction_pointer'],source_nonnull=left['faction_nonnull'],target_nonnull=right['faction_nonnull'],derived_native_is_in_faction_with_projection=projection,projection_not_raw_schema_field=True))
 for e in entries:
  if e['result']:e['result'].pop('country_pointer')
 vt=rt.code(0x280f220,25*8);slots=[dict(index=i,rva=hex(struct.unpack_from('<Q',vt,i*8)[0]-rt.base),in_text=rt.sections['.text'][0]<=struct.unpack_from('<Q',vt,i*8)[0]-rt.base<sum(rt.sections['.text'])) for i in [21,22,23,24]]
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,lookup_root_rva=hex(root_rva),mask=mask,dictionary_count=count,targeted_lookups=entries,current_native_inputs=sources,directional_pairs=pairs,actual_extended_interface_slots=slots,stable_dependencies=stable,native_calls=0,new_visibility_checks=0,schema_visible_relation_emitted=False,promotions=[],scope='Exactly three named bounded country lookups, only actual independently named IS_IN_FACTION_WITH source/target +2D8 operands and four directional controls. Not a generic friendly/ally schema definition; no nonwar/null-faction friendly inference, current visible owner bridge, units/country-object census, MAN/JAP puppet repeat or game calls.')
 (Q/'t242_targeted_faction_controls.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:rt.close()
