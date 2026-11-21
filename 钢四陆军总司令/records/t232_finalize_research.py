# Fresh read-only verification + authorized machine-specific documentation seal only.
import sys,json,struct,hashlib,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from t227_qualified_crisis_replay import supply
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');inv=A/'态势信息读取能力清单.md'
session=json.loads((Q/'t232_initial_session_rebind.json').read_text());prev=json.loads((Q/'t230_final_seal.json').read_text());target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
assert H(inv.read_bytes())==target and inv.read_bytes()==(Q/'t232_inventory_before.md').read_bytes()
reg=json.loads((Q/'t232_regression_results.json').read_text());assert reg['successful'] and reg['unique_methods']==reg['total_test_invocations']==24 and reg['completed_suite_runs']==reg['suite_starts']==1
assert reg['failures']==reg['errors']==reg['collection_failures']==0
for name,h in session['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
# Gather prior code-window sizes only. No frozen heap addresses become targets.
fs={}
for fn,pins in json.loads((Q/'t227_native_code_pins.json').read_text()).items():
 d=json.loads((Q/fn).read_text(encoding='utf-8'))
 for va in pins:fs[va]=d['functions'][va]
for fn in ('t228_native_text_chain.json','t229_winner_semantics_and_ally_pivot.json','t229_named_pivot_closure.json','t230_named_desired_and_front_roots.json','t230_own_front_correction_and_serializer.json'):
 fs.update(json.loads((Q/fn).read_text(encoding='utf-8'))['functions'])
fs['0x178f070']=json.loads((Q/'t229_history_winner_probe.json').read_text())['ui_function']
domain=json.loads((Q/'t232_correct_priority_domain.json').read_text());fs.update(domain['functions']);fs['0x145e1c0']=domain['candidate_functions']['0x145e1c0'];fs['0x253ecd0']=json.loads((Q/'t232_live_token_names.json').read_text())['getter_flow']
newpins=json.loads((Q/'t232_accepted_native_pins.json').read_text());pins=dict(prev['rechecked_native_function_hashes']);pins.update({k:v['sha256'] for k,v in newpins.items()});assert len(pins)==40
rt=Runtime()
try:
 before=rt.guard();assert before==session['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==session['native_controls'][hex(va)]
 checked={}
 for va,h in pins.items():assert H(rt.code(int(va,16),fs[va]['window_size']))==h;checked[va]=h
 # Revalidate actual corrected secondary table after ASLR; parser class metadata independent.
 col,m0,m1=struct.unpack('<3Q',rt.code(0x2affbe0,24));sig,off,cd,td,chd,selfrva=struct.unpack('<6I',rt.pr.read(col,24))
 assert sig==1 and off==0x18 and rt.base+selfrva==col and (m0-rt.base,m1-rt.base)==(0x1eeff60,0x1eefb08)
 assert rt.code(td+16,160).split(b'\0')[0]==b'.?AVCNavyTheaterGroupItem@@'
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup');og=r.array(tg+0x48,128)[0];r.require(og,'COrdersGroup');members=r.array(og+0x50,256);assert len(members)==25
 sq=lambda a:struct.unpack('<q',r.exact(a,8))[0]
 hours=r.i(rt.base+0x33e3678);threshold=sq(rt.base+0x33e3e00);assert (hours,threshold)==(72,99000);controls=[]
 for member in members[:3]:
  u=member-0xb8;r.require(u,'CArmy');assert r.i(u+0x18)==51 and r.i(u+0x1e0)==3 and r.q(u+0xc0)==og
  pp=r.q(u+0x1f0);r.require(pp,'CProvince');pid=r.i(u+0x28);assert r.i(pp+0xa4)==pid
  source=sq(u+0x40);effective,out,bucket=supply(source,sq(u+0x600),sq(u+0x610),hours,threshold,bool(r.q(u+0x2f8)))
  controls.append(dict(unit_id=r.i(u+0x1c),province_id=pid,source_raw=source,effective_raw=effective,out_of_supply=out,native_bucket=bucket))
 assert controls==json.loads((Q/'t232_alert_level_domain.json').read_text())['controls']
 manager=r.q(rt.idler+0x7a8);keys={};master={}
 for aid,name in [(3,'alert_low_supply'),(4,'alert_very_low_supply')]:
  assert r.string(manager+aid*0x468+0x410)==name;master[str(aid)]=r.i(manager+aid*0x468+0x448)
  p,c,n=struct.unpack('<QII',r.exact(manager+(aid+0xf0e)*24,16));assert 0<=n<=c<=32;rows=[]
  for j in range(n):
   ep=p+j*0x468;k=struct.unpack('<4Q',r.exact(ep+0x438,32));assert r.string(ep+0x410)==name and r.i(ep+0x448)==5;rows.append((k[0],k[1],k[3]))
  keys[str(aid)]=rows
 assert master=={'3':5,'4':5} and (0,tg,0) in keys['4'] and (0,tg,0) not in keys['3']
 assert r.exact(rt.base+0x368f570,1)==b'\x01';tc=r.i(rt.base+0x368f574);assert 19369<tc<100000;table=r.q(rt.base+0x368f5a0);tn={}
 for token,name in [(19364,'alert_level'),(19365,'low'),(19366,'medium'),(19367,'high'),(19369,'alert_margin')]:assert r.string(table+token*32)==name;tn[str(token)]=name
 stable=r.stable();after=rt.guard();assert before==after
finally:rt.close()
for name,h in session['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
assert H(inv.read_bytes())==target
seal={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'version':'1.19.5.0.7c6c','country_tag':'SOV','production_hashes':session['production_hashes'],'native_controls':session['native_controls'],'rechecked_native_function_hashes':checked,'rechecked_native_function_count':len(checked),'prior_native_count':36,'new_native_windows':4,'current_token_names':tn,'current_token_count':tc,'live_controls':controls,'sampled_members':3,'native_members':25,'new_units_inspected':0,'active_alert_keys':keys,'master448':master,'notes_payload_reads':0,'schema_severity_samples':0,'promotions':[],'inventory_changed_rows':0,'inventory_sha256':target,'counts':{'verified':87,'unverified':29,'unverified_memory':17,'unverified_nonmemory':12,'tables':14,'fields':116,'columns':3},'production_baseline_fields':51,'fingerprint_gates_unchanged':True,'stable_dependencies':stable,'regression':reg,'final_rebind_launches':1,'game_writes':0,'Post':0,'native_calls':0,'formatter_calls':0,'save_access':0,'time_advance':0,'pause_speed_UI_changes':0,'full_capture':False,'commit_push':False,'generic_production_changes':False,'background_tasks_started':0,'checkpoint_sha256':H((Q/'t232_checkpoint.md').read_bytes()),'next_target':'world.wars.front_invalidated: exact F6A071 dictionary validator/caller reason; no invalidation inference from diagnostics/load errors or console rebuild command'}
(Q/'t232_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert b'## t232 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t232 — 明确继续后绑定重启会话，严重度域隔离\r\npt207u恢复授权。实际PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，两门关闭，版本/生产四哈希/原生指纹一致；未复用旧10288堆址。修正真实第二槽1EEFB08为CNavyTheaterGroupItem副接口adjustor，确认navy UI priority而非陆军危机。新增alert_level解析器145E1C0属于COccupationModifier，当前原生token表独立证low/medium/high->配置+C8=0/1/2，非watch/high/critical，解析器整体仍PARTIAL。只重绑既有3/25见证，active4同组存在；0新成员/0notes原文读取/0严重度样本/0升格。24唯一测试一次收集一次运行24通过；研究collector另有1次无pdata断言失败，原源码保留，不算测试。另转front_invalidated具名字典检查F6A071入口，日志/loader错误不是战争导致失效证据。清单87/29（17内存12非内存），14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。生产51/门/四哈希不变，游戏写入/Post/原生调用/存档/推进/UI变化全0。详见records/t232_checkpoint.md、t232_final_seal.json。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
selected=sorted(p for p in Q.iterdir() if p.is_file() and (p.name.startswith('t232_') or p.name.startswith('test_t232_')) and p.suffix in ('.py','.json','.md') and p.name!='t232_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m={'at_est':datetime.datetime.now().astimezone().isoformat(),'authority':str(A),'record_count':len(files)-2,'new_record_count':len(selected),'inventory_sha256':target,'entries':[{'path':p.relative_to(A).as_posix(),'size':p.stat().st_size,'sha256':H(p.read_bytes())} for p in files]}
mp=Q/'t232_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t232_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps({'at_est':seal['at_est'],'guard':before,'counts':seal['counts'],'native_windows_rechecked':len(checked),'stable_dependencies':stable,'authority_records':m['record_count'],'new_records':len(selected),'inventory_sha256':target,'checkpoint_sha256':seal['checkpoint_sha256'],'archive':str(archive),'archive_sha256':H(archive.read_bytes()),'archive_bytes':archive.stat().st_size},ensure_ascii=False,indent=2))
