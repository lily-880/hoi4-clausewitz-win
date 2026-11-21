"""Frozen t229 native history evidence and rejected ID bridge; no IO/game backend.
Research win/loss is not emitted as schema combat.result without an identity bridge.
"""
import hashlib,struct
from t227_qualified_crisis_replay import Frozen,Unproved,need
BASE=0x7ff758fc0000
PINS={'0xd39310': '90f2aaeff1aeebe3c6568922e9f7d6ff4fe7f8f5ee5e8dc35bbe937d03828daf', '0xd3b290': 'ad5af92c04b0754a7617c97a14d3907d2d35b6305ccce594fd549c6d4154dc4c', '0xd3b6d0': '046b0f4b8747cf58dd833e578385d918f9b45207937db8194fbc49b5bebcf8e0', '0xd40810': '669d0e9b85f41da323b4352430f564f9c580789b51ebc84db9849b21cce832ce', '0xd40a40': '8839dca1d9c945a5eebb50662f334f36bad74d2eaa40a36d0b70f4ab311be227', '0x439620': '02aa184dd303d3b4648496edd7e72a8a5cf39b1397f431a1bfd6e6a6acdc5331', '0x3f78c0': 'eeb3fd2dfbf107312741928327c675f109404111b9a09bd455ee96d05311ece1', '0x17f590': '0447390450f1bda1a0fe30fc707de71139453c83935fd8ec7a28b0712037ac9c', '0x3ec970': '7529d594bc1753fedabda880e3f46debc6b484ff6e3f3bb8c7db4b04a70bbddb', '0x4517e0': '6778017835dd3aff9f478cf42e2c2f2cc280284792e7ce4b3f27adde3f4bb5f7', '0x3eba10': 'debc14cc8afa008586aa77ce50fdf1ca085b5e70516d3060bc8273f0fdad8496', '0xd86fe0': '9940f0fa6355be0c6438f3a9f22eaae50501d85084f43aa87528f5a1ce2a958d', '0x178f070': '6df0aa632c90b9fbe28ff994f5af18b1c90a1653f20eb336092818e76103cb1b'}
FULL={'.?AVCHasWarTogetherTrigger@@','.?AVCAnyAlliedCountryTrigger@@','.?AVCAllAlliedCountryTrigger@@'}
def group_won(selector,defensive):
 need(type(selector) is int and selector in (0,1) and type(defensive) is int and defensive in (0,1),'native boolean inputs')
 return bool(selector^defensive)
