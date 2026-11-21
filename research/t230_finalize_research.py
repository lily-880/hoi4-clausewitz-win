# Machine-specific read-only final binding + authorized research/document seal. No game mutations.
import sys,json,hashlib,struct,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');R=Q.parent
inventory=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
assert inventory.read_bytes()==(Q/'t230_inventory_before.md').read_bytes() and H(inventory.read_bytes())==target
prev=json.loads((Q/'t229_final_seal.json').read_text(encoding='utf-8'));prod=prev['production_hashes']
for name,h in prod.items():assert H((R/name).read_bytes())==h
reg=json.loads((Q/'t230_regression_results.json').read_text())
assert reg['successful'] and reg['unique_methods']==30 and reg['total_invocations']==30 and reg['suite_runs']==2 and reg['final_failures']==reg['final_errors']==0
assert json.loads((Q/'t230_regression_attempt1.json').read_text())['collection_failures']==1
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
 fs={}
 for name in ['t229_winner_semantics_and_ally_pivot.json','t229_named_pivot_closure.json']:fs.update(json.loads((Q/name).read_text(encoding='utf-8'))['functions'])
 fs['0x178f070']=json.loads((Q/'t229_history_winner_probe.json').read_text())['ui_function']
 for va,h in json.loads((Q/'t229_accepted_native_pins.json').read_text()).items():
  assert H(rt.code(int(va,16),fs[va]['window_size']))==h;checked[va]=h
 assert checked==prev['rechecked_native_function_hashes']
 t230fns=json.loads((Q/'t230_named_desired_and_front_roots.json').read_text())['functions']
 t230fns.update(json.loads((Q/'t230_own_front_correction_and_serializer.json').read_text())['functions'])
 newpins=json.loads((Q/'t230_accepted_native_pins.json').read_text())
 for va,h in newpins.items():assert H(rt.code(int(va,16),t230fns[va]['window_size']))==h;checked[va]=h
 assert len(newpins)==4
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 theatres=r.array(rt.country+0x168,64);assert len(theatres)==1
 tp=theatres[0];r.require(tp,'CTheatre')
 fronts=r.array(tp+0x50,4096);rows=[]
 for p in fronts:
  r.q(p);assert rt.cls(p)=='.?AVCFront@@'
  kind,ident=struct.unpack('<II',r.exact(p+0x8,8));back=r.q(p+0x18)
  assert kind==66 and back==tp
  rows.append(dict(front=hex(p),id=ident,kind=kind,theatre_back=hex(back)))
 assert [x['id'] for x in rows]==[1278,76,70,1734,1735]
 # confirm the desired and REQ_DIVS strings are still at the pinned RVAs; no function call
 assert rt.code(0x2860350,len(b'_TotalFrontDesiredNrDivisions'))==b'_TotalFrontDesiredNrDivisions'
 assert rt.code(0x2a69a98,8)==b'REQ_DIVS'
 assert rt.code(0x2a69a80,len(b'garrison_order_headline'))==b'garrison_order_headline'
 stable=r.stable();after=rt.guard();assert before==after
finally:
 rt.close()
for name,h in prod.items():assert H((R/name).read_bytes())==h
old=inventory.read_bytes();assert old==(Q/'t230_inventory_before.md').read_bytes() and H(old)==target
s=old.decode('utf-8');assert s.count('| 字段名 | 已验证/未验证 | 说明 |')==14 and s.count('| 已验证 |')==87 and s.count('| 未验证 |')==29
seal={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'version':version,'country_tag':'SOV','native_controls':native,'rechecked_native_function_count':len(checked),'prior_native_function_count':len(prev['rechecked_native_function_hashes']),'current_native_proof_windows':4,'rechecked_native_function_hashes':checked,'fresh_own_fronts':rows,'official_country_theatre_count':1,'missing_divisions_promoted':False,'desired_named':'_TotalFrontDesiredNrDivisions','req_divs_scope':'garrison_order_ui_partial','stable_dependencies':stable,'inventory_sha256':target,'counts':{'tables':14,'fields':116,'columns':3,'verified':87,'unverified':29,'unverified_memory':17,'unverified_nonmemory':12},'production_hashes':prod,'production_baseline_fields':51,'fingerprint_gates_unchanged':True,'game_writes':0,'post':0,'native_calls':0,'formatter_calls':0,'save_access':0,'time_advance':0,'pause_speed_changes':0,'UI_changes':0,'full_capture':False,'commit_push':False,'generic_production_changes':False,'windows_test_replay':0,'old_suites':0,'regression':reg,'checkpoint_sha256':H((Q/'t230_checkpoint.md').read_bytes()),'inventory_changed_rows':0,'promotions':[],'crisis_scope':'unchanged prior 3/25 members witness only; group cached notes; composed kind; no severity/fullCrisis/feed/Input','next_target':'world.crises.severity independently named severity consumer on the already-qualified crisis/alert witness; no 3/4 or threshold inference and no census expansion'}
(Q/'t230_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
body='\r\n\r\n## t230 — 己方战线成员已证，missing_divisions不升格\r\n独立具名_TotalFrontDesiredNrDivisions是期望兵力，不是缺编。REQ_DIVS与garrison_order_headline/GARRISON_ORDER_CONF同窗，属驻防命令所需师标签，且因间接跳转0x177d3fa保持PARTIAL；所需不是缺口。官方国家theatre数组仅1项，其+0x50上5个CFront（1278、76、70、1734、1735）的+0x18均回指该theatre，为当前己方战线成员。相邻stride 0x1e0的CTheatre+0x50（3/73/3/8）不是己方成员。无具名缺编消费者，不以期望、驻防所需或所需减现有作为官方字段。30唯一测试/2次启动；首次导入因非ASCII字节字面量失败执行0测试，修正后30/30通过，总调用30，Windows0旧套件0。清单保持87/29（17内存12非内存），14表116字段3列及SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3；生产51/指纹门/四哈希不变，游戏写入调用推进UI变化均0。详见records/t230_checkpoint.md及t230_final_seal.json。下一候选crises.severity，须在既有警报/危机见证上找独立具名严重度消费者，不以警报3/4或阈值名称推断，不扩大3/25或notes/feed范围。\r\n'
assert b'## t230 ' not in (A/'README.md').read_bytes()
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if (p.name.startswith('t230_') or p.name.startswith('test_t230_')) and p.suffix in ('.json','.py','.md') and p.name!='t230_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inventory]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
manifest={'at_est':datetime.datetime.now().astimezone().isoformat(),'authority':str(A),'record_count':len(files)-2,'new_research_record_count':len(selected),'inventory_sha256':target,'entries':[{'path':p.relative_to(A).as_posix(),'size':p.stat().st_size,'sha256':H(p.read_bytes())} for p in files]}
mp=Q/'t230_authority_manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t230_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,'t230_authority_manifest.json')
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps({'seal_at_est':seal['at_est'],'guard':before,'counts':seal['counts'],'inventory_sha256':target,'checkpoint_sha256':seal['checkpoint_sha256'],'native_functions_rechecked':len(checked),'stable_dependencies':stable,'own_fronts':rows,'authority_records':manifest['record_count'],'new_research_records':len(selected),'archive':str(archive),'archive_sha256':H(archive.read_bytes()),'archive_bytes':archive.stat().st_size},ensure_ascii=False,indent=2))
