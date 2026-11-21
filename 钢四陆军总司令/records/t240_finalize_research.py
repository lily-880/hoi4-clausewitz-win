# Machine-specific read-only terminal guard and research/docs checkpoint; never game saves/calls.
import sys,json,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q));from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
parent=json.loads((Q/'t239_final_authority_manifest.json').read_text(encoding='utf-8'));G=json.loads((Q/'t240_fresh_guard.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t240_all_native_pins.json').read_text(encoding='utf-8'));reg=json.loads((Q/'t240_regression_attempt1.json').read_text(encoding='utf-8'))
assert parent['record_count']==627 and len(pins)==172 and reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==20 and reg['targeted_methods']==17 and reg['shared_methods']==3 and reg['suite_starts']==reg['completed_suite_runs']==1 and reg['failures']==reg['errors']==reg['collection_failures']==0
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
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',stable_dependencies=stable,rechecked_prior_native_windows=164,current_captured_windows=8,new_native_windows=8,rechecked_total_native_windows=172,rechecked_native_pins=pins,production_baseline_fields=51,production_hashes=G['production_hashes'],native_controls=G['native_controls'],inventory_sha256=target,counts=dict(verified=87,unverified=29,memory=17,nonmemory=12,tables=14,fields=116,columns=3),promotions=[],inventory_changed_rows=0,own_unary_negative_samples=1,current_owner_directional_negative_samples=1,current_owner_directional_positive_samples=0,current_visibility_revalidated=False,foreign_relation_promotion_qualified=False,actual_current_owner=dict(combat=3072,unit=399,raw_ref=368,canonical_index=368,country_tag='D04',target_player_index=3),historical_owner443_not_reused=True,foreign_unit_country_faction_census=0,own_plan_registries_read=0,plan_instances_inspected=0,new_crisis_members_inspected=0,notes_reads=0,alert43_cache_reads=0,unary_trigger_is_not_player_relation=True,named_binary_trigger_evaluators_bound=True,exact_consumed_token=dict(id=0x30d1,name='puppet'),target_resolver_dynamic_not_fixed_field=True,zero_equality_preserved_before_nonzero_alias_guards=True,regression=reg,research_executions=6,research_successes=6,research_discovery_misses=2,research_failures=0,fresh_guard_executions=1,final_seal_executions=1,remote_spawn_failures=0,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,generic_production_edits=False,commit_push=False,background_tasks_started=0,checkpoint_sha256=H((Q/'t240_checkpoint.md').read_bytes()),next_target='Genuine live directional subject/overlord positive controls via independently decoded targeted named-country reference lookup; candidate763E10/763EA0 not invoked, no whole country census; freshly qualified visible-owner bridge required before any promotion. Do not re-poll current negative witness. Pivot distinct field if this route exhausted.')
(Q/'t240_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t240 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t240 — 精确属国方向消费者已绑定，现场负例不冒充可见关系\r\n441970/442B60真实slot22求值器3F9EE0/3FA2E0是unary；新具名PUPPET_OF441690/ SUBJECT_OF442880经3F9E40/3FA270绑定source/target方向与+188亲属国引用、按target索引关系表、D87160消费token30D1现场精确名puppet。二元slot23=1443990动态目标表达式返回输出缓冲，非固定字段。前两次RTTI空发现因TD错误限.rdata，独立CTutFrontline的.data控制纠正；不是不存在证据。fresh同session31576/SOV3/pause1/speed0/tick60781105；当前combat3072/unit399的owner368→368=D04，不沿用旧443/CHI；+188=0且对player3关系+288空，只有负例，未重新验证visibility，无友好/中立/全feed或字段升格。164旧+8新=172窗口终验；生产51/四hash/门不变。20唯一离线方法17专项3共享，一轮20调用全过；研究6执行6成0异常，其中2空发现miss，guard和seal各1另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无后台、生产改动或commit。下一步定向国家引用查找取得真实属国正例，非census；升格仍需当前可见owner桥。详见records/t240_checkpoint.md及final_seal。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t240_') or p.name.startswith('test_t240_')) and p.suffix in ('.py','.json','.md') and 'authority_manifest' not in p.name)
for p in selected:
 dst=A/'records'/p.name;assert not dst.exists();dst.write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=seal['at_est'],authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t240_final_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t240_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=172,records=m['record_count'],files=len(files),new_record_count=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