def replay(first,second,pivot):
 for d in (first,second,pivot):
  g=d['before'];need(g==d['after'],'unstable guard');need(g['pid']==10288 and g['base']==hex(BASE) and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values()),'session gate')
 need(first['before']==second['before']==pivot['before'],'mixed session')
 fs={a:f for a,f in second['functions'].items() if a in PINS};fs.update(pivot['functions']);fs['0x178f070']=first['ui_function']
 for a,h in PINS.items():
  need(a in fs,'missing accepted native proof');f=fs[a];need(f['sha256']==h and hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()==h,'native integrity')
  if a=='0x178f070':need(len(f['unresolved_edges'])==2,'UI remains partial, not globally closed')
  else:
   need(not f['unresolved_edges'],'open accepted native proof')
   expected_tails=[{'site':'0xd40b0a','target':'0x2546250'}] if a=='0xd40a40' else []
   need(f['external_tails']==expected_tails,'unexpected native external tail')  # explicit known serializer tail, never invoked
 def ops(a,*want):
  got={x.partition(' ')[2] for x in fs[a]['asm']};need(all(x in got for x in want),'native semantic operands')
 ops('0xd40810','shr r8b, 1','and r8b, 1','mov edx, 0xe3')
 ops('0xd40a40','movzx r8d, byte ptr [rdi + 0x444]','mov edx, 0x3756','movzx r8d, byte ptr [rdi + 0x447]','mov edx, 0x4dbc')
 ops('0xd3b6d0','shr r9b, 1','and r9b, 1','mov r8d, dword ptr [rsp + 0x38]','call 0xd3b290','call 0xd394e0')
 ops('0xd3b290','movzx ecx, byte ptr [rax + 0x444]','test sil, sil','test cl, cl','mov al, 1','xor al, al','mov byte ptr [rsp + 0x9c], al','mov dword ptr [rsp + 0x98], ebp')
 ops('0x178f070','movzx r8d, byte ptr [rax + 0x444]','cmp byte ptr [rbx + 0x28], al','sete al','cmp r8d, eax','setne dl')
 expected={0xe3:'win',0x3756:'defensive_victory',0x4dbc:'player_is_attacker'}
 tt={x['token']:x for x in second['tokens']};need(set(tt)==set(expected),'named keyword set')
 for token,name in expected.items():
  t=tt[token];need(t['name']==t['actual_name']==name,'native keyword name');b=bytes.fromhex(t['registration_raw_hex']);need(b[:3]==b'\x4c\x8d\x05' and int(t['registration_rva'],16)+7+struct.unpack_from('<i',b,3)[0]==int(t['literal_rva'],16),'keyword RIP provenance')
 need(second['history_active_bridge_proved'] is False,'no independent bridge certificate')
 fm,sm=Frozen(first),Frozen(second);gs=int(first['before']['gs'],16);index=3
 roots=fm.array(gs+0x880,2048);manager=roots[index];need(hex(manager)==first['manager']==second['manager'] and sm.array(gs+0x880,2048)[index]==manager,'history manager country root')
 pool=fm.q(BASE+0x33ea870);count=fm.i(BASE+0x33ea87c);need(pool==sm.q(BASE+0x33ea870) and count==sm.i(BASE+0x33ea87c)==first['pool_count']==second['pool_count']==247,'pool namespace')
 need(hex(pool)==first['pool']==second['pool'],'pool pointer')
 groups=sm.array(manager+8,128);need(second['inspection_limit_per_group']==32 and second['group_limit']==2,'bounded outcome scan');rows=second['references'];need(len(rows)==14 and len({x['record_index'] for x in rows})==14,'fourteen unique retained references')
 result=[]
 for row in rows:
  gp=int(row['group'],16);need(gp in groups,'group membership');ptr,cap,n=struct.unpack('<QII',sm.read(gp+0xc8,16));j=row['ordinal'];need(0<=j<min(n,32) and n<=cap<=100000,'reference bound');idx,side=struct.unpack_from('<IB',sm.read(ptr+j*8,8));need(0<=idx<count,'pool index bound');rec=pool+idx*0x448;defvic=sm.read(rec+0x444,1)[0];pa=sm.read(rec+0x447,1)[0];won=group_won(side,defvic)
  need((idx,side,defvic,pa,hex(rec),hex(ptr+j*8),sm.q(gp+0xe0))==(row['record_index'],row['side_selector'],row['defensive_victory'],row['player_is_attacker'],row['record'],row['reference_address'],int(row['group_handle'],16)),'raw history join')
  need(won==row['native_group_won_reconstructed'],'raw win reconstruction');result.append({'history_pool_index':idx,'side_selector':side,'defensive_victory':defvic,'group_won':won})
 need({r['group_won'] for r in result}=={False,True} and second['outcomes_present']==[False,True],'actual win loss contrast')
 by={x['history_pool_index']:x for x in result};need(by[212]['group_won'] and by[214]['group_won'] and not by[5]['group_won'],'actual selected outcome controls')
 # Initial two rows are a SUBSET of the14, not two extra unique samples or outcome contrast.
 for row in first['references']:
  e=by[row['record_index']];need(row['reference_result_byte']==e['side_selector'] and e['group_won'],'initial field is selector, both initial outcomes win')
 active=[]
 for row in first['active_controls']:
  cp=int(row['combat'],16);need(cp in fm.array(gs+0x268,4096),'active registry');uid=fm.i(cp+0x1c);typ=fm.i(cp+0x18);need(typ==row['type']==62 and uid==row['combat_id'],'native active handle');need(row['id_in_history_pool_index_range']==(0<=uid<count),'active range audit');active.append(uid)
 need(set(active)=={3072,3096,3097} and all(i>=count for i in active),'actual distinct ID namespace controls')
 bindings=pivot['full_trigger_bindings'];need({x['class_name'] for x in bindings}==FULL and len(bindings)==3,'reject short factory interfaces')
 for row in bindings:
  slots=set(row['slots']);need(slots==({'0xa8','0xb0'} if 'HasWarTogether' in row['class_name'] else {'0xa8','0xb0','0xc0'}),'virtual slot bound')
 ops('0x3f78c0','call 0xd86fe0');ops('0xd86fe0','movzx eax, byte ptr [rcx + 0x310]','ret ')
 ops('0x4517e0','cmp qword ptr [rcx + 0x2d8], 0','sete al')
 ops('0x3ec970','call qword ptr [rax + 0xc0]','mov rax, qword ptr [rcx + 0x2d8]','mov rbx, qword ptr [rax + 0x58]')
 ops('0x3eba10','call qword ptr [rax + 0xc0]','mov rax, qword ptr [rcx + 0x2d8]','mov rbx, qword ptr [rax + 0x58]')
 accepted_literals=[];rejected_literals=[]
 for x in pivot['named_literals']:
  reachable={int(v.split(' ',1)[0],16) for v in fs[x['function']]['asm']}
  (accepted_literals if int(x['site'],16) in reachable else rejected_literals).append(x['text'])
 need('TRIGGER_HAS_WAR_TOGETHER_WITH' in accepted_literals,'independent named common-war consumer');need(pivot['live_faction_resampling']==0 and pivot['new_friendly_samples']==0,'no faction loop or invented friend positive')
 return {'retained_research_results':result,'unique_retained_references':14,'initial_two_overlap':True,'active_id_controls':sorted(active),'pool_count':count,'native_active_history_id_bridge':False,'schema_combats':[],'result_exported':False,'relation_exported':False,'new_foreign_friendly_positives':0,'common_war_flag_offset':'0x310','allied_scope_uses_faction_roster':True,'valid_pivot_classes':sorted(FULL),'rejected_factory_classes':pivot['rejected_factory_rows'],'ignored_unreachable_neighbor_literals':rejected_literals,'ui_generic_flow_partial':True,'new_promotions':0,'complete_input':False,'complete_crisis_feed':False,'notes_scope_preserved':'group advisory with3/25sampled causal witness; kind composed, not native enum','reason':'Actual native retained win/loss proved; exact active-combat/history identity bridge absent. Common-war flag is not a friendly enum; allied-scope collection still faction-gated. No date/side/correlation substitution.'}
