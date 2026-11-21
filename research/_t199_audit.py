import sys,json,hashlib,struct,re
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable
from input_loaded_fields import LoadedReader,own_plans
from input_capture_live import capture

def guard():
 pid=find_pid('hoi4.exe');assert pid==12948
 p=Proc(pid)
 try:
  pe=PE(p.image_path);se=detect_session(p,pe);gs=int(se['signals']['gs_ptr'],16);idle=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(p,gs)['country_ptr'],16)
  def cl(a):return _rtti_name_from_vtable(pe,struct.unpack('<Q',p.read(a,8))[0]-p.base)
  r=LoadedReader(p.read,cl);plans,_=own_plans(r,co);pause=p.read(idle+0x6c1,1)[0];speed=struct.unpack('<I',p.read(gs+0x4bc,4))[0]
  assert pause==1 and speed==0 and all(not x['executing']for x in plans)
  return {'pid':pid,'pause':pause,'speed_slot':speed,'clock_hex':p.read(gs+0x468,0x24).hex(),'plans':plans}
 finally:p.close()
before=guard();a=capture();b=capture();after=guard();assert before==after,'READ-ONLY INVARIANT CHANGED';assert a['observation']==b['observation'],'DOUBLE CAPTURE DIFFERS'
(R/'research/t199_full_capture_fixed_a.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8');(R/'research/t199_full_capture_fixed_b.json').write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')
w=a['observation']['world'];assert len(w['plans'])==4 and len(w['combats'])==2;assert a['observation']['meta']['speed']=='pause';assert all(not x['executing']for x in w['plans']);assert [x['vertex_province_ids']for x in w['plans']].count([2072,7944])==2
positives={u['unit_id']:u['combat_id']for u in w['own_units']if u.get('in_combat')};assert positives=={1831:1,1832:1,1833:2,1834:2,1841:2}
assert all("is a required property"in e['message']for e in a['schema_validation']['errors'])
inv=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');raw=inv.read_bytes();lines=raw.decode('utf-8').splitlines();rows=[ln for ln in lines if re.match(r'^\| [a-z_]+\.',ln)];assert len(rows)==116 and sum(x.startswith('| 字段名 |')for x in lines)==14;assert all(len(x.split('|'))==5 for x in rows)
report={'before':before,'after':after,'double_capture_observation_equal':True,'new_reader_schema_type_or_enum_errors':[],'full_schema_valid':a['schema_validation']['valid'],'full_schema_missing_required_count':a['schema_validation']['error_count'],'units':len(w['own_units']),'provinces':len(w['provinces']),'armies':w['armies'],'army_groups':w['army_groups'],'formations':[{k:u[k]for k in ('unit_id','formation')if k in u}for u in w['own_units']if 'formation'in u],'own_combat_positives':positives,'inventory':{'sha256':hashlib.sha256(raw).hexdigest(),'fields':116,'tables':14,'columns':3,'verified':sum('| 已验证 |'in x for x in rows),'unverified':sum('| 未验证 |'in x for x in rows),'bom':raw.startswith(b'\xef\xbb\xbf')},'gate_open':(R/'research/safe_land_tool_gate.OPEN').exists(),'game_writes':0,'post_calls':0,'remote_calls':0,'new_promotions':['world.shortages.equipment.affected_unit_ids']}
(R/'research/t199_e2e_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

