# Research-only final fresh read binding, independent hashes, one-row C-document seal.
import sys,json,hashlib,struct,datetime,zipfile
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from t227_qualified_crisis_replay import supply
H=lambda b:hashlib.sha256(b).hexdigest();A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');R=Q.parent
inventory=A/'态势信息读取能力清单.md';baseline='8c51a0318d5d72dc3b0d2a67325462c16c42629abffddb1438f18b774e636740';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
assert H(inventory.read_bytes())==baseline;proposed=(Q/'t228_inventory_proposed.md').read_bytes();assert H(proposed)==target
prev=json.loads((Q/'t227_final_seal.json').read_text(encoding='utf-8'));prod=prev['production_hashes']
for name,h in prod.items():assert H((R/name).read_bytes())==h
rt=Runtime()
try:
 before=rt.guard();assert before['pid']==10288 and before['base']=='0x7ff758fc0000' and before['country_index']==3 and before['pause']==1 and before['speed_slot']==0 and before['hour_tick']==60781105 and not any(before['markers'].values())
 version=rt.code(0x2795083,48).split(b'\0')[0].decode();assert version=='1.19.5.0.7c6c'
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';native={}
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:native[hex(va)]=H(rt.code(va,n));assert native[hex(va)]==prev['native_controls'][hex(va)]
 checked={};oldpins=json.loads((Q/'t227_native_code_pins.json').read_text())
 for fn,pins in oldpins.items():
  d=json.loads((Q/fn).read_text(encoding='utf-8'))
  for va,h in pins.items():assert H(rt.code(int(va,16),d['functions'][va]['window_size']))==h;checked[va]=h
 chain=json.loads((Q/'t228_native_text_chain.json').read_text());pins=json.loads((Q/'t228_native_text_pins.json').read_text())
 for va,h in pins.items():assert H(rt.code(int(va,16),chain['functions'][va]['window_size']))==h;checked[va]=h
 for va,key in [(0x29c5118,b'LOW_SUPPLIES_TIPS'),(0x29c4210,b'ALERT_RIGHTCLICK')]:assert rt.code(va,len(key)+1)==key+b'\0'
 # All heap entrances below are rebound from this Runtime, not frozen pointers.
 tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup');og=r.array(tg+0x48,128)[0];r.require(og,'COrdersGroup');members=r.array(og+0x50,256);assert len(members)==25
 sq=lambda a:struct.unpack('<q',r.exact(a,8))[0]
 hours=r.i(rt.base+0x33e3678);threshold=sq(rt.base+0x33e3e00);assert (hours,threshold)==(72,99000);controls=[]
 for member in members[:3]:
  u=member-0xb8;r.require(u,'CArmy');assert r.i(u+0x18)==51 and r.i(u+0x1e0)==3 and r.q(u+0xc0)==og
  assert r.q(r.q(member)+0x20)==rt.base+0xc4f050 and r.q(r.q(u)+0x40)==rt.base+0x20f350
  pp=r.q(u+0x1f0);r.require(pp,'CProvince');pid=r.i(u+0x28);assert r.i(pp+0xa4)==pid
  source=sq(u+0x40);effective,out,bucket=supply(source,sq(u+0x600),sq(u+0x610),hours,threshold,bool(r.q(u+0x2f8)))
  controls.append(dict(unit_id=r.i(u+0x1c),province_id=pid,source_raw=source,effective_raw=effective,out_of_supply=out,native_bucket=bucket))
 by={x['unit_id']:x for x in controls};assert set(by)=={500,374,479};assert (by[479]['province_id'],by[479]['source_raw'],by[479]['effective_raw'],by[479]['out_of_supply'],by[479]['native_bucket'])==(1780,11335,11335,True,0);assert (by[374]['source_raw'],by[374]['effective_raw'],by[374]['out_of_supply'],by[374]['native_bucket'])==(100000,100000,False,2)
 manager=r.q(rt.idler+0x7a8);active={};note_raw=None
 for aid,name in [(3,'alert_low_supply'),(4,'alert_very_low_supply')]:
  assert r.string(manager+aid*0x468+0x410)==name
  ptr,cap,n=struct.unpack('<QII',r.exact(manager+(aid+0xf0e)*24,16));assert 0<=n<=cap<=32;keys=[]
  for j in range(n):
   ep=ptr+j*0x468;k=struct.unpack('<QQQQ',r.exact(ep+0x438,32));assert r.string(ep+0x410)==name;keys.append((k[0],k[1],k[3]))
   if aid==4 and (k[0],k[1],k[3])==(0,tg,0):
    assert note_raw is None;b=r.exact(ep+0x28,32);length,c=struct.unpack_from('<QQ',b,16);assert 0<length<=4096 and length<=c<=1048576;note_raw=b[:length] if c<=15 else r.exact(struct.unpack_from('<Q',b)[0],length)
  active[str(aid)]=keys
 assert (0,tg,0) in active['4'] and (0,tg,0) not in active['3'];assert note_raw is not None and len(note_raw)==672 and H(note_raw)=='baea0542d50eaec437826773d8070fcd6a1a7c653a7bd0c6b846b5b4c8f44fba'
 proof=json.loads((Q/'t228_notes_semantic_proof.json').read_text(encoding='utf-8'));assert note_raw.decode('utf-8')==proof['replay']['qualified_fields']['notes'];stable=r.stable();after=rt.guard();assert before==after
