import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,read_campaign_summary
from input_loaded_fields import LoadedReader,own_plans
pr=Proc(find_pid('hoi4.exe'))
try:
 assert pr.pid==12948;pe=PE(pr.image_path);se=detect_session(pr,pe);gs=int(se['signals']['gs_ptr'],16);idle=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(pr,gs)['country_ptr'],16)
 rr=LoadedReader(pr.read,lambda a:_rtti_name_from_vtable(pe,struct.unpack('<Q',pr.read(a,8))[0]-pr.base));assert pr.read(idle+0x6c1,1)==b'\1';clock=pr.read(gs+0x468,0x24)
 q=lambda at:struct.unpack('<q',rr.exact(at,8))[0]
 buffer_hours=rr.i(pr.base+0x33e3678);threshold=q(pr.base+0x33e3e00);units=[]
 for up in rr.array(co+0x290,4096):
  rr.require(up,'CArmy');source=q(up+0x40);need=q(up+0x600);reserve=q(up+0x610);special=rr.q(up+0x2f8);bf=reserve//buffer_hours if buffer_hours else None;ratio=None if bf is None else max(0,min(100000,max(source,bf)))if need>0 else 0
  units.append({'id':rr.i(up+0x1c),'consumer_factor_30_raw':source,'army_600_raw':need,'army_610_raw':reserve,'special_2f8_present':bool(special),'ui_ratio_candidate_raw':ratio,'ui_out_of_supply_candidate':False if special else ratio<threshold if ratio is not None else None})
 plans,_=own_plans(rr,co);assert all(not x['executing']for x in plans);assert clock==pr.read(gs+0x468,0x24)and pr.read(idle+0x6c1,1)==b'\1';rr.stable()
 out={'pid':pr.pid,'base':hex(pr.base),'pause':1,'clock_unchanged':True,'buffer_denominator_rva':'0x33e3678','buffer_parameter_raw':buffer_hours,'out_of_supply_threshold_rva':'0x33e3e00','threshold_raw':threshold,'units':units,'note':'New actual inputs to identified official UI arithmetic; still candidate output, no remote getter call and no inventory promotion.'};(R/'research/t201_supply_ui_live_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:pr.close()
