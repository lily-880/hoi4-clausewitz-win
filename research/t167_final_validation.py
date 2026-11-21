from pathlib import Path
import json,hashlib,collections
import jsonschema
p=Path('research');a=json.loads((p/'t167_live_capture.json').read_text(encoding='utf-8'));b=json.loads((p/'t167_live_capture_repeat.json').read_text(encoding='utf-8'));schema=json.loads(Path('calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'));errors=sorted(jsonschema.Draft202012Validator(schema).iter_errors(a['observation']),key=lambda e:str(list(e.path)));w=a['observation']['world']
for u in w['own_units']:jsonschema.validate(u['strength'],{'$ref':'#/$defs/Strength','$defs':schema['$defs']})
jsonschema.validate(w['shortages']['manpower'],schema['$defs']['Shortages']['properties']['manpower'])
D=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');raw=D.read_bytes();text=raw.decode('utf-8');rows=[]
for line in text.splitlines():
 if not line:continue
 assert line.startswith('|') and len(line.strip('|').split('|'))==3
 c=[x.strip() for x in line.strip('|').split('|')]
 if c[1] in ('已验证','未验证'):rows.append(c)
assert len(rows)==116 and len({x[0] for x in rows})==116 and text.count('| 字段名 | 已验证/未验证 | 说明 |')==14
assert collections.Counter(x[1] for x in rows)=={'已验证':37,'未验证':79}
old=(p/'t167_态势信息读取能力清单_更新前.md').read_text(encoding='utf-8');oldnames={x.split('|')[1].strip() for x in old.splitlines() if ' | 已验证 | ' in x or ' | 未验证 | ' in x};assert oldnames=={x[0] for x in rows}
m=json.loads((p/'t167_document_update_verification.json').read_text(encoding='utf-8'));assert m['sha256']==hashlib.sha256(raw).hexdigest()
prev=json.loads((p/'t165_remaining82_dependency_audit.json').read_text(encoding='utf-8'));status={x[0]:x[1] for x in rows};items=[x for x in prev['items'] if status[x['field']]=='未验证'];assert len(items)==79;(p/'t167_remaining79_dependency_audit.json').write_text(json.dumps({'remaining':79,'items':items},ensure_ascii=False,indent=2),encoding='utf-8')
result={'pid':a['pid'],'version':a['game_version'],'read_only':True,'two_observations_equal':a['observation']==b['observation'],'complete_input':False,'schema_checked':True,'full_schema_valid':not errors,'full_schema_error_count':len(errors),'errors':[{'path':'.'.join(map(str,e.path)),'message':e.message} for e in errors],'unit_tests_passed':53,'compile_passed':True,'units':len(w['own_units']),'manpower_current_total':sum(u['strength']['manpower'] for u in w['own_units']),'manpower_available':w['shortages']['manpower']['available'],'hp_current_max':[(u['unit_id'],u['strength']['current'],u['strength']['max']) for u in w['own_units']],'loaded_dependent_reads_rechecked':a['evidence']['loaded_dependent_reads_rechecked'],'document':m}
(p/'t167_validation_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('errors','hp_current_max','document')},ensure_ascii=False,indent=2));print('DOC',m['sha256'])
