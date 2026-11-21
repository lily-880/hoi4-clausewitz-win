import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable
from input_loaded_fields import LoadedReader,_typed_equipment_amounts
p=Proc(find_pid('hoi4.exe'))
try:
 assert p.pid==12948;pe=PE(p.image_path);se=detect_session(p,pe);gs=int(se['signals']['gs_ptr'],16);idle=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(p,gs)['country_ptr'],16);assert p.read(idle+0x6c1,1)==b'\1';clock=p.read(gs+0x468,0x24)
 def cls(a):return _rtti_name_from_vtable(pe,struct.unpack('<Q',p.read(a,8))[0]-p.base)
 r=LoadedReader(p.read,cls);rows=[];affected={};unresolved=[]
 for up in r.array(co+0x290,4096):
  r.require(up,'CArmy');uid=r.i(up+0x1c);tp=r.q(up+0x3b8);r.require(tp,'CReferencedDivisionTemplate')
  need=_typed_equipment_amounts(r,tp+0x120,'CEquipmentArcheTypePool',16,8);current=_typed_equipment_amounts(r,up+0x348,'CEquipmentVariantPool',24,16);cmap={x['equipment_type']:x['amount_raw']for x in current};d={}
  for x in need:
   name=x['equipment_type']
   if name not in cmap:unresolved.append({'unit_id':uid,'type':name,'reason':'absent current bucket: do not assume zero without getter'});continue
   delta=x['amount_raw']-cmap[name];d[name]={'need_raw':x['amount_raw'],'current_raw':cmap[name],'deficit_raw':max(0,delta)}
   if delta>0:affected.setdefault(name,[]).append(uid)
  rows.append({'unit_id':uid,'typed_comparison':d})
 stable=r.stable();assert p.read(gs+0x468,0x24)==clock and p.read(idle+0x6c1,1)==b'\1'
 out={'pid':p.pid,'pause':1,'units_checked':len(rows),'rows':rows,'affected_unit_ids_by_type':affected,'unresolved':unresolved,'dependent_reads_rechecked':stable,'scope':'physical per-type template need versus current fielded stock, not national demanded or request queue','human_casualty_inference':False}
 (R/'research/t199_equipment_affected_live.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:p.close()
