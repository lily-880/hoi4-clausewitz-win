exec(open(__file__.replace('_t199_scalars.py','_t199_inspect.py'),encoding='utf-8').read().split('c=json.loads')[0])
import re
# collect named assertions not covered by earlier broad scan
ss=[]
for m in re.finditer(rb'[\x20-\x7e]{5,}',p.data):
 t=m.group().decode()
 if any(k in t for k in ('GetOrderType','IsInCombat','GetSupplyRatio','GetCurrentSupply','GetDuration','GetMovementProgress','ORDER_FRONT =','ORDER_DEFEND')):ss.append(t)
print('ADDITIONAL',json.dumps(ss,indent=2))
for name,term in (('_t182_clip_carmy_base_writer_0xc5c0a0.txt','movement_progress'),('_t185_clip_combatant_base_0x147ff20.txt','losses')):
 lines=(R/'research'/name).read_text(encoding='utf-8').splitlines()
 for j,l in enumerate(lines):
  if term in l:print('SCALAR_CLIP',term,'\n'.join(lines[max(0,j-3):j+5]))
# full movement serializer/helper is pure static disassembly, no execution
for a,n in ((0x2545f90,0x80),(0x133e5e0,0x90),(0x147eb20,0x80),(0xc0eae0,0x100)):
 lines=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(p.read_rva(a,n),a)];print('DISASM',hex(a),'\n'.join(lines));(R/f'research/_t199_clip_{a:x}.txt').write_text('\n'.join(lines),encoding='utf-8')
