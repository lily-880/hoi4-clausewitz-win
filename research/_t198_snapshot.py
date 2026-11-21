import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
import _t197_setpath_zero_post as h
import _t196_scaffold_and_validate as old
p=h.Proc(12948);pe=h.PE(h.EXE);s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16)
assert p.read(idler+0x6c1,1)==b'\1'
out={'date':(h.read_campaign_summary(p,gs).get('verified')or{}).get('date_full'),'pause':1,'units':[],'combats':[]}
for up in h.ptr_array(p,co+0x290,4096):
 d=old.snap_unit(p,pe,up);d['progress_u32']=struct.unpack('<I',p.read(up+0x240,4))[0];out['units'].append(d)
for cp in h.ptr_array(p,gs+0x268,1024):out['combats'].append({'ptr':hex(cp),'class':h.cls(p,pe,cp),'head':p.read(cp,0x100).hex()})
out['combat_array']=list(h.pdx(p,gs+0x268));out['allow_post']=h.allow_post();p.close()
(R/'research/t198_current_snapshot.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('LIVE',json.dumps({'date':out['date'],'pause':1,'units_nonempty':[d for d in out['units'] if d['path'] or d['full_path'] or d['commandlist_size']],'unit1829':out['units'][0],'combats':out['combats'],'combat_array':out['combat_array']},indent=2))
for name in ('t182_carmy_writers.json','t183_live_assigned_to.json','t185_land_combatant_activity.json','t188_plan_writers.json'):
 pp=R/'research'/name
 if pp.exists():
  dd=json.loads(pp.read_text(encoding='utf-8'));print('META',name,json.dumps(dd,ensure_ascii=False)[:1800])
src=(R/'calling/input_loaded_fields.py').read_text(encoding='utf-8');print('READER DEFS', [x for x in src.splitlines() if x.startswith('def ') and any(k in x.lower() for k in ('combat','supply','order','manpower','hp'))])
