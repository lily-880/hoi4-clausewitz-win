# Shutdown preservation ONLY. No game/process/backend imports or access.
import json,hashlib,zipfile,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');H=lambda b:hashlib.sha256(b).hexdigest()
inv=A/'态势信息读取能力清单.md';target='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
assert H(inv.read_bytes())==target and inv.read_bytes()==(Q/'t231_inventory_before.md').read_bytes()
status=json.loads((Q/'t231_stop_status.json').read_text());assert status['state']=='STOPPED_AT_USER_SHUTDOWN_CHECKPOINT' and status['unique_semantic_tests_executed']==0 and status['promotions']==[]
assert b'## t231 ' not in (A/'README.md').read_bytes()
body='\r\n\r\n## t231 — 用户下机要求：立即保存研究检查点并停止\r\n严重度研究未完成，0升格/0语义测试；6次研究启动5份JSON、1次断言失败，不算测试。+448同值5不能推严重度；ALERT_PRIORITY接收者与既有陆军危机连接未证。slot1 RVA误抄（应1eefb08、实际用了1eafb08）两次尝试均拒绝。原始资料和更正保留。清单87/29（17内存12非内存），14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。停止后仅文档保存同步，不再读取进程，不访问游戏存档；无后台任务，不自动恢复，须用户明确继续。详见records/t231_checkpoint_STOPPED.md、t231_stop_status.json。\r\n'
with (A/'README.md').open('ab') as f:f.write(body.encode('utf-8'))
seal={'at_est':datetime.datetime.now().astimezone().isoformat(),'state':status['state'],'inventory_sha256':target,'inventory_changed_rows':0,'promotions':[],'tests_executed':0,'game_access_during_shutdown':0,'no_background_tasks_started':True,'resume_requires_explicit_continue':True,'checkpoint_sha256':H((Q/'t231_checkpoint_STOPPED.md').read_bytes()),'scope':'docs-only shutdown seal; no fresh game/process reads'}
(Q/'t231_final_STOPPED_seal.json').write_text(json.dumps(seal,indent=2)+'\n')
selected=sorted(p for p in Q.iterdir() if p.is_file() and p.name.startswith('t231_') and p.suffix in ('.py','.json','.md') and p.name!='t231_STOPPED_authority_manifest.json')
for p in selected:(A/'records'/p.name).write_bytes(p.read_bytes())
files=[A/'README.md',inv]+sorted((A/'records').glob('*'));assert all(p.is_file() for p in files)
m={'state':status['state'],'authority':str(A),'record_count':len(files)-2,'new_record_count':len(selected),'inventory_sha256':target,'entries':[{'path':p.relative_to(A).as_posix(),'size':p.stat().st_size,'sha256':H(p.read_bytes())} for p in files]}
mp=Q/'t231_STOPPED_authority_manifest.json';mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');archive=Q/'t231_stopped_checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
 for p in selected:z.write(p,'research/'+p.name)
print(json.dumps({'seal':seal,'authority_records':m['record_count'],'new_records':len(selected),'archive':str(archive),'archive_sha256':H(archive.read_bytes()),'archive_bytes':archive.stat().st_size},indent=2))
