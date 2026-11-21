# Read-only game revalidation; C docs/research checkpoint only, never game saves.
import sys,json,struct,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest()
A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
prev=json.loads((Q/'t233_final_seal.json').read_text(encoding='utf-8'))
parent=json.loads((Q/'t233_authority_manifest.json').read_text(encoding='utf-8'))
P=json.loads((Q/'t234_pending_list_and_predicates.json').read_text(encoding='utf-8'))
L=json.loads((Q/'t234_relation_enqueue_callers.json').read_text(encoding='utf-8'))
reg=json.loads((Q/'t234_regression_attempt1.json').read_text(encoding='utf-8'))
pins=json.loads((Q/'t234_all_native_pins.json').read_text(encoding='utf-8'))
assert len(pins)==93
assert reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==17 and reg['suite_starts']==reg['completed_suite_runs']==1
assert reg['failures']==reg['errors']==reg['collection_failures']==0
assert H(inv.read_bytes())==target and inv.read_bytes()==(Q/'t234_inventory_before.md').read_bytes()
for e in parent['entries']:assert H((A/e['path']).read_bytes())==e['sha256']
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
assert L['lea_targets']['f7e1c0_enqueue']=='0x33eb090' and L['lea_targets']['f7b940_enqueue']=='0x33eb020'
rt=Runtime()
try:
 before=rt.guard();assert before==prev['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 for va,pin in pins.items():assert H(rt.code(int(va,16),pin['window_size']))==pin['sha256']
 # Re-derive D56B10 global list RVAs from the same live instructions; one status read, not a schema sample.
 def rip(site,size,off):
  raw=rt.code(site,size);return site+size+struct.unpack_from('<i',raw,off)[0]
 list_obj,count_rva,data_rva=rip(0xd56b16,7,3),rip(0xd56b2e,7,3),rip(0xd56b3a,7,3)
 assert (hex(list_obj),hex(count_rva),hex(data_rva))==(P['pending']['list_object_rva'],P['pending']['count_rva'],P['pending']['data_rva'])
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 count=r.i(rt.base+count_rva);data=r.q(rt.base+data_rva)
 assert count==0 and data==0 and P['pending']['count']==0 and not P['pending']['player_listed']
 pending=dict(list_object_rva=hex(list_obj),count_rva=hex(count_rva),data_rva=hex(data_rva),count=count,data=hex(data),player_country=hex(rt.country),player_listed=False)
 # Confirm the three wrapper LEAs still resolve, without reading EndBundle counters as samples.
 def lea(site):
  raw=rt.code(site,7);assert raw[0] in (0x48,0x4c) and raw[1]==0x8d;return site+7+struct.unpack_from('<i',raw,3)[0]
 assert lea(0xf7bbc1)==lea(0xf7bd98)==lea(0xf7e25c)==0x33eb090
 assert lea(0xf7b94a)==0x33eb020
 stable=r.stable();after=rt.guard();assert after==before
finally:rt.close()
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
assert H(inv.read_bytes())==target
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',production_baseline_fields=51,production_hashes=prev['production_hashes'],native_controls=prev['native_controls'],rechecked_native_function_hashes={k:v['sha256'] for k,v in pins.items()},rechecked_native_function_count=93,prior_native_count=59,new_native_windows=34,pending_list=pending,lea_second_scope='0x33eb090',lea_first_scope='0x33eb020',stable_dependencies=stable,schema_front_invalidated_positive_samples=0,schema_front_invalidated_negative_samples=0,promotions=[],counts=dict(verified=87,unverified=29,unverified_memory=17,unverified_nonmemory=12,tables=14,fields=116,columns=3),inventory_changed_rows=0,inventory_sha256=target,checkpoint_sha256=H((Q/'t234_checkpoint.md').read_bytes()),regression=reg,research_launches=3,research_successes=3,research_failures=0,final_seal_launches=1,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,commit_push=False,generic_production_changes=False,background_tasks_started=0,next_target='visible_units.visibility.confidence via independently named unit-intel confidence consumer; not NNavy INTEL_LEVEL_* defines, not opacity/tier, not 33EB090 empty/pending-zero rescans')
(Q/'t234_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t234 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t234 — 33EB090外交入队是共享flush，不是战争失效字段\r\n实际PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，逐块freshguard。F7BB20/F7BCE0/F7E1C0的LEA均入33EB090；NotifyControllerChanged仍为33EB020。独立具名DIPLOMACY_JOINED_WAR_*与pWarRelation消费者118DEF0以xor ecx,ecx调用F7E1C0，不是把交战双方作为显式参数入队。撤销保证、和平会议、事件、派系清理、志愿军与删除战区共享同一scope，故非wars.front_invalidated。D56B10复制全局pending表33EA908，当前count0/data空，不作为schema假值。748490/DA37F0无独立命名，不能当作at-war或己方前线桥。NNavy INTEL_LEVEL定义不是visibility.confidence。17唯一离线测试1次运行17通过；研究3启动全成功。清单87/29（17内存12非内存），14表116字段3列与SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变；生产51/门/指纹/四哈希未改，游戏写入/Post/调用/存档/推进/UI全0。详见records/t234_checkpoint.md、t234_final_seal.json。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t234_') or p.name.startswith('test_t234_')) and p.suffix in ('.py','.json','.md') and p.name!='t234_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=datetime.datetime.now().astimezone().isoformat(),authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files])
mp=Q/'t234_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t234_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=93,stable_dependencies=stable,records=m['record_count'],new_records=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
