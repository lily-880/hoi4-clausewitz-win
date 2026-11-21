# Readonly machine-specific native dataflow and scope rebind. Never invoke a native function.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from t227_qualified_crisis_replay import supply
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
H=lambda b:hashlib.sha256(b).hexdigest();prev=json.loads((Q/'t227_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
 assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup');og=r.array(tg+0x48,128)[0];r.require(og,'COrdersGroup');members=r.array(og+0x50,256);assert len(members)==25
 sq=lambda a:struct.unpack('<q',r.exact(a,8))[0]
 hours=r.i(rt.base+0x33e3678);threshold=sq(rt.base+0x33e3e00);controls=[]
 for member in members[:3]:
  u=member-0xb8;r.require(u,'CArmy');assert r.i(u+0x18)==51 and r.i(u+0x1e0)==3 and r.q(u+0xc0)==og
  assert r.q(r.q(member)+0x20)==rt.base+0xc4f050 and r.q(r.q(u)+0x40)==rt.base+0x20f350
  pp=r.q(u+0x1f0);r.require(pp,'CProvince');pid=r.i(u+0x28);assert r.i(pp+0xa4)==pid
  source=sq(u+0x40);capacity=sq(u+0x600);reserve=sq(u+0x610);special=bool(r.q(u+0x2f8));effective,out,bucket=supply(source,capacity,reserve,hours,threshold,special)
  controls.append(dict(unit_id=r.i(u+0x1c),province_id=pid,source_raw=source,effective_raw=effective,capacity_raw=capacity,reserve_raw=reserve,special=special,out_of_supply=out,native_bucket=bucket))
 by={x['unit_id']:x for x in controls};assert set(by)=={500,374,479} and by[479]['out_of_supply'] and by[479]['native_bucket']==0 and not by[374]['out_of_supply'] and by[374]['native_bucket']==2
 manager=r.q(rt.idler+0x7a8);ptr,cap,n=struct.unpack('<QII',r.exact(manager+(4+0xf0e)*24,16));assert 0<n<=cap<=32;selected=[]
 def txt(a):
  b=r.exact(a,32);n,c=struct.unpack_from('<QQ',b,16);assert 0<=n<=4096 and n<=c<=1048576;raw=b[:n] if c<=15 else r.exact(struct.unpack_from('<Q',b)[0],n);return {'text':raw.decode('utf-8'),'raw_hex':raw.hex(),'length':n,'capacity':c}
 for j in range(n):
  ep=ptr+j*0x468;keys=struct.unpack('<QQQQ',r.exact(ep+0x438,32))
  if keys[0]==0 and keys[1]==tg and keys[3]==0:selected.append({'entry':hex(ep),'name':txt(ep+0x410),'instant':txt(ep+8),'delayed':txt(ep+0x28)})
 assert len(selected)==1 and selected[0]['name']['text']=='alert_very_low_supply'
 cs=Cs(CS_ARCH_X86,CS_MODE_64);functions={}
 for va,n in [(0xb525a0,0x400),(0x65e780,0x600)]:
  raw=rt.code(va,n);f=walk_flow(cs,raw,va);f.update(raw_hex=raw.hex(),sha256=H(raw));functions[hex(va)]=f
 literals={}
 for va,n in [(0x29c5118,96),(0x29c4210,96),(0x2796e30,32)]:
  raw=rt.code(va,n);literals[hex(va)]={'raw_hex':raw.hex(),'ascii_prefix':raw.split(b'\0')[0].decode('ascii','replace')}
 stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'theatre':hex(tp),'theater_group':hex(tg),'orders_group':hex(og),'member_count':len(members),'sample_count':len(controls),'controls':controls,'hours':hours,'out_threshold':threshold,'selected':selected,'functions':functions,'literals':literals,'stable_dependencies':stable,'raw_dependencies':[{'address':hex(a),'size':n,'hex':b.hex()} for (a,n),b in sorted(r.samples.items())],'scope':'Independent fresh rebind of the same3/25 controls, not a new unit scan; group-level cached note only, not witness-specific text or complete record'}
 (Q/'t228_scope_and_text_consumers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('functions','raw_dependencies')},ensure_ascii=False,indent=2));print({a:{k:f[k] for k in ['reachable_instruction_count','unresolved_edges','external_tails']} for a,f in functions.items()})
finally:rt.close()
