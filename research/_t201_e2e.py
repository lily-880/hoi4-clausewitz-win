import sys,json,struct,hashlib
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,read_campaign_summary
from input_loaded_fields import LoadedReader,own_plans
from input_capture_live import capture

def state():
 pr=Proc(find_pid('hoi4.exe'))
 try:
  assert pr.pid==12948;pe=PE(pr.image_path);se=detect_session(pr,pe);gs=int(se['signals']['gs_ptr'],16);idler=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(pr,gs)['country_ptr'],16);r=LoadedReader(pr.read,lambda a:_rtti_name_from_vtable(pe,struct.unpack('<Q',pr.read(a,8))[0]-pr.base));plans,_=own_plans(r,co)
  d={'pid':pr.pid,'base':hex(pr.base),'pause':pr.read(idler+0x6c1,1)[0],'speed_slot':struct.unpack('<I',pr.read(gs+0x4bc,4))[0],'date':read_campaign_summary(pr,gs)['fields']['date_full'],'plans':[{'id':x['plan_id'],'executing':x['executing']}for x in plans]};assert d['pause']==1 and d['speed_slot']==0 and all(not x['executing']for x in plans);return d
 finally:pr.close()
before=state();captures=[]
for label in('a','b'):
 d=capture();captures.append(d);(R/f'research/t201_full_capture_{label}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
after=state();assert before==after and captures[0]['observation']==captures[1]['observation'];a=captures[0];units=a['observation']['world']['own_units'];out={'before':before,'after':after,'observation_equal':True,'counts':{'units':len(units),'normal_supply':sum(x['supply']['in_supply']for x in units),'out_of_supply':sum(not x['supply']['in_supply']for x in units),'provinces':len(a['observation']['world']['provinces']),'armies':len(a['observation']['world']['armies']),'army_groups':len(a['observation']['world']['army_groups']),'plans':len(a['observation']['world']['plans']),'combats':len(a['observation']['world']['combats'])},'schema_errors':a['schema_validation']['error_count'],'complete_input':a['complete_input'],'post_calls':0,'remote_calls':0,'game_writes':0,'gate_open':(R/'research/safe_land_tool_gate.OPEN').exists(),'capture_sha256':{label:hashlib.sha256((R/f'research/t201_full_capture_{label}.json').read_bytes()).hexdigest()for label in('a','b')},'inventory_current_readback':'blocked by local-exec root; last confirmed 72/44 4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a; no D write attempted','new_proofs_pending_inventory':['world.own_units.supply.ratio','world.own_units.supply.in_supply']};assert not out['gate_open'];(R/'research/t201_e2e_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
with(R/'research/t201_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块3：真实非默认补给正反样本与完整capture\n新只读读取21师官方UI公式各输入；buffer参数72、阈值99000。9师不足（1831-1835/1840/1841/1847/1848），12师正常。实际source比例约0.61279-0.61285或0.91240；保留储备后有效比例0.89105-0.89107或0.97536，不能把Army+40直当最终ratio。已添加有边界/溢出拒绝和依赖复读的unit_supply并接入完整capture。两个端到端导出observation完全相同，21师均输出ratio/in_supply，isolated仍省略。官方暂停与游戏日期/全部计划执行状态读前后完全相同。\n两项已有新活体正反证据，本地记录为证实待清单同步。但D盘目标的Read和专用CopyToBox均被allowed local-exec root拒绝，未改用Shell绕过，未写D盘，也不能声称新SHA读回。最后确认清单仍72/44、SHA4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a；两项状态同步后应为74/42，非已写入事实。\nCombat静态vtable归属已确证1489550是CLandBorderWarCombat槽78，而普通CLandCombat槽78=1347FD0、槽80=1348D30。边境战+E8开始时间不能移植普通陆战。\n离线保存t198原始源码及SHA；修正提前清除unpaused风险，只有官方pause1才能清除；异常路径不重用已Post对象，不再含自动重试执行器。历史脚本首行硬阻止执行。只编译/AST与纯函数回归，未执行历史脚本，未活体复现。并未找全预制暂停底层失败根因。\n''')
