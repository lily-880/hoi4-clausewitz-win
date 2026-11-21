import sys,json,struct,hashlib,re
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,read_campaign_summary
from input_loaded_fields import LoadedReader,own_plans
p=Proc(find_pid('hoi4.exe'))
try:
 assert p.pid==12948;pe=PE(p.image_path);s=detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idle=int(s['signals']['idler_ptr'],16);co=int(resolve_player_country(p,gs)['country_ptr'],16)
 def cls(a):return _rtti_name_from_vtable(pe,struct.unpack('<Q',p.read(a,8))[0]-p.base)
 r=LoadedReader(p.read,cls);assert p.read(idle+0x6c1,1)==b'\1';clock=p.read(gs+0x468,0x24);supply=[]
 for up in r.array(co+0x290,4096):
  r.require(up,'CArmy');vt=r.q(up+0x10);col=r.q(vt-8);offset=struct.unpack('<I',r.exact(col+4,4))[0];assert offset==16 and cls(up+0x10)=='.?AVCArmy@@'and vt-p.base==0x29d6f78
  supply.append({'unit_id':r.i(up+0x1c),'secondary_rva':hex(vt-p.base),'col_offset':offset,'motorization_level':r.exact(up+0x2d,1)[0],'disrupted_supply_raw':struct.unpack('<q',r.exact(up+0xb0,8))[0]})
 plans=[]
 for th in r.array(co+0x168,64):
  for gp in r.array(th+0x80,256):
   for off in(0x98,0xb0,0xc8):
    for ip in r.array(gp+off,256):
     r.require(ip,'COrderInstance');plans.append({'id':r.i(ip+0x244),'vt':hex(r.q(ip)-p.base),'type_raw':r.i(ip+0x30),'fallback_official':r.exact(ip+0x298,1)[0],'midpoints_header':r.exact(ip+0x280,16).hex(),'executing':bool(r.exact(ip+0x248,1)[0])})
 assert all(not q['executing']for q in plans);assert clock==p.read(gs+0x468,0x24)and p.read(idle+0x6c1,1)==b'\1';checked=r.stable()
 raw=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md').read_bytes();lines=raw.decode('utf-8').splitlines();rows=[x for x in lines if re.match(r'^\| [a-z_]+\.',x)]
 out={'pid':p.pid,'pause':1,'speed_slot':struct.unpack('<I',p.read(gs+0x4bc,4))[0],'date':read_campaign_summary(p,gs).get('verified',{}).get('date_full'),'clock_unchanged':True,'supply_identity_live':supply,'plans_official_new_fields':plans,'dependent_reads_checked':checked,'gate_open':(R/'research/safe_land_tool_gate.OPEN').exists(),'new_promotions':[],'inventory':{'sha256':hashlib.sha256(raw).hexdigest(),'fields':len(rows),'tables':sum(x.startswith('| 字段名 |')for x in lines),'verified':sum('| 已验证 |'in x for x in rows),'unverified':sum('| 未验证 |'in x for x in rows)}}
 assert out['inventory']['sha256']=='4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a';assert out['speed_slot']==0
 (R/'research/t200_new_live_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
 with (R/'research/t200_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块6：针对新证据的只读活体确认与接续任务\n已只读逐21师确认+0x10处次级vt均为0x29D6F78，COL offset=16且RTTI为CArmy，独立吻合CSupplyConsumer继承和序列化证据。读取motorization/disrupted_supply仅作基类定位证据，不输出到supply三项。已只读读取4实例官方fallback+0x298和midpoints头；证据存t200_new_live_evidence.json。读前后时钟完全不变、官方暂停、全部计划执行false。\n本块未新增字段升格，清单仍14表116字段3列，72/44，32项内存候选不变；SHA4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a。34项离线回归全部通过。全段0Post、0游戏写入、0远程调用，无存档/commit/push。\n工作仍有可执行的新链，未宣称穷尽或终止：\nA. 从CArmy+0x10消费者基类进入补给分配调用者，反查读取consumer+0x20..0x98的getter、公式及UI supply标签；不要继续在错误+0x688或F47840 state dirty结构上找。可先枚举CSupplyConsumer构造器VT引用及其分配者，跟踪0xCED300基类writer的调用前this流。\nB. 从0xFC9880的UI this+0x90/+0x224分流，追该UI对象构建/更新器到真实COrderInstance，再对应fallback+0x298和ORDER_MOVE子实例轴路径。现在桥接函数尚未深查，不应泛称无样本天花板。\nC. Combat从0x1347FD0和0x1348D30的调用者追调度单位，再追constructor0x147C240的生命周期与history写入，分离duration、day和GameTime起讫。\nD. 暂停底层失效还缺失败对象payload/clone/Execute trace，现阶段仅历史数据分析；已确认的遏制bug与地址文档错误不能冒称唯一底层根因。不得为补日志解除暂停或执行指令。\n''')
finally:p.close()