finally:rt.close()
reg=json.loads((Q/'t228_regression_results.json').read_text());assert reg['successful'] and reg['unique_methods']==30 and reg['total_invocations']==30 and reg['completed_suite_runs']==1 and reg['collection_failures']==1
old=inventory.read_bytes();assert old==(Q/'t228_inventory_before.md').read_bytes();aa=old.splitlines(keepends=True);bb=proposed.splitlines(keepends=True);assert len(aa)==len(bb) and sum(a!=b for a,b in zip(aa,bb))==1
s=proposed.decode('utf-8');assert s.count('| 字段名 | 已验证/未验证 | 说明 |')==14 and s.count('| 已验证 |')==87 and s.count('| 未验证 |')==29
inventory.write_bytes(proposed)
body='\r\n\r\n## t228 — 已缓存原文说明与独立范围一致性\r\nB61660独立_delayed注册/存储、B79D00具名补充文本写入及B52A30/B525A0复制链，证明当前同源战区组警报4的672字节已缓存中文补充原文；非53字节模板或22字节标题，未调用格式化/本地化函数或替换键和占位符。仅升格crises.notes；原换行和0x11格式码保留。范围复核仅重绑原3/25成员，479因果见证、374健康阴性与500中间对照均不变；说明是战区组通用建议，不是每师诊断，海路建议仍为条件句。kind仍为组合注解，非原生枚举，无severity/完整危机记录/feed/Input。30唯一方法（25专项范围+5共享）通过；2次启动但首次导入依赖失败执行0测试，只有1轮完整套件/30调用，Windows0、旧套件0。清单87/29（17内存+12非内存未证），14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3。生产51/指纹门及四哈希不变，游戏零写入/调用/推进。详见records/t228_checkpoint.md/t228_final_seal.json。下一候选combats.result的独立胜负消费者与精确历史战斗编号连接，不重做已闭合日期换算。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
seal={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'version':version,'country_tag':'SOV','native_controls':native,'rechecked_native_function_count':len(checked),'rechecked_native_function_hashes':checked,'controls':controls,'sampled_members':3,'native_member_count':25,'new_units_inspected':0,'active_alert_keys':active,'note_byte_length':len(note_raw),'note_raw_sha256':H(note_raw),'scope':'same native group cached advisory, not witness-specific diagnosis or full affected-unit census','stable_dependencies':stable,'inventory_sha256':H(proposed),'counts':{'tables':14,'fields':116,'columns':3,'verified':87,'unverified':29,'unverified_memory':17,'unverified_nonmemory':12},'production_hashes':prod,'production_baseline_fields':51,'fingerprint_gates_unchanged':True,'game_writes':0,'post':0,'native_calls':0,'formatter_calls':0,'save_access':0,'time_advance':0,'pause_speed_changes':0,'full_capture':False,'commit_push':False,'windows_test_replay':0,'regression':reg,'checkpoint_sha256':H((Q/'t228_checkpoint.md').read_bytes()),'inventory_changed_rows':1}
(Q/'t228_final_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
selected=sorted(p for p in Q.iterdir() if (p.name.startswith('t228_') or p.name.startswith('test_t228_')) and p.suffix in ('.json','.py','.md') and p.name!='t228_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inventory]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
manifest={'at_est':datetime.datetime.now().astimezone().isoformat(),'authority':str(A),'record_count':len(files)-2,'inventory_sha256':H(proposed),'entries':[{'path':p.relative_to(A).as_posix(),'size':p.stat().st_size,'sha256':H(p.read_bytes())} for p in files]}
mp=Q/'t228_authority_manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t228_final_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,'t228_authority_manifest.json')
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps({'seal_at_est':seal['at_est'],'guard':before,'counts':seal['counts'],'inventory_sha256':H(proposed),'checkpoint_sha256':seal['checkpoint_sha256'],'native_functions_rechecked':len(checked),'stable_dependencies':stable,'note_raw_sha256':H(note_raw),'authority_records':manifest['record_count'],'new_research_records':len(selected),'archive':str(archive),'archive_sha256':H(archive.read_bytes()),'archive_bytes':archive.stat().st_size},ensure_ascii=False,indent=2))
