# Machine-specific read-only terminal guard and research/docs checkpoint; never game saves/calls.
import sys,json,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q));from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
parent=json.loads((Q/'t240_final_authority_manifest.json').read_text(encoding='utf-8'));G=json.loads((Q/'t241_fresh_guard.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t241_all_native_pins.json').read_text(encoding='utf-8'));reg=json.loads((Q/'t241_regression_attempt1.json').read_text(encoding='utf-8'))
assert parent['record_count']==648 and len(pins)==175 and reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==20 and reg['targeted_methods']==17 and reg['shared_methods']==3 and reg['suite_starts']==reg['completed_suite_runs']==1 and reg['failures']==reg['errors']==reg['collection_failures']==0
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
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',stable_dependencies=stable,rechecked_prior_native_windows=172,current_captured_windows=3,new_native_windows=3,rechecked_total_native_windows=175,rechecked_native_pins=pins,production_baseline_fields=51,production_hashes=G['production_hashes'],native_controls=G['native_controls'],inventory_sha256=target,counts=dict(verified=87,unverified=29,memory=17,nonmemory=12,tables=14,fields=116,columns=3),promotions=[],inventory_changed_rows=0,named_country_lookup_requests=4,lookup_bucket_keys_inspected=4,lookup_positive_samples=3,lookup_negative_samples=1,directional_subject_positive_pairs=1,directional_subject_negative_pairs=1,positive_pair='MAN113->JAP48',negative_pair='JAP48->MAN113',negative_dependency_record_present=True,negative_same_puppet_discriminator=True,player_relative_positive_samples=0,current_visibility_checks=0,current_visible_owner_bridges=0,projections_are_not_raw_fields=True,foreign_country_object_census=0,current_D04_negative_repolls=0,own_unary_negative_repolls=0,plan_instances_inspected=0,new_crisis_members_inspected=0,notes_reads=0,alert43_cache_reads=0,regression=reg,research_executions=4,research_successes=3,research_execution_failures=1,research_failure_reason='Unsupported polymorphic lookup-root assumption; Runtime.cls AssertionError, source and failure1 preserved; corrected plain-layout collector makes no class claim.',research_unique_successful_collectors=3,fresh_guard_executions=1,final_seal_executions=1,remote_spawn_failures=0,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,generic_production_edits=False,commit_push=False,background_tasks_started=0,checkpoint_sha256=H((Q/'t241_checkpoint.md').read_bytes()),next_target='Independently named allied/friendly pair evaluator (candidate faction-with/allied consumer), exact source/target and bounded SOV/MON versus JAP controls, never null-faction/nonwar inference. No more MAN/JAP or D04 negative polls. Current qualified visible-owner plus fresh visibility mandatory before promotion; pivot if no productive distinct-consumer route.')
(Q/'t241_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t241 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t241 — 定向国家查找与真实属国方向正反例，仍不冒充玩家可见关系\r\n763E10是FNV1a32字符串查找，763EA0是有界countryref数组访问；1D5170精确bucket.last逆链到first，未调用。根33DF288由native ETH消费者RIP推导。首次bucket收集误当polymorphic触发RTTI断言，失败原稿/记录保留；修正plainlayout不作类名声明。仅4定向lookup共4key：MAN113/JAP48/SOV3正确映射，QZQ桶有RHD但不相等故miss，非census。真实MAN→JAP父引用48+puppetflag1且dependency30D1双方48为正；JAP→MAN同样存在30D1记录但48≠113且无父/level为负，证明方向不能从记录存在/类型推出。两bool明确是native输入离线投影，非原始schema字段；JAP不是玩家SOV3，无新visibility或可见owner桥，0升格。175窗口=172旧+3新终验，生产51/四hash/门不变。20唯一方法17专项3共享1轮20调用全过；研究4执行3成功1RTTI断言失败，guard/seal各1另计，0spawn失败。清单87/29(17memory12nonmemory)，14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无后台或生产改动。下步具名allied/friendly消费者与定向真实对照，非nullfaction/nonwar推理。详见records/t241_checkpoint.md及final_seal。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t241_') or p.name.startswith('test_t241_')) and p.suffix in ('.py','.json','.md') and 'authority_manifest' not in p.name)
for p in selected:
 dst=A/'records'/p.name;assert not dst.exists();dst.write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=seal['at_est'],authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t241_final_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t241_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=175,records=m['record_count'],files=len(files),new_record_count=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
