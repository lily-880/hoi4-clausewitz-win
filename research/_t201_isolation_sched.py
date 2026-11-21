from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
import re
cs.detail=False
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
keys=json.loads((R/'research/t201_next_static.json').read_text())['isolation_keys'];wanted={'CHANGE_TEMPLATE_DISABLED_ENCIRCLED','HQ_WITHDRAWAL_BLOCKED_ENCIRCLED','HQ_DEPLOYMENT_BLOCKED_ENCIRCLED','BM_ENCIRCLEMENT_PENALTY'};targets={int(k['rva'],16):k['label']for k in keys if k['label']in wanted};out={'isolation_ui_refs':[]}
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',p.data):
 pos=m.start();at=rv(pos)
 if at is None:continue
 target=at+7+struct.unpack_from('<i',p.data,pos+3)[0]
 if target not in targets:continue
 st,en=fn(at);ls=clip(st);out['isolation_ui_refs'].append({'label':targets[target],'fn':hex(st),'at':hex(at),'context':[s for s in ls if at-300<=int(s.split()[0],16)<=at+80]})
out['plan_lookup_12df090']=clip(0x12df090)
gs=json.loads((R/'research/t201_next_static.json').read_text())['GS_bound_combat_array_functions'];out['low_gs_candidates']=[x for x in gs if int(x['fn'],16)<0x4b0000 and x['virtual_slots']]
(R/'research/t201_isolation_scheduler_focus.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
