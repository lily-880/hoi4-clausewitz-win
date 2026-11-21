from pathlib import Path
import json,sys,struct,hashlib
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
p=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe');cs=Cs(CS_ARCH_X86,CS_MODE_64)
c=json.loads((R/'research/t199_full_capture.json').read_text(encoding='utf-8'));world=c['observation']['world'];errors=c['schema_validation']['errors']
print('CAPTURE',json.dumps({'units':len(world['own_units']),'plans':world.get('plans'),'combats':world.get('combats'),'incombat':[{'unit_id':u['unit_id'],'in_combat':u.get('in_combat'),'combat_id':u.get('combat_id')} for u in world['own_units'] if 'in_combat'in u],'schema_error_count':c['schema_validation']['error_count'],'errors':errors,'evidence_combat':c['evidence'].get('combats_array')},ensure_ascii=False,indent=2))
schema=json.loads((R/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'));print('DEFS',list(schema.get('$defs',{})))
for name,d in schema.get('$defs',{}).items():
 if any(k in name.lower() for k in ('combat','plan','order','time','supply')):print('SCHEMA',name,json.dumps(d,ensure_ascii=False))
# print only relevant existing research excerpts
for name in ('_t185_clip_combatant_base_0x147ff20.txt','_t188_clip_orderinstance_writer_0x10d1450.txt','_t188_clip_orderinstance_writer_tail.txt','_t185_clip_supplyconsumer_writer_0xf4c950.txt'):
 f=R/'research'/name
 if f.exists():
  lines=f.read_text(encoding='utf-8').splitlines();print('CLIP',name)
  if 'combatant_base'in name:
   for j,l in enumerate(lines):
    if 'losses'in l or '+ 0xb8]'in l:print('\n'.join(lines[max(0,j-4):j+7]))
  elif 'orderinstance'in name:
   print('\n'.join(l for l in lines if '; TOKEN'in l or '+ 0x30]'in l or '0x33d8'in l or '0x35f3'in l))
for name in ('t185_supply_consumer.json','t190_unverified_triage.json'):
 f=R/'research'/name
 if f.exists():
  d=json.loads(f.read_text(encoding='utf-8'));print('EVIDENCE',name,json.dumps(d,ensure_ascii=False)[:5500])
# basic disasm around combat getters and scalar update leads
for a,n in ((0x133e5e0,0x90),(0x134d5e0,0x20),(0x147ff20,0x240)):
 lines=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(p.read_rva(a,n),a)];(R/f'research/_t199_clip_{a:x}.txt').write_text('\n'.join(lines),encoding='utf-8')
