# Read-only game revalidation; C docs/research checkpoint only, never game saves.
import sys,json,struct,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from t233_frozen_checks import own_membership,resolve_key
H=lambda b:hashlib.sha256(b).hexdigest()
A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
prev=json.loads((Q/'t232_final_seal.json').read_text(encoding='utf-8'));parent=json.loads((Q/'t232_authority_manifest.json').read_text(encoding='utf-8'));P=json.loads((Q/'t233_rebuild_scope_and_predicate.json').read_text(encoding='utf-8'));E=json.loads((Q/'t233_named_bundle_enqueue.json').read_text(encoding='utf-8'));reg=json.loads((Q/'t233_regression_attempt1.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t233_all_native_pins.json').read_text(encoding='utf-8'));assert len(pins)==59
assert reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==20 and reg['suite_starts']==reg['completed_suite_runs']==1
assert reg['failures']==reg['errors']==reg['collection_failures']==0
assert H(inv.read_bytes())==target and inv.read_bytes()==(Q/'t233_inventory_before.md').read_bytes()
for e in parent['entries']:assert H((A/e['path']).read_bytes())==e['sha256']
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 before=rt.guard();assert before==prev['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 for va,pin in pins.items():assert H(rt.code(int(va,16),pin['window_size']))==pin['sha256']
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';theatres=r.array(rt.country+0x168,64);assert len(theatres)==1;tp=theatres[0];r.require(tp,'CTheatre');fronts=[]
 for p in r.array(tp+0x50,4096):
  r.require(p,'CFront');area=r.q(p+0x70);r.require(area,'CControllerArea');fronts.append(dict(pointer=hex(p),kind=r.i(p+8),id=r.i(p+12),theatre_back=hex(r.q(p+0x18)),area=hex(area),area_class=rt.cls(area),byte7c=r.exact(p+0x7c,1)[0],byte7d=r.exact(p+0x7d,1)[0]))
 assert fronts==P['own_theatres'][0]['fronts']
 mp,cap,n=struct.unpack('<QII',r.exact(tp+0x198,16));assert 0<=n<=cap<=4096;assert n==5;verified=[]
 for x in P['own_theatres'][0]['dictionary_rows']:
  a,b,f=struct.unpack('<3Q',r.exact(mp+x['index']*0xc0,24));assert (hex(a),hex(b),hex(f))==(x['area'],x['enemies_area'],x['front']);r.require(f,'CFront');resolved=a
  if not a and b:
   ep=r.q(b+0x20);ec=r.i(b+0x2c);assert 0<=ec<=4096;resolved=r.q(ep) if ec else 0;assert ec==x['enemy_controller_count'];assert ep==int(x['enemy_controller_data'],16)
  assert resolved==int(x['resolved_controller_area'],16) and bool(resolved);r.require(resolved,'CControllerArea');assert (resolved==r.q(f+0x70))==x['matches_front_area'];verified.append(x)
 current=dict(pointer=hex(tp),fronts=fronts,dictionary_rows=verified);own_membership(current)
 scopes=[]
 for x in E['bundles']:
  site=int(x['named_consumer_site'],16);raw=rt.code(site,7);assert raw[:3]==b'\x48\x8d\x0d';v=site+7+struct.unpack('<i',raw[3:])[0];assert hex(v)==x['rva'];a=rt.base+v
  got=dict(named_consumer_site=hex(site),rva=hex(v),country_count=r.i(a+12),secondary_count=r.i(a+0x24),active_nesting=r.i(a+0x60),mode_byte=r.exact(a+0x64,1)[0],locked=r.exact(a+0x65,1)[0]);assert got==x;scopes.append(got)
 stable=r.stable();after=rt.guard();assert after==before
finally:rt.close()
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
assert H(inv.read_bytes())==target
seal=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,after=after,version='1.19.5.0.7c6c',country_tag='SOV',production_baseline_fields=51,production_hashes=prev['production_hashes'],native_controls=prev['native_controls'],rechecked_native_function_hashes={k:v['sha256'] for k,v in pins.items()},rechecked_native_function_count=59,prior_native_count=40,new_native_windows=19,current_own_theatre=current,named_bundle_scopes=scopes,stable_dependencies=stable,live_valid_key_samples=5,live_invalid_key_samples=0,schema_front_invalidated_positive_samples=0,schema_front_invalidated_negative_samples=0,promotions=[],counts=dict(verified=87,unverified=29,unverified_memory=17,unverified_nonmemory=12,tables=14,fields=116,columns=3),inventory_changed_rows=0,inventory_sha256=target,checkpoint_sha256=H((Q/'t233_checkpoint.md').read_bytes()),regression=reg,research_launches=6,research_successes=4,research_failures=2,initial_channel_guard_launches=1,final_seal_launches=2,final_seal_failures=1,final_seal_failure_before_Runtime=True,game_writes=0,Post=0,native_calls=0,formatter_calls=0,save_access=0,time_advance=0,pause_speed_UI_changes=0,full_capture=False,commit_push=False,generic_production_changes=False,background_tasks_started=0,next_target='Second named occupation scope33EB090 exact diplomatic relation/war-change enqueue through F6F9B0/F7BCE0/F7E1C0; not another F6A071 or empty-scope scan')
(Q/'t233_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t233 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t233 — 当前前线字典、构造断言与具名controller变更链\r\n实际PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，逐块freshguard。F6A071是F69F30构造/更新的无效key断言，非战争失效布尔量。当前己方1theatre/5front，字典5值精确匹配；3直接key、2enemy key均有效，后两first-controller不同于保留front+70，不得误判失效。具名EndBundle Conquer/Relation与NotifyControllerChanged调用链已证，但controller变化不是外交战争因果，空scope不算schema false。7D有省份成员插入共享写入，不升格。20唯一离线测试1次运行20通过；研究6启动4成功2失败源码保留；最终59原生窗口重验。清单87/29（17内存12非内存），14表116字段3列与SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变；生产51/门/指纹/四哈希未改，游戏写入/Post/调用/存档/推进/UI全0。详见records/t233_checkpoint.md、t233_final_seal.json。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t233_') or p.name.startswith('test_t233_')) and p.suffix in ('.py','.json','.md') and p.name!='t233_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m=dict(at_est=datetime.datetime.now().astimezone().isoformat(),authority=str(A),record_count=len(files)-2,new_record_count=len(selected),inventory_sha256=target,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t233_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t233_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps(dict(at_est=seal['at_est'],guard=before,native_windows=59,stable_dependencies=stable,records=m['record_count'],new_records=len(selected),checkpoint_sha256=seal['checkpoint_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=H(archive.read_bytes())),ensure_ascii=False,indent=2))
