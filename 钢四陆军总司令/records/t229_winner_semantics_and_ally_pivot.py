# Readonly native result semantics and distinct ally-trigger pivot. No game calls.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest();prev=json.loads((Q/'t228_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
 assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True;functions={}
 def freeze(va,raw,old=None):
  f=walk_flow(cs,raw,va);f.update(raw_hex=raw.hex(),sha256=H(raw));
  if old:
   h=old.get('sha256',old.get('loaded_window_sha256'))
   if h is not None:assert h==H(raw),(hex(va),'old code changed')
   else:assert old['asm']==f['asm'],(hex(va),'legacy reachable instructions changed')
   f['prior_validation']='raw hash match' if h is not None else 'exact reachable instruction match; legacy hash absent'
  functions[hex(va)]=f;return f
 old=json.loads((Q/'t207_native_new_entrances.json').read_text(encoding='utf-8'))['functions']
 for a in ('0xd39310','0xd3b290'):
  f=old[a];freeze(int(a,16),rt.code(int(a,16),f['window_size']),f)
 oldclose=json.loads((Q/'t211_observer_close_id_arguments.json').read_text(encoding='utf-8'))['observer_close_flow'];freeze(0xd3b6d0,rt.code(0xd3b6d0,oldclose['window_size']),oldclose)
 for fn,key in [('t211_observer_prefix_field_identity_contract.json','0xd40810'),('t208_date_history_id_flows.json','0xd40a40')]:
  f=json.loads((Q/fn).read_text(encoding='utf-8'))['flows'][key];freeze(int(key,16),rt.code(int(key,16),f['window_size']),f)
 # Verify actual keyword-name bytes referenced by loaded registration clips.
 mp=json.loads((Q/'t163_script_token_map.json').read_text(encoding='utf-8'));tokens=[]
 for row in mp:
  if row['token'] not in (0xe3,0x3756,0x4dbc):continue
  va=int(row['registration_rva'],16);raw=rt.code(va,64);ins=next(cs.disasm(raw,va));op=ins.operands[1];assert ins.mnemonic=='lea' and op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP
  literal=ins.address+ins.size+op.mem.disp;actual=rt.code(literal,96).split(b'\0')[0].decode();assert actual==row['name'];tokens.append(dict(row,literal_rva=hex(literal),actual_name=actual,registration_raw_hex=raw.hex()))
 # Rebind retained rows, sampling by OUTCOME contrast, not by side-selector contrast.
 manager=r.array(rt.gs+0x880,2048)[rt.index];r.require(manager,'CManager@NCombatLog');groups=r.array(manager+8,128)
 pool=r.q(rt.base+0x33ea870);pool_count=r.i(rt.base+0x33ea87c);assert 0<pool_count<100000
 rows=[];summaries=[];outcomes=set()
 for gp in groups[:2]:
  r.require(gp,'COrdersGroupLogs@NCombatLog');handle=r.q(gp+0xe0);ptr,cap,n=struct.unpack('<QII',r.exact(gp+0xc8,16));assert 0<=n<=cap<=100000;inspected=0
  for j in range(min(n,32)):
   idx,selector=struct.unpack_from('<IB',r.exact(ptr+j*8,8));assert idx<pool_count and selector in (0,1);rec=pool+idx*0x448;r.require(rec,'SCombatData@NCombatLog');defvic= r.exact(rec+0x444,1)[0];pa=r.exact(rec+0x447,1)[0];assert defvic in (0,1) and pa in (0,1)
   won=bool(selector^defvic);rows.append({'group':hex(gp),'group_handle':hex(handle),'ordinal':j,'record_index':idx,'record':hex(rec),'reference_address':hex(ptr+j*8),'side_selector':selector,'defensive_victory':defvic,'player_is_attacker':pa,'native_group_won_reconstructed':won});outcomes.add(won);inspected+=1
   if outcomes=={False,True}:break
  summaries.append({'group':hex(gp),'reference_count':n,'inspected':inspected})
  if outcomes=={False,True}:break
 # New pivot: inspect only fixed trigger-vtable cluster, not faction/live-country zeros.
 start=0x2800000;size=0x20000;blob=rt.code(start,size);candidates=[];seen=set();pdata_va,pdata_size=rt.sections['.pdata'];pd=rt.code(pdata_va,pdata_size);ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
 def fn(va):
  matches=[x for x in ranges if x[0]<=va<x[1]]
  if not matches:return {'target':hex(va),'unwind':'none'}
  b,e,u=matches[0];assert b==va and e-b<=0x8000;f=freeze(va,rt.code(va,e-b));return {'target':hex(va),'instruction_count':f['reachable_instruction_count'],'unresolved_edges':f['unresolved_edges']}
 for off in range(0,size-0xc8,8):
  col=struct.unpack_from('<Q',blob,off)[0]
  if not rt.base<=col<=rt.base+rt.pr.image_size-24:continue
  cr=col-rt.base;header=rt.code(cr,24);sig,vo,cd,td,ch,selfr=struct.unpack('<6I',header)
  if sig!=1 or selfr!=cr or vo!=0 or not 0<td<rt.pr.image_size-176:continue
  rawname=rt.code(td+0x10,160).split(b'\0')[0]
  if not rawname.startswith(b'.?AV'):continue
  name=rawname.decode('ascii','replace')
  if name not in ('.?AVCHasWarTogetherTrigger@@','.?AVCAnyAlliedCountryTrigger@@','.?AVCAllAlliedCountryTrigger@@'):continue  # CTriggerEntry factory tables are short: never read A8/B0 there
  vt=start+off+8
  if name in seen:continue
  seen.add(name);tooltip,evaluator=struct.unpack_from('<QQ',blob,off+8+0xa8);assert rt.base<=tooltip<rt.base+rt.pr.image_size and rt.base<=evaluator<rt.base+rt.pr.image_size
  candidates.append({'class_name':name,'vtable_rva':hex(vt),'tooltip':fn(tooltip-rt.base),'evaluator':fn(evaluator-rt.base)})
 stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'tokens':tokens,'manager':hex(manager),'pool':hex(pool),'pool_count':pool_count,'groups':summaries,'references':rows,'outcomes_present':sorted(outcomes),'inspection_limit_per_group':32,'group_limit':2,'functions':functions,'ally_vtable_scan':{'start':hex(start),'size':size,'matches':candidates,'scope':'bounded cluster only; not global absence; no null-faction resampling'},'stable_dependencies':stable,'raw_dependencies':[{'address':hex(a),'size':n,'hex':b.hex()} for (a,n),b in sorted(r.samples.items())],'correction':'Initial probe key reference_result_byte was provisional/misleading: raw group+c8 byte+4 is a SIDE selector, NOT victory. D3B290 transforms explicit win and defensive_victory into selector. First two old rows were both own-side wins, not win/loss contrast. Raw values unchanged.','history_active_bridge_proved':False}
 (Q/'t229_winner_semantics_and_ally_pivot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('functions','raw_dependencies','tokens','references')},ensure_ascii=False,indent=2));print('rows',len(rows),'outcomes',sorted(outcomes));print('FIRST_LAST',rows[:2],rows[-2:])
finally:rt.close()
