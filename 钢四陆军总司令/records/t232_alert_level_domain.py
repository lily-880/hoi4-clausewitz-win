# Native parser name/domain certificate, not a schema severity mapping. Read only.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
H=lambda b:hashlib.sha256(b).hexdigest();session=json.loads((Q/'t232_initial_session_rebind.json').read_text())
rt=Runtime()
try:
 g=rt.guard();assert g==session['before']
 assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==session['native_controls'][hex(va)]
 for name,h in session['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
 rv,rs=rt.sections['.rdata'];blob=rt.code(rv,rs);target=struct.pack('<Q',rt.base+0x145e1c0);at=0;identities=[]
 while len(identities)<16:
  i=blob.find(target,at)
  if i<0:break
  at=i+8
  if i%8:continue
  row={'slot_rva':hex(rv+i),'class':None}
  for b in range(64):
   cpos=i-8-b*8
   if cpos<0:break
   col=struct.unpack_from('<Q',blob,cpos)[0]
   if not rt.base<=col<rt.base+rt.pr.image_size:continue
   raw=rt.pr.read(col,24);sig,off,cd,td,chd,selfrva=struct.unpack('<6I',raw)
   if sig!=1 or selfrva!=col-rt.base or not 0<td<rt.pr.image_size:continue
   name=rt.code(td+16,200).split(b'\0')[0].decode('ascii','replace')
   if not name.startswith('.?A'):continue
   row.update({'class':name,'vtable_rva':hex(rv+cpos+8),'slot_offset':hex((rv+i)-(rv+cpos+8)),'col_rva':hex(col-rt.base),'col_hex':raw.hex(),'this_offset':off,'td_rva':hex(td)})
   break
  identities.append(row)
 # Independently validate named token-registration RIP literal and immediate registration token.
 mp=json.loads((Q/'t163_script_token_map.json').read_text(encoding='utf-8'));names={'alert_level','low','medium','high','alert_margin','on_enable','on_disable','state_modifier','state_resistance_modifier'}
 cs=Cs(CS_ARCH_X86,CS_MODE_64);clips=[]
 for row in mp:
  if row['name'] not in names:continue
  va=int(row['registration_rva'],16);raw=rt.code(va,64);ins=list(cs.disasm(raw,va));lit=None
  first=ins[0]
  if first.mnemonic=='lea' and 'rip' in first.op_str:
   # parse expected seven-byte RIP LEA from token registrar; verify actual loaded literal
   disp=struct.unpack_from('<i',raw,3)[0];dst=va+7+disp;b=rt.code(dst,160).split(b'\0')[0]
   assert b.decode()==row['name'];lit={'rva':hex(dst),'text':b.decode()}
  assert lit is not None
  clips.append(dict(row,raw_hex=raw.hex(),asm=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in ins],loaded_literal=lit))
 # Existing qualified entrance: rebind exactly same 3 controls, not a new census.
 from t227_qualified_crisis_replay import supply
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup');og=r.array(tg+0x48,128)[0];r.require(og,'COrdersGroup');members=r.array(og+0x50,256);assert len(members)==25
 sq=lambda a:struct.unpack('<q',r.exact(a,8))[0]
 hours=r.i(rt.base+0x33e3678);threshold=sq(rt.base+0x33e3e00);assert (hours,threshold)==(72,99000);controls=[]
 for member in members[:3]:
  u=member-0xb8;r.require(u,'CArmy');assert r.i(u+0x18)==51 and r.i(u+0x1e0)==3 and r.q(u+0xc0)==og
  assert r.q(r.q(member)+0x20)==rt.base+0xc4f050 and r.q(r.q(u)+0x40)==rt.base+0x20f350
  pp=r.q(u+0x1f0);r.require(pp,'CProvince');pid=r.i(u+0x28);assert r.i(pp+0xa4)==pid
  source=sq(u+0x40);effective,out,bucket=supply(source,sq(u+0x600),sq(u+0x610),hours,threshold,bool(r.q(u+0x2f8)))
  controls.append(dict(unit_id=r.i(u+0x1c),province_id=pid,source_raw=source,effective_raw=effective,out_of_supply=out,native_bucket=bucket))
 assert {x['unit_id'] for x in controls}=={500,374,479}
 manager=r.q(rt.idler+0x7a8);active={};master={}
 for aid,name in [(3,'alert_low_supply'),(4,'alert_very_low_supply')]:
  assert r.string(manager+aid*0x468+0x410)==name;master[str(aid)]=r.i(manager+aid*0x468+0x448)
  ptr,cap,n=struct.unpack('<QII',r.exact(manager+(aid+0xf0e)*24,16));assert 0<=n<=cap<=32;rows=[]
  for j in range(n):
   ep=ptr+j*0x468;key=struct.unpack('<4Q',r.exact(ep+0x438,32));assert r.string(ep+0x410)==name
   rows.append({'key0':key[0],'key_group':hex(key[1]),'key3':key[3],'field448':r.i(ep+0x448)})
  active[str(aid)]=rows
 # Reloaded save may have no cached alert yet: do not run updater to manufacture one.
 qualified=any(x['key0']==0 and x['key_group']==hex(tg) and x['key3']==0 for x in active['4'])
 stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'parser_slot_identities':identities,'token_registration_clips':clips,'controls':controls,'sampled_members':3,'native_member_count':25,'new_units_inspected':0,'theater_group':hex(tg),'master_field448':master,'active':active,'actual_cached_alert4_for_same_group':qualified,'raw_dependencies':[{'address':hex(a),'size':n,'hex':b.hex()} for (a,n),b in sorted(r.samples.items())],'stable_dependencies':stable,'scope':'alert_level parser may belong to an unrelated domain; do not map low/medium/high to watch/high/critical. Existing 3-member bound unchanged, no notes payload read or formatter call, no full feed.'}
 (Q/'t232_alert_level_domain.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in out.items() if k not in ('raw_dependencies','token_registration_clips','before','after')},ensure_ascii=False,indent=2))
finally:rt.close()
