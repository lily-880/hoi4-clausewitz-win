exec(open(__file__.replace('_t200_unit_accessors.py','_t200_start.py'),encoding='utf-8').read().split('# one opening')[0])
from capstone.x86 import X86_OP_MEM,X86_REG_RCX
cs.detail=True
out=[]
for s,e,u in fns:
 if not 0xc50000<=s<0xc5c000 or e-s>224:continue
 ins=list(cs.disasm(p.read_rva(s,e-s),s));rr=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in ins if any(o.type==X86_OP_MEM and o.mem.base==X86_REG_RCX and 0x20<=o.mem.disp<=0xa0 for o in i.operands)]
 if rr:
  txt=clip(s);out.append({'fn':hex(s),'size':e-s,'fields':rr,'fixed_100000':any('0x186a0'in x for x in txt),'asm':txt if len(txt)<=18 else txt[:6]})
(R/'research/t200_unit_consumer_accessor_candidates.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
