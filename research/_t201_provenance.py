from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
import re
from capstone.x86_const import X86_OP_REG,X86_OP_MEM,X86_REG_RIP
cs.detail=True
out={'isolation_helpers':{},'GS_actual_array_refs':[],'template_reason_callers':[]}
for a in(0xc47c40,0xc47880,0xc402a0):out['isolation_helpers'][hex(a)]=clip(a)
text=next(s for s in p.sections if s.name=='.text');seen=set();pos=text.raw_ptr
# Straight-line provenance is a candidate filter, not an execution proof.
while True:
 pos=p.data.find(struct.pack('<I',0x268),pos+1)
 if pos<0 or pos>=text.raw_ptr+text.raw_size:break
 st,en=fn(text.virtual_address+pos-text.raw_ptr)
 if st in seen:continue
 seen.add(st);ls=list(cs.disasm(p.read_rva(st,en-st),st));taint={};events=[]
 def rn(reg):
  name=cs.reg_name(reg) or ""
  if name in('eax','ecx','edx','ebx','esi','edi','esp','ebp'):return 'r'+name[1:]
  return re.sub(r'^(r\d+)[dwb]$',r'\1',name)
 for i in ls:
  ops=i.operands;new=None;dest=None
  if ops and ops[0].type==X86_OP_REG:dest=rn(ops[0].reg)
  if i.mnemonic=='mov'and len(ops)>1 and ops[1].type==X86_OP_REG:new=taint.get(rn(ops[1].reg))
  if len(ops)>1 and ops[1].type==X86_OP_MEM and i.mnemonic in('mov','lea'):
   m=ops[1].mem;tag=taint.get(rn(m.base))
   if i.mnemonic=='mov'and m.base==X86_REG_RIP and i.address+i.size+m.disp==0x33dd6b0:new='GS'
   elif tag=='GS'and m.disp==0x268:
    events.append(i.address);new='combat_array_header'if i.mnemonic=='lea'else'combat_array_data'
   elif tag=='GS'and m.disp==0 and i.mnemonic=='lea':new='GS'
  try:written=i.regs_access()[1]
  except Exception:written=[]
  for r in written:taint.pop(rn(r),None)
  if dest and new:taint[dest]=new
  if i.mnemonic=='call':
   for r in('rax','rcx','rdx','r8','r9','r10','r11'):taint.pop(r,None)
 if events:
  out['GS_actual_array_refs'].append({'fn':hex(st),'contexts':[[f'{j.address:x} {j.mnemonic} {j.op_str}'for j in ls if e-35<=j.address<=e+160]for e in events]})
# New direct callers of the reason formatter identify the code-producing predicate.
for m in re.finditer(rb'[\xe8\xe9]',p.data[text.raw_ptr:text.raw_ptr+text.raw_size]):
 off=text.raw_ptr+m.start();a=text.virtual_address+m.start()
 if off+5>len(p.data):continue
 if a+5+struct.unpack_from('<i',p.data,off+1)[0]!=0x1739900:continue
 st,en=fn(a);ls=clip(a);out['template_reason_callers'].append({'at':hex(a),'fn':hex(st),'context':[s for s in ls if a-130<=int(s.split()[0],16)<=a+50]})
(R/'research/t201_precise_provenance.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('HELPERS',json.dumps(out['isolation_helpers'],indent=2));print('EXACT_GS_ARRAY_FUNCTIONS',[x['fn']for x in out['GS_actual_array_refs']]);print('TEMPLATE_REASON_CALLERS',json.dumps(out['template_reason_callers'],indent=2))
with(R/'research/t201_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块4：计划UI桥接、50项回归通过与隔离新入口\nFD2DC0中FD4682调用12DF090返回r15实例；FD4742对其+298 fallback分支为真时UI+224=1；否则FD4760按实例+30==1选择UI0，不等于1选UI2（r14已清零）；另+119特殊标志走UI4。FC9880已知UI0/1/2分别defensive/fallback/offensive。当前type2+fallback0不能称frontline；当前fallback1在schema无枚举，不能强塞frontline。继续校验12DF090→C402A0实例身份及特殊+119边界，仍不升格计划type。\n剩余新链：CHANGE_TEMPLATE_DISABLED_ENCIRCLED位于1739900的原因码4分支；HQ_WITHDRAWAL/DEPLOYMENT_BLOCKED_ENCIRCLED的真实判断调用分别C47C40/C47880，已开始拆函数，而非把out-of-supply直接等同isolated。\n50项离线回归全部通过（新增16项；第一次仅UTF-8导出被Windows默认GBK解码，测试明确指定UTF-8后通过；无需重采样）。完整capture依旧50项required缺失，complete_input=false，未冒称全合同完成。\n宽GS+268/虚槽扫描含大量其他对象+268甚至call/stack偏移碰撞，不能作为调度者证据；已改为显式GS全局来源的寄存器传播筛选，结果只作后续候选。\n''')
