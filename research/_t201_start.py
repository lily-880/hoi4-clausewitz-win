import sys,json,struct,hashlib,bisect,re
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from mem import Proc,find_pid
from gamestate import detect_session,resolve_player_country,_rtti_name_from_vtable,read_campaign_summary
from input_loaded_fields import LoadedReader,own_plans
profile=json.loads((R/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8'))
pr=Proc(find_pid('hoi4.exe'))
try:
 exe=pr.image_path;assert hashlib.sha256(Path(exe).read_bytes()).hexdigest().upper()==profile['exe_sha256'].upper();p=PE(exe);se=detect_session(pr,p);assert se['in_game'];gs=int(se['signals']['gs_ptr'],16);idle=int(se['signals']['idler_ptr'],16);co=int(resolve_player_country(pr,gs)['country_ptr'],16)
 rr=LoadedReader(pr.read,lambda a:_rtti_name_from_vtable(p,struct.unpack('<Q',pr.read(a,8))[0]-pr.base));plans,_=own_plans(rr,co);assert pr.read(idle+0x6c1,1)==b'\1'and all(not x['executing']for x in plans)
 status={'pid':pr.pid,'base':hex(pr.base),'pause':1,'speed_slot':struct.unpack('<I',pr.read(gs+0x4bc,4))[0],'date':read_campaign_summary(pr,gs).get('verified',{}).get('date_full'),'plan_ids':[x['plan_id']for x in plans],'all_plans_stopped':True,'gate_open':(R/'research/safe_land_tool_gate.OPEN').exists()};assert status['speed_slot']==0
 (R/'research/t201_initial_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8');print('STATUS',status)
finally:pr.close()
cs=Cs(CS_ARCH_X86,CS_MODE_64);pd=next(s for s in p.sections if s.name=='.pdata');fns=list(struct.iter_unpack('<III',p.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size//12*12]));starts=[x[0]for x in fns]
def fn(a):
 j=bisect.bisect_right(starts,a)-1;return fns[j][:2]if j>=0 and fns[j][0]<=a<fns[j][1]else(a,a+64)
def clip(a):
 a,e=fn(a);ls=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in cs.disasm(p.read_rva(a,e-a),a)];(R/f'research/_t201_clip_{a:x}.txt').write_text('\n'.join(ls),encoding='utf-8');return ls
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
# direct caller chains newly prioritized this block
out={'direct_callers':{},'consumer_vtable_refs':[],'ui_supply_labels':[],'ui_supply_refs':[]}
targets={0xfc9880,0x1347fd0,0x1348d30,0x147c240,0xf4ca30}
for m in re.finditer(rb'[\xe8\xe9]',p.data):
 i=m.start();a=rv(i)
 if a is None or i+5>len(p.data):continue
 dest=a+5+struct.unpack_from('<i',p.data,i+1)[0]
 if dest in targets:
  fs,fe=fn(a)
  if fs<=a<fe and fs<0x2700000:
   out['direct_callers'].setdefault(hex(dest),[]).append({'at':hex(a),'fn':hex(fs),'opcode':hex(p.data[i])});clip(fs)
# choose precise UI labels, not lua define errors or RTTI
labels={}
for m in re.finditer(rb'[A-Z][A-Z0-9_]{4,100}\x00',p.data):
 a=rv(m.start());t=m.group()[:-1].decode()
 if a and 0x29c0000<a<0x2b50000 and any(k in t for k in('SUPPLY_STATUS','SUPPLY_LEVEL','OUT_OF_SUPPLY','SUPPLY_REMAIN','SUPPLY_CONSUM','SUPPLY_DEMAND','SUPPLY_FULFILL','SUPPLY_USE','SUPPLY_ISOLAT','SUPPLY_RATIO')):
  labels[a]=t
out['ui_supply_labels']=[{'rva':hex(k),'text':v}for k,v in labels.items()]
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',p.data):
 i=m.start();a=rv(i)
 if a is None:continue
 dest=a+7+struct.unpack_from('<i',p.data,i+3)[0]
 if dest==0x29cfa58:
  fs,fe=fn(a);out['consumer_vtable_refs'].append({'at':hex(a),'fn':hex(fs)});clip(fs)
 if dest in labels:
  fs,fe=fn(a);out['ui_supply_refs'].append({'at':hex(a),'fn':hex(fs),'label':labels[dest]});clip(fs)
(R/'research/t201_new_call_chains.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
(R/'research/t201_checkpoint.md').write_text('''# t201 checkpoint（持续严格只读）\n\n已加载code-changes，按本机活体依赖例外。开段重新发现PID、映像base、GS/player/idler并核对exe SHA，不沿用堆指针。官方暂停、speed0、全部已读计划executing=false，闸门关闭。0Post/0游戏写入/0远程调用，无存档/commit/push。\n块1新链：CSupplyConsumer vtable构造引用、具体UI supply标签调用者、FC9880直接调用者、Combat两计数更新及基构造的直接调用者已新建xref证据。后续沿这些根函数拆解，非重复短访问器扫描。\n''',encoding='utf-8')
