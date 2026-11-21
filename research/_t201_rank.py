import json
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');d=json.loads((R/'research/t201_remaining_static_chains.json').read_text(encoding='utf-8'))
print('PLAN_WRITERS')
for x in d['new_ui_category_refs']:
 if x['asm'].startswith('mov dword ptr'):print(json.dumps(x,indent=2))
print('FALLBACK_REF_COUNT',len(d['order_fallback_ui_refs']));print(json.dumps(d['order_fallback_ui_refs'],indent=2))
out=[]
for x in d['combat_scheduler_candidates']:
 aa={int(s.split()[0],16)for c in x['array_refs']for s in c if '0x268]'in s};cc={int(s.split()[0],16)for c in x['virtual_calls']for s in c if ' call 'in s and any(t in s for t in('+ 0x78]','+ 0x80]'))}
 if aa and cc:out.append((min(abs(a-c)for a in aa for c in cc),x))
print('SCHED_RANK',[(n,x['fn'])for n,x in sorted(out,key=lambda z:z[0])]);print('NEAR_SCHEDULERS',json.dumps([x for n,x in out if n<150],indent=2))
