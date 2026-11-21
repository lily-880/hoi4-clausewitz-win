from pathlib import Path
import json,hashlib
p=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');b=p.read_bytes();s=b.decode('utf-8');fields=['meta.player_country.tag','world.own_units.owner.tag','world.provinces.victory_points']
for f in fields:s=s.replace('| '+f+' | 未验证 |','| '+f+' | 已验证 |')
s=s.replace('玩家国家的三字母代号，当前版本未独立核验。','当前运行时国家表中玩家国家的三字母代号。').replace('师所属国家的三字母代号，当前版本未独立核验。','当前己方师所属国家在运行时国家表中的代号。').replace('该省胜利点分值与名称。','当前己方师所在12省的胜利点分值及已有重命名。')
assert s.count(' | 已验证 | ')==34 and s.count(' | 未验证 | ')==82
Path('research/t165_清单_新增tagVP前.md').write_bytes(b);p.write_bytes(s.encode('utf-8'));back=p.read_bytes();assert back.decode('utf-8')==s
q=Path('research/t165_document_update_verification.json');m=json.loads(q.read_text(encoding='utf-8'));m.update(verified=34,unverified=82,sha256=hashlib.sha256(back).hexdigest());m['newly_verified_fields']+=fields;q.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');print(m['sha256'])
