exec(open(__file__.replace('_t200_deeper.py','_t200_start.py'),encoding='utf-8').read().split('# one opening')[0])
import re
from capstone.x86 import X86_OP_MEM
cs.detail=True
out={}
for a in (0x22c4780,0x22c64f0):
 lines=clip(a);out[hex(a)]={'bounds':[hex(x)for x in fn(a)],'instructions':len(lines),'execute_sites':[x for x in lines if '[rax + 0x50]'in x or '[rax + 0x48]'in x]}
for j in range(24):
 a=struct.unpack('<Q',p.read_rva(0x29e6e10+8*j,8))[0]-0x140000000
 if 0xe50000<=a<0xe60000:
  lines=clip(a);out[f'pause_slot{j}']={'rva':hex(a),'head':lines[:10]}
# RIP-relative links to official named tooltip labels
labels={0x29f6428:'ORDER_DEFENSIVE_LINE',0x29f6510:'ORDER_PROV_TOOLTIP_FALLBACK_LINE',0x29f6560:'ORDER_OFFENSIVE_LINE'}
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
refs=[]
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',p.data):
 i=m.start();a=rv(i)
 if not a:continue
 target=a+7+struct.unpack_from('<i',p.data,i+3)[0]
 if target in labels:
  s,e=fn(a);clip(s);refs.append({'at':hex(a),'fn':hex(s),'label':labels[target]})
out['plan_tooltip_refs']=refs
# new writer identification: only memory writes to combat timer slots in combat implementation regions
writers={}
for s,e,u in fns:
 if not(0x1330000<=s<0x1350000 or 0x147c000<=s<0x1481000):continue
 hits=[]
 for i in cs.disasm(p.read_rva(s,e-s),s):
  if i.mnemonic not in('mov','inc','add','sub','and','xor','dec'):continue
  if i.operands and i.operands[0].type==X86_OP_MEM and i.operands[0].mem.disp in(0x40,0x44):hits.append(f'{i.address:x} {i.mnemonic} {i.op_str}')
 if hits:
  writers[hex(s)]=hits
  if any('0x44]'in h for h in hits):clip(s)
out['combat_timer_writer_candidates']=writers
(R/'research/t200_deeper_static.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
