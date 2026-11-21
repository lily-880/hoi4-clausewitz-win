import sys,json,hashlib,re,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'));sys.path.insert(0,str(R/'research'))
import _t197_setpath_zero_post as h
from input_loaded_fields import LoadedReader,own_active_combats,own_unit_current_combat,own_plans,unit_current_manpower,unit_hp
p=h.Proc(12948);pe=h.PE(h.EXE);s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16);r=LoadedReader(p.read,lambda a:h.cls(p,pe,a))
out={'pause':p.read(idler+0x6c1,1)[0],'plans':own_plans(r,co),'combats':own_active_combats(r,gs,co),'units':[]};assert out['pause']==1
for up in r.array(co+0x290,4096):
 uid=r.i(up+0x1c)
 if uid in (1829,1831,1832,1833,1834,1841):out['units'].append({'id':uid,'combat':own_unit_current_combat(r,gs,co,uid),'manpower':unit_current_manpower(r,up),'hp':unit_hp(r,up)})
for cp in r.array(gs+0x268,4096):
 for off in (0x28,0x30):
  bp=r.q(cp+off);print('LOSSES RAW',hex(bp),p.read(bp+0xb8,0x20).hex())
inv=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');raw=inv.read_bytes();lines=raw.decode('utf-8').splitlines();rows=[ln for ln in lines if re.match(r'^\| [a-z_]+\.',ln)];out['inventory']={'sha256':hashlib.sha256(raw).hexdigest(),'fields':len(rows),'verified':sum('| 已验证 |'in ln for ln in rows),'unverified':sum('| 未验证 |'in ln for ln in rows),'tables':sum(ln.startswith('| 字段名 |')for ln in lines)}
assert out['inventory']['fields']==116 and out['inventory']['tables']==14
out['remaining']=[ln.split('|')[1].strip() for ln in rows if '| 未验证 |'in ln];out['allow_post']=h.allow_post();out['gate_open']=(R/'research/safe_land_tool_gate.OPEN').exists();p.close();(R/'research/t198_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
