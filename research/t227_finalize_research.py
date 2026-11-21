# t227 research-only fresh final binding and C-authority seal; no game writes/calls.
import sys,json,hashlib,struct,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from t227_qualified_crisis_replay import supply
H=lambda b:hashlib.sha256(b).hexdigest()
A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');R=Q.parent;inventory=A/'态势信息读取能力清单.md'
assert H(inventory.read_bytes())=='ebd57b52a517d88e51e39b10f3c3b529e2ce2b542e9fde5ebd9f9d2cb1871ae5'
proposed=(Q/'t227_inventory_proposed.md').read_bytes();assert H(proposed)=='8c51a0318d5d72dc3b0d2a67325462c16c42629abffddb1438f18b774e636740'
prod={'calling/input_capture_live.py':'e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37','calling/input_loaded_fields.py':'1aecf151e7f221fa2f1a6b86b37a9d15bf2a44d0f7f649f552b2af8f808e65b5','calling/tables/generalissimo_input.schema.json':'9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee','calling/input_observation.py':'27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6'}
for name,h in prod.items():assert H((R/name).read_bytes())==h,name
rt=Runtime()
try:
 before=rt.guard();assert before['pid']==10288 and before['base']=='0x7ff758fc0000' and before['country_index']==3 and before['pause']==1 and before['speed_slot']==0 and before['hour_tick']==60781105 and not any(before['markers'].values())
 version=rt.code(0x2795083,48).split(b'\0')[0].decode();assert version=='1.19.5.0.7c6c'
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';native={}
 for va,n,h in [(0x147c330,2048,'d47cee77d6354b55c8409394903552842feb1b9034e84a6b99cc88ee9bb735e6'),(0xcec2e0,4096,'f421f2fca4a1bbcc7156a96fc752dfa7b8298bc006ca3c5488470faffd0369d3')]:
  native[hex(va)]=H(rt.code(va,n));assert native[hex(va)]==h
 pins=json.loads((Q/'t227_native_code_pins.json').read_text());checked={}
 for filename,funcs in pins.items():
  ds=json.loads((Q/filename).read_text())
  for va,h in funcs.items():
   f=ds['functions'][va];assert H(rt.code(int(va,16),f['window_size']))==h;checked[va]=h
 tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup')
 og=r.array(tg+0x48,128)[0];r.require(og,'COrdersGroup');members=r.array(og+0x50,256);assert len(members)==25
 hours=r.i(rt.base+0x33e3678);threshold=struct.unpack('<q',r.exact(rt.base+0x33e3e00,8))[0];assert (hours,threshold)==(72,99000);controls=[]
 for mp in members[:3]:
  u=mp-0xb8;r.require(u,'CArmy');assert r.q(r.q(mp)+0x20)==rt.base+0xc4f050 and r.q(r.q(u)+0x40)==rt.base+0x20f350
  assert r.i(u+0x18)==51 and r.i(u+0x1e0)==3 and r.q(u+0xc0)==og
  uid=r.i(u+0x1c);pp=r.q(u+0x1f0);r.require(pp,'CProvince');pid=r.i(u+0x28);assert r.i(pp+0xa4)==pid
  sq=lambda a:struct.unpack('<q',r.exact(a,8))[0]
  src=sq(u+0x40);eff,out,bucket=supply(src,sq(u+0x600),sq(u+0x610),hours,threshold,bool(r.q(u+0x2f8)))
  controls.append(dict(unit_id=uid,province_id=pid,source=src,effective=eff,out_of_supply=out,bucket=bucket))
 by={x['unit_id']:x for x in controls};assert set(by)=={500,374,479}
 assert (by[479]['province_id'],by[479]['source'],by[479]['effective'],by[479]['out_of_supply'],by[479]['bucket'])==(1780,11335,11335,True,0)
 assert (by[374]['source'],by[374]['effective'],by[374]['out_of_supply'],by[374]['bucket'])==(100000,100000,False,2)
 manager=r.q(rt.idler+0x7a8);names={3:'alert_low_supply',4:'alert_very_low_supply',5:'alert_base_low_supply',6:'alert_base_very_low_supply'}
 for aid,name in names.items():assert r.string(manager+aid*0x468+0x410)==name
 active={}
 for aid in (3,4):
  ptr,cap,n=struct.unpack('<QII',r.exact(manager+(aid+0xf0e)*24,16));assert 0<=n<=cap<=128;keys=[]
  for j in range(n):
   ep=ptr+j*0x468;key=struct.unpack('<QQQQ',r.exact(ep+0x438,32));assert r.string(ep+0x410)==names[aid];keys.append((key[0],key[1],key[3]))
  active[str(aid)]=keys
 assert (0,tg,0) in active['4'] and (0,tg,0) not in active['3'];stable=r.stable();after=rt.guard();assert before==after
