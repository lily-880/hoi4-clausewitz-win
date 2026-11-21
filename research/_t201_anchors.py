from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
import re
cs.detail=False
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
wanted={'ARMY_UNIT_SUPPLY','ARMY_UNIT_SUPPLY_DESC_BAD','ARMY_UNIT_SUPPLY_DESC_OK','SUPPLY_DIVISION_DEMAND'};entries=json.loads((R/'research/t201_supply_ui_names.json').read_text());targets={rv(x['offset']):x['text']for x in entries if x['text']in wanted};out={'supply_ui_refs':[]}
# demand label not in previous filter: find exact raw name
for t in wanted:
 b=t.encode()+b'\0';pos=p.data.find(b)
 if pos>=0:targets[rv(pos)]=t
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',p.data):
 j=m.start();a=rv(j)
 if a is None:continue
 dest=a+7+struct.unpack_from('<i',p.data,j+3)[0]
 if dest not in targets:continue
 ls=clip(a);rec={'at':hex(a),'fn':hex(fn(a)[0]),'label':targets[dest],'excerpt':[l for l in ls if a-200<=int(l.split()[0],16)<=a+100]};out['supply_ui_refs'].append(rec)
# Static callable hour accessor and historical combat scalar check, not a process call.
out['57a7a0']=clip(0x57a7a0)
snap=json.loads((R/'research/t198_current_snapshot.json').read_text());out['historical_combat_header_scalars']={c['ptr']:{hex(k):struct.unpack_from('<I',bytes.fromhex(c['head']),k)[0]for k in(0x40,0x44,0xd8,0xdc,0xe0,0xe4,0xe8,0xec)}for c in snap['combats']}
# New targeted read of current idler vtable only; all process targets rebound now.
from mem import Proc,find_pid
from gamestate import detect_session
pr=Proc(find_pid('hoi4.exe'))
try:
 se=detect_session(pr,p);idle=int(se['signals']['idler_ptr'],16);assert pr.read(idle+0x6c1,1)==b'\1';vt=struct.unpack('<Q',pr.read(idle,8))[0];meth=struct.unpack('<Q',pr.read(vt+0xc8,8))[0]-pr.base;out['idler_order_getter']={'vt_rva':hex(vt-pr.base),'getter_rva':hex(meth),'asm':clip(meth)}
finally:pr.close()
(R/'research/t201_exact_anchors.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
