import sys,json,struct,re
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'));sys.path.insert(0,str(R/'research'))
import _t197_setpath_zero_post as h
p=h.Proc(12948);pe=h.PE(h.EXE);s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16);cs=Cs(CS_ARCH_X86,CS_MODE_64)
# use annotated old token dict for writer clips
print('RESEARCH FILES', [f.name for f in (R/'research').glob('*') if any(x in f.name.lower() for x in ('combat_writer','combatant','landcombat','combatants'))])
out={}
for cp in h.ptr_array(p,gs+0x268,1024):
 vt=struct.unpack('<Q',p.read(cp,8))[0];slots=[struct.unpack('<Q',p.read(vt+i*8,8))[0]-p.base for i in range(8)]
 out[hex(cp)]={'vt':hex(vt-p.base),'slots':[hex(v) for v in slots]}
 for slot in (1,2):
  fn=slots[slot];off=pe.rva_to_off(fn)
  if off is None:continue
  lines=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(pe.data[off:off+0x1000],fn)]
  (R/f'research/_t198_clip_combat_slot{slot}_{fn:x}.txt').write_text('\n'.join(lines),encoding='utf-8')
  out[hex(cp)][f'slot{slot}_head']=lines[:30]
(R/'research/t198_combat_bind.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2));p.close()
# summarize prior 182 combat metadata if filenames match
for f in (R/'research').glob('t18*.json'):
 if any(x in f.name.lower() for x in ('combat','landcombat')):
  d=json.loads(f.read_text(encoding='utf-8'));print('PRIOR',f.name,json.dumps(d,ensure_ascii=False)[:2000])
