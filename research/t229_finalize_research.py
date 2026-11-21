# Machine-specific read-only final binding + authorized research/document seal. No game mutations.
import sys,json,hashlib,struct,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');R=Q.parent
inventory=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
assert inventory.read_bytes()==(Q/'t229_inventory_before.md').read_bytes() and H(inventory.read_bytes())==target
prev=json.loads((Q/'t228_final_seal.json').read_text(encoding='utf-8'));prod=prev['production_hashes']
for name,h in prod.items():assert H((R/name).read_bytes())==h
reg=json.loads((Q/'t229_regression_results.json').read_text());assert reg['successful'] and reg['unique_methods']==30 and reg['total_invocations']==60 and reg['suite_runs']==2 and reg['final_failures']==reg['final_errors']==0
cor=json.loads((Q/'t229_research_corrections.json').read_text());assert H((Q/'t229_initial_probe_sources.zip').read_bytes())==cor['initial_sources_archive_sha256']
for name,key in [('t229_winner_semantics_and_ally_pivot.py','corrected_second_probe_source_sha256'),('t229_named_pivot_closure.py','corrected_third_probe_source_sha256')]:assert H((Q/name).read_bytes())==cor[key]
rt=Runtime()
try:
 before=rt.guard();assert before['pid']==10288 and before['base']=='0x7ff758fc0000' and before['country_index']==3 and before['pause']==1 and before['speed_slot']==0 and before['hour_tick']==60781105 and not any(before['markers'].values())
 version=rt.code(0x2795083,48).split(b'\0')[0].decode();assert version=='1.19.5.0.7c6c'
 native={}
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:native[hex(va)]=H(rt.code(va,n));assert native[hex(va)]==prev['native_controls'][hex(va)]
 checked={};oldpins=json.loads((Q/'t227_native_code_pins.json').read_text())
 for fn,pins in oldpins.items():
  d=json.loads((Q/fn).read_text(encoding='utf-8'))
  for va,h in pins.items():assert H(rt.code(int(va,16),d['functions'][va]['window_size']))==h;checked[va]=h
 chain=json.loads((Q/'t228_native_text_chain.json').read_text());pins=json.loads((Q/'t228_native_text_pins.json').read_text())
 for va,h in pins.items():assert H(rt.code(int(va,16),chain['functions'][va]['window_size']))==h;checked[va]=h
 assert checked==prev['rechecked_native_function_hashes'] and len(checked)==19
 fs={}
 for name in ['t229_winner_semantics_and_ally_pivot.json','t229_named_pivot_closure.json']:fs.update(json.loads((Q/name).read_text(encoding='utf-8'))['functions'])
 fs['0x178f070']=json.loads((Q/'t229_history_winner_probe.json').read_text())['ui_function'];newpins=json.loads((Q/'t229_accepted_native_pins.json').read_text());assert len(newpins)==13
 for va,h in newpins.items():assert H(rt.code(int(va,16),fs[va]['window_size']))==h;checked[va]=h
 assert len(checked)==32
 # New Runtime-derived heap entrances; prior heap-address strings never loaded as targets.
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';roots=r.array(rt.gs+0x880,2048);manager=roots[rt.index];r.q(manager);assert rt.cls(manager)=='.?AVCManager@NCombatLog@@'
 groups=r.array(manager+8,128);matches=[]
 for gp in groups:
  r.q(gp);assert 'COrdersGroupLogs' in rt.cls(gp)
  if r.q(gp+0xe0)==0x100000035:matches.append(gp)
 assert len(matches)==1;gp=matches[0];ptr,cap,n=struct.unpack('<QII',r.exact(gp+0xc8,16));assert n==151 and n<=cap<=100000
 pool=r.q(rt.base+0x33ea870);poolcap=r.i(rt.base+0x33ea878);poolcount=r.i(rt.base+0x33ea87c);assert poolcount==247 and poolcount<=poolcap<=100000
 refcounts=r.q(rt.base+0x33ea888);useflags=r.q(rt.base+0x33ea8a0);controls=[]
 for ordinal,expected in [(0,(212,0,1,True)),(13,(5,1,1,False))]:
  raw=r.exact(ptr+ordinal*8,8);idx,selector=struct.unpack_from('<IB',raw);assert idx<poolcount and selector in (0,1)
  rec=pool+idx*0x448;r.q(rec);assert 'SCombatData' in rt.cls(rec);defensive=r.exact(rec+0x444,1)[0];assert defensive in (0,1);win=bool(selector^defensive)
  assert (idx,selector,defensive,win)==expected;rc=struct.unpack('<h',r.exact(refcounts+idx*2,2))[0];used=r.exact(useflags+idx,1)[0];assert rc>0 and used==1
  controls.append(dict(ordinal=ordinal,pool_index=idx,side_selector=selector,defensive_victory=defensive,native_group_win_reconstructed=win,positive_native_refcount=rc,native_slot_in_use=used))
 active=[]
 for cp in r.array(rt.gs+0x268,4096):
  uid=r.i(cp+0x1c)
  if uid not in (3072,3096,3097):continue
  r.require(cp,'CLandCombat');assert r.i(cp+0x18)==62;active.append(dict(type=62,combat_id=uid,in_history_pool_index_domain=0<=uid<poolcount))
 assert {x['combat_id'] for x in active}=={3072,3096,3097} and not any(x['in_history_pool_index_domain'] for x in active)
 stable=r.stable();after=rt.guard();assert before==after
