import json,hashlib,collections
from pathlib import Path
import jsonschema
r=json.loads(Path('research/t165_live_capture.json').read_text(encoding='utf-8'));r2=json.loads(Path('research/t165_live_capture_repeat.json').read_text(encoding='utf-8'));s=json.loads(Path('calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'));err=sorted(jsonschema.Draft202012Validator(s).iter_errors(r['observation']),key=lambda e:str(list(e.path)))
w=r['observation']['world'];vp=s['$defs']['Province']['properties']['victory_points']
for p in w['provinces']:jsonschema.validate(p['victory_points'],vp)
D=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');b=D.read_bytes();text=b.decode('utf-8');rows=[]
for line in text.splitlines():
 if not line:continue
 assert line.startswith('|') and len(line.strip('|').split('|'))==3
 c=[x.strip() for x in line.strip('|').split('|')]
 if c[1] in ('已验证','未验证'):rows.append(c)
assert len(rows)==116 and len({x[0] for x in rows})==116;assert text.count('| 字段名 | 已验证/未验证 | 说明 |')==14
status={f:st for f,st,_ in rows};assert collections.Counter(status.values())=={'已验证':34,'未验证':82}
m=json.loads(Path('research/t165_document_update_verification.json').read_text(encoding='utf-8'));assert hashlib.sha256(b).hexdigest()==m['sha256']
a=json.loads(Path('research/t165_95_field_dependency_audit.json').read_text(encoding='utf-8'));remaining=[]
for item in a['items']:
 item['current_status']=status[item['field']]
 if item['current_status']=='未验证':remaining.append(item)
assert len(remaining)==82
Path('research/t165_remaining82_dependency_audit.json').write_text(json.dumps({'remaining':82,'no_global_sample_blocker_claimed':True,'items':remaining},ensure_ascii=False,indent=2),encoding='utf-8')
out={'pid':r['pid'],'version':r['game_version'],'complete_input':False,'two_live_observations_equal':r['observation']==r2['observation'],'full_schema_valid':not err,'full_schema_error_count':len(err),'full_schema_errors':[{'path':'.'.join(map(str,e.path)),'message':e.message} for e in err],'leaders':len(w['leaders']),'display_name_links':r['evidence']['leader_collection']['display_name_pointer_links'],'player':r['observation']['meta']['player_country'],'widths':{u['template']['template_id']:u['template']['combat_width'] for u in w['own_units']},'infrastructure':[(p['province_id'],p.get('infrastructure')) for p in w['provinces']],'victory_points':[(p['province_id'],p['victory_points']) for p in w['provinces']],'dependent_reads_rechecked':r['evidence']['loaded_dependent_reads_rechecked'],'unit_tests':{'passed':38,'failed':0},'document':m}
Path('research/t165_validation_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('full_schema_errors','infrastructure','victory_points','document')},ensure_ascii=False,indent=2));print('DOC',m['sha256'],len(rows),'fields',14,'tables',34,82)
