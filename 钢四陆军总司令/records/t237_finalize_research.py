# Machine-specific read-only terminal guard and C docs checkpoint; never game saves.
import sys,json,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q));from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3';inv=A/'态势信息读取能力清单.md'
parent=json.loads((Q/'t237_reconciled_authority_manifest.json').read_text(encoding='utf-8'));G=json.loads((Q/'t237_fresh_guard.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t237_all_native_pins.json').read_text(encoding='utf-8'));reg=json.loads((Q/'t237_regression_attempt1.json').read_text(encoding='utf-8'))
assert len(pins)==142 and reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==17 and reg['suite_starts']==reg['completed_suite_runs']==1 and reg['failures']==reg['errors']==reg['collection_failures']==0
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
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',stable_dependencies=stable,rechecked_prior_native_windows=135,new_native_windows=7,rechecked_total_native_windows=142,rechecked_native_pins=pins,production_baseline_fields=51,production_hashes=G['production_hashes'],native_controls=G['native_controls'],t236_recovery_records=26,t236_pending_C_resolved=True,t236_missing_box_helpers_resolved=True,prior_pending_audit_preserved=True,inventory_sha256=target,counts=dict(verified=87,unverified=29,memory=17,nonmemory=12,tables=14,fields=116,columns=3),promotions=[],inventory_changed_rows=0,plan_status_positive_samples=0,plan_status_negative_samples=0,plan_instances_inspected=0,own_plan_registries_read=0,cached_alert43_absence_only=True,cached_alert43_not_reread_in_final_seal=True,regression=reg,research_executions=4,research_successes=3,research_failures=1,fresh_guard_executions=1,recovery_executions=1,final_seal_executions=1,remote_spawn_failures=0,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,generic_production_edits=False,commit_push=False,background_tasks_started=0,checkpoint_sha256=H((Q/'t237_checkpoint.md').read_bytes()),next_target='Bind B620C0 receiver/output at B6DD96: aggregate alert UI priority vs per-entry semantic severity; never map colors/448/3/4/thresholds automatically. No alert43/empty-plan loops.')
(Q/'t237_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t237 research' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t237 research — 计划无师警报仅聚合组键，非逐计划status\r\n恢复t23624pending+2helperJSON且保留原pending审计，C与box SHA对齐。freshPID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，135旧+7新=142原生窗口终验。具名alert_battleplans_with_no_divs29C3DD0→ID43→B6F730→B5BB40独立插入/删除与递归链；当前缓存43为空仅是缓存缺席，不是逐计划阴性或全部可执行。0plan实例/0empty-plan轮询/0升格。17唯一离线方法1轮17通过；研究4执行3成功1失败（错误假定manager有RTTI，失败源码保留），guard/recovery/finalseal另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。生产51/四哈希/指纹门不变，游戏写/Post/调用/存档/推进/UI全0。下一步仅独立判明B620C0/B6DD96是聚合UI优先级还是逐项severity，不从颜色/448推导schema。详见records/t237_checkpoint.md及final_seal。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t237_') or p.name.startswith('test_t237_')) and p.suffix in ('.py','.json','.md') and 'authority_manifest' not in p.name)
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=seal['at_est'],authority=str(A),record_count=len(files)-2,new_record_count=len(selected)-1,selected_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t237_final_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t237_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=142,records=m['record_count'],files=len(files),selected_count=len(selected),new_record_count=m['new_record_count'],checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
