import json,hashlib
from pathlib import Path
D=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');before=D.read_bytes();s=before.decode('utf-8');updates={'world.own_units.strength.manpower':'当前己方21师按国籍人数表合计的实际人力。','world.shortages.manpower.available':'当前玩家国家中央池与登记州可用人数之和。'};out=[];found=[]
for line in s.splitlines():
 c=[x.strip() for x in line.strip('|').split('|')]
 if c[0] in updates:
  assert c[1]=='未验证';found.append(c[0]);line='| '+c[0]+' | 已验证 | '+updates[c[0]]+' |'
 out.append(line)
assert set(found)==set(updates);s='\n'.join(out)+'\n';assert s.count(' | 已验证 | ')==36 and s.count(' | 未验证 | ')==80;assert s.count('| 字段名 | 已验证/未验证 | 说明 |')==14
for line in s.splitlines():
 if line:assert line.startswith('|') and len(line.strip('|').split('|'))==3
Path('research/t167_态势信息读取能力清单_更新前.md').write_bytes(before);D.write_bytes(s.encode('utf-8'));after=D.read_bytes();assert after.decode('utf-8')==s
Path('research/t167_态势信息读取能力清单_修订.md').write_bytes(after)
m={'target':str(D),'sha256':hashlib.sha256(after).hexdigest(),'prior_sha256':hashlib.sha256(before).hexdigest(),'utf8_readback_equal':True,'fields':116,'tables':14,'columns':3,'verified':36,'unverified':80,'new_fields':list(updates)};Path('research/t167_document_update_verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(m,ensure_ascii=False,indent=2))