finally:rt.close()
for name,h in prod.items():assert H((R/name).read_bytes())==h
old=inventory.read_bytes();assert old==(Q/'t229_inventory_before.md').read_bytes() and H(old)==target
s=old.decode('utf-8');assert s.count('| 字段名 | 已验证/未验证 | 说明 |')==14 and s.count('| 已验证 |')==87 and s.count('| 未验证 |')==29
seal={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'version':version,'country_tag':'SOV','native_controls':native,'rechecked_native_function_count':len(checked),'prior_native_function_count':19,'current_native_proof_windows':13,'rechecked_native_function_hashes':checked,'fresh_selected_history_controls':controls,'fresh_active_controls':active,'unique_history_samples':14,'initial2_subset_of14':True,'wins':13,'losses':1,'new_unique_samples_in_final_control_rebind':0,'exact_active_history_bridge_proved':False,'schema_result_samples':0,'new_friendly_samples':0,'live_faction_resampling':0,'stable_dependencies':stable,'inventory_sha256':target,'counts':{'tables':14,'fields':116,'columns':3,'verified':87,'unverified':29,'unverified_memory':17,'unverified_nonmemory':12},'production_hashes':prod,'production_baseline_fields':51,'fingerprint_gates_unchanged':True,'game_writes':0,'post':0,'native_calls':0,'formatter_calls':0,'save_access':0,'time_advance':0,'pause_speed_changes':0,'UI_changes':0,'full_capture':False,'commit_push':False,'generic_production_changes':False,'windows_test_replay':0,'old_suites':0,'regression':reg,'checkpoint_sha256':H((Q/'t229_checkpoint.md').read_bytes()),'inventory_changed_rows':0,'promotions':[],'crisis_scope':'unchanged prior3/25members witness only; group cached notes; composedkind; no severity/fullCrisis/feed/Input','next_target':'world.shortages.missing_divisions independently named frontline staffing consumer + actual own-front membership and genuine controls; no desiredforce or aggregate substitution'}
(Q/'t229_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
body='\r\n\r\n## t229 — 原生历史胜负已证，活动编号连接仍不升格\r\n独立具名win(E3)、defensive_victory3756与精确logger证明groupwin=selector XOR defensive_victory。14唯一历史引用（初始2条包含其中），13胜/1负；212与5为真实正负对照，214与5同selector但相反胜负。selector不是result；247为池槽数非战斗普查。活动type62/3072、3096、3097没有精确历史ID连接，故0升格。共同战争具名触发器与盟国scope为不同静态转向，无新外国友军样本、不再重采nullfaction。3个短factory槽及leaf后的邻居literal误归属均拒绝并保留原始源码审计ZIP。30唯一测试/2轮60调用；首轮15失败11错误因checker误拒精确序列化尾跳，修正后全30通过，Windows0旧套件0。清单保持87/29（17内存12非内存），14表116字段3列及SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3；生产51/指纹门/四哈希不变，游戏写入调用推进UI变化均0。危机3/25见证、组级缓存说明与非完整feed边界不变。详见records/t229_checkpoint.md及t229_final_seal.json。下一候选missing_divisions独立具名前线缺编消费者，需真实己方前线与正负样本，不以期望兵力或单位汇总替代。\r\n'
assert b'## t229 ' not in (A/'README.md').read_bytes()
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if (p.name.startswith('t229_') or p.name.startswith('test_t229_')) and p.suffix in ('.json','.py','.md') and p.name!='t229_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inventory]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
audit=Q/'t229_initial_probe_sources.zip';manifest={'at_est':datetime.datetime.now().astimezone().isoformat(),'authority':str(A),'record_count':len(files)-2,'new_research_record_count':len(selected),'inventory_sha256':target,'audit_archive':{'path':audit.name,'size':audit.stat().st_size,'sha256':H(audit.read_bytes())},'entries':[{'path':p.relative_to(A).as_posix(),'size':p.stat().st_size,'sha256':H(p.read_bytes())} for p in files]}
mp=Q/'t229_authority_manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t229_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,'t229_authority_manifest.json');z.write(audit,'audit/'+audit.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps({'seal_at_est':seal['at_est'],'guard':before,'counts':seal['counts'],'inventory_sha256':target,'checkpoint_sha256':seal['checkpoint_sha256'],'native_functions_rechecked':len(checked),'stable_dependencies':stable,'selected_controls':controls,'authority_records':manifest['record_count'],'new_research_records':len(selected),'archive':str(archive),'archive_sha256':H(archive.read_bytes()),'archive_bytes':archive.stat().st_size},ensure_ascii=False,indent=2))
