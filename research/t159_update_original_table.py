from pathlib import Path
import json,hashlib,re
from datetime import datetime,timezone,timedelta
root=Path.cwd();target=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');source=root/'research/态势信息读取能力清单_1.19.5修订.md'
original_bytes=target.read_bytes();original=original_bytes.decode('utf-8-sig');new_source=source.read_text(encoding='utf-8-sig')
def cells(line):return [x.strip().strip('`') for x in line.split('|')[1:-1]]
def norm(field):return field.replace('[]','')
new={}
for line in new_source.splitlines():
 if line.startswith('|'):
  c=cells(line)
  if len(c)==3 and c[1] in ('已验证','未验证'):new[norm(c[0])]=(c[1],c[2])
blocks=[];section=None;current=[]
for line in original.splitlines():
 if line.startswith('## '):
  if section is not None:blocks.append((section,current))
  section=line[3:].strip();current=[]
 elif line.startswith('|'):
  c=cells(line)
  if len(c)==3 and c[1] in ('已验证','未验证'):current.append(c)
if section is not None:blocks.append((section,current))
assert len(blocks)==14
assert sum(len(rows) for _,rows in blocks)==116
explicit={
 'meta.player_country.index':('已验证','当前玩家控制国家的引擎序号。'),
 'meta.player_country.tag':('未验证','玩家国家的三字母代号，当前版本未独立核验。'),
 'world.own_units.owner.index':('已验证','当前己方师所属国家的引擎序号。'),
 'world.own_units.owner.tag':('未验证','师所属国家的三字母代号，当前版本未独立核验。'),
 'world.own_units.relation_to_player':('已验证','仅已验证与玩家同国的self关系。'),
 'world.own_units.template.template_id':('已验证','当前21个己方师所用四种模板的内部编号。'),
 'world.own_units.template.battalions':('已验证','当前四种己方模板内非空主战营的类型和数量。'),
 'world.own_units.strength.manpower':('未验证','师当前人力，尚未与满编人力区分。'),
 'world.provinces.province_id':('已验证','当前己方师所在省份的编号。'),
 'world.provinces.terrain':('已验证','当前己方师所在12省的引擎地形名称。'),
 'world.provinces.controller':('已验证','当前己方登记区域的占领国编号，未验省份易手。'),
 'world.provinces.owner':('已验证','当前己方登记区域的法理归属国编号，未验归属变化。'),
 'world.visible_units':('未验证','战争迷雾下玩家实际可见的其他陆部队。'),
}
for part,desc in [('year','年份'),('month','月份'),('day','日'),('hour','小时')]:explicit['meta.game_time.'+part]=('已验证','游戏内当前'+desc+'。')
rendered=[];changes=[];result_rows=[]
for section,rows in blocks:
 lines=['| 字段名 | 已验证/未验证 | 说明 |','| --- | --- | --- |']
 for field,old_status,old_desc in rows:
  full=section+'.'+field
  if section=='world.visible_units' and field=='visible_units':full=section
  key=norm(full)
  status,desc=explicit.get(key,new.get(key,('未验证',old_desc)))
  assert status in ('已验证','未验证') and '|' not in desc and '\n' not in desc
  if status!=old_status or desc!=old_desc:changes.append({'field':full,'old_status':old_status,'status':status,'description':desc})
  lines.append('| '+full+' | '+status+' | '+desc+' |');result_rows.append((full,status,desc))
 rendered.append('\n'.join(lines))
updated='\n\n'.join(rendered)+'\n'
assert len(result_rows)==116 and len({r[0] for r in result_rows})==116
for line in updated.splitlines():
 if not line.strip():continue
 assert line.startswith('|') and line.endswith('|') and len(cells(line))==3
assert updated.count('| 字段名 | 已验证/未验证 | 说明 |')==14
assert dict((f,s) for f,s,d in result_rows)['world.own_units.strength.manpower']=='未验证'
for f in ('meta.allow_write','meta.geography_scope','policy.stance','policy.instructions'):
 assert dict((k,s) for k,s,d in result_rows)[f]=='未验证'
backup=root/'research/t159_态势信息读取能力清单_更新前.md';backup.write_bytes(original_bytes)
target.write_text(updated,encoding='utf-8',newline='\n')
readback=target.read_bytes();decoded=readback.decode('utf-8',errors='strict')
assert decoded==updated
sha=hashlib.sha256(readback).hexdigest()
manifest={'updated_at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5),'EST')).isoformat(),'target':str(target),'basis':str(source),'backup':str(backup),'tables':14,'columns':['字段名','已验证/未验证','说明'],'field_rows':116,'verified_rows':sum(s=='已验证' for f,s,d in result_rows),'utf8_readback_matches':True,'only_tables':True,'sha256':sha,'previous_sha256':hashlib.sha256(original_bytes).hexdigest(),'changes':changes}
(root/'research/t159_document_update_verification.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k!='changes'},ensure_ascii=False,indent=2))
print('STATUS_CHANGES',json.dumps([c for c in changes if c['old_status']!=c['status']],ensure_ascii=False,indent=2))
