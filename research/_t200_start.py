import sys,struct,json,hashlib,bisect
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
p=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe');cs=Cs(CS_ARCH_X86,CS_MODE_64)
pd=next(s for s in p.sections if s.name=='.pdata');fns=list(struct.iter_unpack('<III',p.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size//12*12]));starts=[x[0]for x in fns]
def fn(a):
 j=bisect.bisect_right(starts,a)-1
 return fns[j][:2]if j>=0 and fns[j][0]<=a<fns[j][1]else(a,a+64)
def clip(a):
 a,e=fn(a);lines=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in cs.disasm(p.read_rva(a,e-a),a)];(R/f'research/_t200_clip_{a:x}.txt').write_text('\n'.join(lines),encoding='utf-8');return lines
# one opening read-only health guard
from mem import Proc,find_pid
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,read_campaign_summary
from input_loaded_fields import LoadedReader,own_plans
pr=Proc(find_pid('hoi4.exe'))
try:
 assert pr.pid==12948;se=detect_session(pr,p);gs=int(se['signals']['gs_ptr'],16);idle=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(pr,gs)['country_ptr'],16)
 rr=LoadedReader(pr.read,lambda a:_rtti_name_from_vtable(p,struct.unpack('<Q',pr.read(a,8))[0]-pr.base));plans,_=own_plans(rr,co);assert pr.read(idle+0x6c1,1)==b'\1'and all(not x['executing']for x in plans)
 status={'pid':pr.pid,'pause':1,'speed_slot':struct.unpack('<I',pr.read(gs+0x4bc,4))[0],'date':read_campaign_summary(pr,gs).get('verified',{}).get('date_full'),'all_plans_stopped':True,'gate_open':(R/'research/safe_land_tool_gate.OPEN').exists()}
 (R/'research/t200_initial_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8');print('STATUS',status)
finally:pr.close()
inv=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');raw=inv.read_bytes();lines=raw.decode('utf-8').splitlines();unv=[x.split('|')[1].strip()for x in lines if '| 未验证 |'in x];memory=[x for x in unv if x.startswith('world.')];assert len(memory)==32
buckets={}
for name in memory:
 key='supply'if'.supply.'in name else 'march_order'if'.order.'in name else 'visibility'if name.startswith('world.visible_units')else name.split('.')[1]
 buckets.setdefault(key,[]).append(name)
tri={'inventory_sha256':hashlib.sha256(raw).hexdigest(),'unverified_memory_count':32,'groups':buckets};(R/'research/t200_candidate_triage.json').write_text(json.dumps(tri,ensure_ascii=False,indent=2),encoding='utf-8');print('GROUPS',buckets)
# CPauseGame factory, clone, post queue, sink/drain/update loops
vt=0x29e6e10;clone=struct.unpack('<Q',p.read_rva(vt+0x68,8))[0]-0x140000000
for a in (0xe53a00,clone,0x22c4250,0x23f5d40,0x23f6550,0x22c4710):
 text=clip(a);print('STATIC',hex(a),'instructions',len(text),'\n'.join(text[:70]))
(R/'research/t200_checkpoint.md').write_text('''# t200 checkpoint（持续严格只读）\n\n授权pt184u继续静态/只读工作；禁止Post/游戏内存写入/远程函数调用/解除暂停/存档/commit/push。开段pid12948，官方暂停，速度槽0，全部已读计划executing=false，闸门关闭。\n\n块1：已将32项剩余内存候选按supply/march_order/visibility/plans/combats/crises/wars/shortages分组落盘t200_candidate_triage.json。优先走此前未拆解的CPauseGame Clone→队列sink/drain→执行回执链、Combat时间字段写入者、计划type2下的fallback标志及tooltip分流，而非重复空快照。\n''',encoding='utf-8')
