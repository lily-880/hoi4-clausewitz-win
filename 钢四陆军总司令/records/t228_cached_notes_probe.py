# Machine-dependent readonly loaded-memory research; no game calls/writes/UI/save access.
import sys,json,hashlib,datetime,struct
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t227_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
 assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup')
 manager=r.q(rt.idler+0x7a8)
 def text(a):
  b=r.exact(a,32);n,c=struct.unpack_from('<QQ',b,16);assert 0<=n<=4096 and n<=c<=1048576
  raw=b[:n] if c<=15 else r.exact(struct.unpack_from('<Q',b)[0],n)
  return {'address':hex(a),'length':n,'capacity':c,'raw_hex':raw.hex(),'text':raw.decode('utf-8')}
 rows=[]
 for aid in (3,4):
  ptr,cap,n=struct.unpack('<QII',r.exact(manager+(aid+0xf0e)*24,16));assert 0<=n<=cap<=32
  master=manager+aid*0x468
  item={'alert_id':aid,'master':hex(master),'master_name':text(master+0x410),'master_instant':text(master+8),'master_delayed':text(master+0x28),'active_count':n,'entries':[]}
  for j in range(n):
   ep=ptr+j*0x468;keys=struct.unpack('<QQQQ',r.exact(ep+0x438,32))
   item['entries'].append({'entry':hex(ep),'key0':hex(keys[0]),'group':hex(keys[1]),'key3':hex(keys[3]),'same_current_group':keys[1]==tg,'name':text(ep+0x410),'instant':text(ep+8),'delayed':text(ep+0x28)})
  rows.append(item)
 cs=Cs(CS_ARCH_X86,CS_MODE_64);functions={}
 for va,n in [(0xb69710,0x1400),(0xb52950,0x100),(0xb52a30,0x200)]:
  raw=rt.code(va,n);f=walk_flow(cs,raw,va);f.update(raw_hex=raw.hex(),sha256=H(raw));functions[hex(va)]=f
 # Recheck earlier specific producer/registration functions, not repeating demand/date scans.
 for filename,va in [('t227_supply_alert_mapping_consumers.json','0xb79d00'),('t226_supply_alert_threshold_getters.json','0xb61660')]:
  old=json.loads((Q/filename).read_text(encoding='utf-8'))['functions'][va];raw=rt.code(int(va,16),old['window_size']);assert H(raw)==old['sha256']
 stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'current_theater_group':hex(tg),'rows':rows,'functions':functions,'stable_dependencies':stable,'raw_dependencies':[{'address':hex(a),'size':n,'hex':b.hex()} for (a,n),b in sorted(r.samples.items())],'scope':'Read existing master/active cached strings only; no localization/formatter/native invocation; no Input/full crisis claim','production_hashes':prev['production_hashes'],'native_controls':prev['native_controls']}
 (Q/'t228_cached_notes_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'at_est':out['at_est'],'rows':rows,'functions':{k:{x:v[x] for x in ['reachable_instruction_count','unresolved_edges','external_tails']} for k,v in functions.items()},'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:rt.close()
