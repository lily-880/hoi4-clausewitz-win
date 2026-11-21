# Machine-specific read-only terminal guard and research/docs checkpoint; never game saves/calls.
import sys,json,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q));from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
parent=json.loads((Q/'t238_final_authority_manifest.json').read_text(encoding='utf-8'));G=json.loads((Q/'t239_fresh_guard.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t239_all_native_pins.json').read_text(encoding='utf-8'));reg=json.loads((Q/'t239_regression_attempt1.json').read_text(encoding='utf-8'))
assert parent['record_count']==608 and len(pins)==164 and reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==20 and reg['targeted_methods']==17 and reg['shared_methods']==3 and reg['suite_starts']==reg['completed_suite_runs']==1 and reg['failures']==reg['errors']==reg['collection_failures']==0
assert H(inv.read_bytes())==target and inv.read_bytes()==(Q/'t236_inventory_before.md').read_bytes()
for e in parent['entries']:assert H((A/e['path']).read_bytes())==e['sha256']
for name,h in G['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 before=rt.guard();assert before==G['before'];assert before['pause']==1 and before['speed_slot']==0 and not any(before['markers'].values());assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==G['native_controls'][hex(va)]
 for p in pins.values():assert H(rt.code(int(p['window_start'],16),p['window_size']))==p['sha256']
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';stable=r.stable();after=rt.guard();assert after==before
finally:rt.close()
for name,h in G['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
assert H(inv.read_bytes())==target
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',stable_dependencies=stable,rechecked_prior_native_windows=154,current_captured_windows=10,new_native_windows=10,rechecked_total_native_windows=164,rechecked_native_pins=pins,production_baseline_fields=51,production_hashes=G['production_hashes'],native_controls=G['native_controls'],pending_t236_resolved=True,prior_pending_audit_preserved=True,inventory_sha256=target,counts=dict(verified=87,unverified=29,memory=17,nonmemory=12,tables=14,fields=116,columns=3),promotions=[],inventory_changed_rows=0,plan_type_positive_samples=0,plan_type_negative_samples=0,axis_positive_samples=0,axis_negative_samples=0,foreign_relation_positive_samples=0,foreign_relation_negative_samples=0,actual_current_country_lookup=dict(raw_index=3,canonical_index=3,tag='SOV',not_a_new_field_control=True),plan_instances_inspected=0,own_plan_registries_read=0,foreign_unit_country_faction_census=0,new_crisis_members_inspected=0,notes_reads=0,alert43_cache_reads=0,tutorial_helpers_not_invoked=True,tutorial_helper_observed_contract='Writes tutorial+50 and passes named string to opaque virtual call; not qualified read-only bool getter; no debug-symbol signature or event/audio-role claim',offensive_helper_uses_verified_vertices_not_axis=True,relation_named_tooltips_only_not_evaluator_proof=True,regression=reg,research_executions=4,research_successes=4,research_failures=0,fresh_guard_executions=1,offline_vertex_excerpt_generations=1,final_seal_executions=1,remote_spawn_failures=0,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,generic_production_edits=False,commit_push=False,background_tasks_started=0,checkpoint_sha256=H((Q/'t239_checkpoint.md').read_bytes()),next_target='Recover real trigger table/evaluator for named441970(TRIGGER_IS_PUPPET)/442B60(TRIGGER_IS_SUBJECT); exact directional overlord-to-player identity and visible-unit owner bridge, not unary-any-subject/faction/nonwar inference. Require actual controls before promotion.')
(Q/'t239_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t239 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t239 — 教程回调非只读getter；offensive匹配旧vertex非axis，转属国关系消费者\r\nfreshPID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，154旧+10新=164窗口终验；生产51/四哈希/门不变。1A57380/1A57590实际会写教程+50并传tutorial_objective_done给不透明虚调用，未调用且不能当只读bool。country引用经C07BF0/C08790/+340重映射到+310国家表，现场3→3→SOV；C085F0只比规范化索引非外交。frontline含type2+A8+ETH额外条件，不能type2命名。10B9240递归子计划+70匹配并收集指针，独立现有reader哈希证明+70已是vertex，非axis。新TRIGGER_IS_PUPPET441970/IS_SUBJECT442B60具名入口仅tooltip，下一步须独立触发器求值器和相对玩家overlord身份、可见部队owner桥，非任意属国/非战友好。0新字段真实样本/0plan或派系扫描/0升格。20唯一离线方法(17专项3共享)1轮全过；研究4执行全成功，guard/离线摘录/finalseal另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无生产编辑/提交。详见records/t239_checkpoint.md及final_seal。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t239_') or p.name.startswith('test_t239_')) and p.suffix in ('.py','.json','.md') and 'authority_manifest' not in p.name)
for p in selected:
 dst=A/'records'/p.name;assert not dst.exists();dst.write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=seal['at_est'],authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t239_final_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t239_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=164,records=m['record_count'],files=len(files),new_record_count=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