finally:rt.close()
rows=[x for x in proposed.decode('utf-8').splitlines() if x.startswith('| ') and x.count('|')==4]
assert sum('| 已验证 |' in x for x in rows)==86 and sum('| 未验证 |' in x for x in rows)==30
assert proposed.decode('utf-8').count('| 字段名 | 已验证/未验证 | 说明 |')==14
old=inventory.read_bytes();assert old==(Q/'t227_inventory_before.md').read_bytes();a=old.splitlines(keepends=True);b=proposed.splitlines(keepends=True);assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==3
reg=json.loads((Q/'t227_regression_results.json').read_text());assert reg['successful'] and reg['unique_test_methods']==32 and reg['total_invocations_including_failed_run']==64
inventory.write_bytes(proposed)
body='\r\n\r\n## t227 — 海空基地警报与陆军补给因果见证\r\nB58150实际映射海空基地警报5/6而非陆军3/4。独立B79D00链及当前CTheaterGroup缓存警报4，与479师缺补给阳性/374师阴性形成双重证据；仅升格crises.kind/unit_ids/province_ids三个窄见证字段，kind明确为组合schema注解而非原生Crisis枚举，不输出severity/notes或完整危机/Input。只查3/25成员，500中间对照不作bucket0见证。32唯一离线方法（27专项范围+5共享），两轮64调用，首轮10错误来自研究断言B79E64误写，按真实B79E65修正后末轮32全过；0Windows复放。清单86/30（18内存+12非内存未证），14表116字段3列，SHA8c51a0318d5d72dc3b0d2a67325462c16c42629abffddb1438f18b774e636740。生产51/指纹门及四哈希不变，游戏零写入/调用/推进。详见records/t227_checkpoint.md/t227_final_seal.json。下一目标已缓存alert4文本的crises.notes独立消费者；键/占位符不算notes，不推断严重度。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
seal={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'version':version,'country_tag':'SOV','native_controls':native,'rechecked_native_function_count':len(checked),'rechecked_native_function_hashes':checked,'controls':controls,'active_alert_keys':active,'stable_dependencies':stable,'inventory_sha256':H(proposed),'counts':{'tables':14,'fields':116,'columns':3,'verified':86,'unverified':30,'unverified_memory':18,'unverified_nonmemory':12},'production_hashes':prod,'production_baseline_fields':51,'fingerprint_gates_unchanged':True,'game_writes':0,'post':0,'native_calls':0,'save_access':0,'time_advance':0,'pause_speed_changes':0,'full_capture':False,'commit_push':False,'windows_test_replay':0,'regression':reg,'checkpoint_sha256':H((Q/'t227_checkpoint.md').read_bytes()),'inventory_changed_rows':3}
(Q/'t227_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
selected=sorted(p for p in Q.iterdir() if (p.name.startswith('t227_') or p.name.startswith('test_t227_')) and p.suffix in ('.json','.py','.md') and p.name!='t227_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inventory]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
manifest={'at_est':datetime.datetime.now().astimezone().isoformat(),'authority':str(A),'record_count':len(files)-2,'inventory_sha256':H(proposed),'entries':[{'path':p.relative_to(A).as_posix(),'size':p.stat().st_size,'sha256':H(p.read_bytes())} for p in files]}
mp=Q/'t227_authority_manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t227_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,'t227_authority_manifest.json')
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps({'seal_at_est':seal['at_est'],'guard':before,'counts':seal['counts'],'inventory_sha256':H(proposed),'checkpoint_sha256':seal['checkpoint_sha256'],'authority_records':manifest['record_count'],'archive':str(archive),'archive_sha256':H(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'new_research_records':len(selected)},ensure_ascii=False,indent=2))
