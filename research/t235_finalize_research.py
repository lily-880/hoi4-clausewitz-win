# Read-only game revalidation; C docs/research checkpoint only, never game saves.
import sys,json,struct,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest()
A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
prev=json.loads((Q/'t234_final_seal.json').read_text(encoding='utf-8'))
parent=json.loads((Q/'t234_authority_manifest.json').read_text(encoding='utf-8'))
P=json.loads((Q/'t235_country_intel_and_front_full.json').read_text(encoding='utf-8'))
reg=json.loads((Q/'t235_regression_attempt1.json').read_text(encoding='utf-8'))
pins=json.loads((Q/'t235_all_native_pins.json').read_text(encoding='utf-8'))
assert len(pins)==106
assert reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==17 and reg['suite_starts']==reg['completed_suite_runs']==1
assert reg['failures']==reg['errors']==reg['collection_failures']==0
assert H(inv.read_bytes())==target and inv.read_bytes()==(Q/'t235_inventory_before.md').read_bytes()
for e in parent['entries']:assert H((A/e['path']).read_bytes())==e['sha256']
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 before=rt.guard();assert before==prev['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 for va,pin in pins.items():assert H(rt.code(int(va,16),pin['window_size']))==pin['sha256']
 # Recheck exact named token and descriptor code-derived pointer only; no pending-list or observer scan.
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 assert r.exact(rt.base+0x368f570,1)==b'\x01';table=r.q(rt.base+0x368f5a0)
 name=r.string(table+0x338f*32);assert name=='frontage_full' and P['front_full_token']==dict(id=13199,name=name)
 raw=rt.code(0x2a001,7);assert raw[:3]==b'\x48\x8d\x0d';vt=0x2a008+struct.unpack_from('<i',raw,3)[0];assert vt==0x2834cc8
 slots=struct.unpack('<2Q',rt.code(vt,16));assert tuple(p-rt.base for p in slots)==(0x3111c0,0x493900)
 stable=r.stable();after=rt.guard();assert after==before
finally:rt.close()
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
assert H(inv.read_bytes())==target
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',production_baseline_fields=51,production_hashes=prev['production_hashes'],native_controls=prev['native_controls'],rechecked_native_function_hashes={k:v['sha256'] for k,v in pins.items()},rechecked_native_function_count=106,prior_native_count=93,new_native_windows=13,front_full_token=dict(id=13199,name=name),descriptor_proved_methods=['0x3111c0','0x493900'],stable_dependencies=stable,schema_unit_confidence_positive_samples=0,schema_unit_confidence_negative_samples=0,schema_manpower_front_cannot_hold_samples=0,new_foreign_units_inspected=0,observer_entries_read=0,promotions=[],counts=dict(verified=87,unverified=29,unverified_memory=17,unverified_nonmemory=12,tables=14,fields=116,columns=3),inventory_changed_rows=0,inventory_sha256=target,checkpoint_sha256=H((Q/'t235_checkpoint.md').read_bytes()),regression=reg,research_launches=4,research_successes=4,research_failures=0,final_seal_launches=1,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,commit_push=False,generic_production_changes=False,background_tasks_started=0,next_target='frontage_full evaluator from factory493900 vtable2832D50: subject and capacity inputs first; not automatically manpower-caused hold failure; no country-intel confidence substitution')
(Q/'t235_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t235 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t235 — 国家陆军情报不是可见师置信度\r\nPID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105逐块freshguard，106原生窗口终验。三NIntel模板计数getter只返回名字；CURRENT_ARMY_INTEL具名消费者以国家tag/kind1调用14CB760，army_intel表达式独立说明country domain，非师confidence。ASCII confidence0只为有界字符串发现，不是全局不存在证明。frontage_full(token338F)具名front-full入口与descriptor factory493900已证，但不是缺人导致战略战线守不住；不推导字段。0升格/0置信度样本/0新外军或observer读取。17唯一离线测试1次17通过，研究4启动全成功。清单87/29(17内存12非内存)、14表116字段3列与SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变；生产51/门/四哈希/指纹未改，游戏写入/Post/调用/存档/推进/UI全0。详见records/t235_checkpoint.md及final_seal。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t235_') or p.name.startswith('test_t235_')) and p.suffix in ('.py','.json','.md') and p.name!='t235_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=datetime.datetime.now().astimezone().isoformat(),authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files])
mp=Q/'t235_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t235_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=106,stable_dependencies=stable,records=m['record_count'],new_records=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
