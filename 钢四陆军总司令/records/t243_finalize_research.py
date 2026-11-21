# Machine-specific read-only terminal guard and research/docs checkpoint; never game saves/calls.
import sys,json,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q));from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
parent=json.loads((Q/'t242_final_authority_manifest.json').read_text(encoding='utf-8'));G=json.loads((Q/'t243_fresh_guard.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t243_all_native_pins.json').read_text(encoding='utf-8'));reg=json.loads((Q/'t243_regression_attempt1.json').read_text(encoding='utf-8'))
assert parent['record_count']==685 and len(pins)==182 and reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==12 and reg['targeted_methods']==9 and reg['shared_methods']==3 and reg['suite_starts']==reg['completed_suite_runs']==1 and reg['failures']==reg['errors']==reg['collection_failures']==0
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
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),status='STOPPED',stop_authority='Usert209u02:33EST finish current big step/save/stop; supersedes keep-running',explicit_future_continue_required=True,automatic_resume=False,further_research_scheduled=False,before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',stable_dependencies=stable,rechecked_prior_native_windows=180,current_captured_code_windows=2,new_native_windows=2,rechecked_total_native_windows=182,rechecked_native_pins=pins,production_baseline_fields=51,production_hashes=G['production_hashes'],native_controls=G['native_controls'],inventory_sha256=target,counts=dict(verified=87,unverified=29,memory=17,nonmemory=12,tables=14,fields=116,columns=3),promotions=[],inventory_changed_rows=0,C58600_loader_branch_closed_not_runtime_isolation=True,C58600_secondary_receiver_alias_caveat=True,independent_pivot_completed_before_stop='world.combats.result exact logger identity caller only',new_exact_logger_caller='0x1349260',new_exact_logger_callsite='0x1349680',active_history_identity_bridge_still_unproved=True,live_history_samples=0,live_combat_samples=0,isolated_live_unit_samples=0,isolated_positive_samples=0,current_visibility_checks=0,current_visible_owner_bridges=0,foreign_country_object_census=0,faction_puppet_repolls=0,plan_instances_inspected=0,new_crisis_members_inspected=0,notes_reads=0,regression=reg,research_executions=2,research_successes=2,research_execution_failures=0,remote_spawn_failures=0,fresh_guard_executions=1,final_seal_executions=1,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,generic_production_edits=False,commit_push=False,background_tasks_started=0,background_tasks_running=0,no_process_reads_after_this_seal=True,checkpoint_sha256=H((Q/'t243_checkpoint_STOPPED.md').read_bytes()),future_only_pending_entrance='1349260 exact caller receiver/active-history identity chain, only after explicit continue; not scheduled',next_target='NONE: STOPPED per user; no t244 or auto-resume')
(Q/'t243_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t243 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t243 — STOPPED：按用户t209u完成本步后保存停工\r\nC58600完整4950字节/1103指令确认token/加载域，secondary receiver与别名须区分，无运行时isolated证明，未执行或访问存档。停工指示到达前已转不同字段combats.result，唯一可达1349260→1349680→D3B6D0显示side+28/+30及observer+1D0结构，但active/history ID桥仍未证明，0live样本/0升格，不重推win/date。12唯一离线方法9专项3共享，一轮12调用全过；研究2执行全成，guard/seal各1另计，0失败。182窗口=180旧+2新终验，生产51四hash门不变。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/native调用/存档/推进/UI全0。此为研究文档保存，非游戏存档。终验后停止所有研究与进程读取，无后台，无自动继续或t244；须用户明确继续。详见records/t243_checkpoint_STOPPED.md及final_seal。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t243_') or p.name.startswith('test_t243_')) and p.suffix in ('.py','.json','.md') and 'authority_manifest' not in p.name)
for p in selected:
 dst=A/'records'/p.name;assert not dst.exists();dst.write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=seal['at_est'],authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t243_final_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t243_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=182,records=m['record_count'],files=len(files),new_record_count=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
