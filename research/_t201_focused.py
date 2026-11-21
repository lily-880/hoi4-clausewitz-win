from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
import re
cs.detail=False
out={}
for a in(0x1f5230,0x1eae60):
 ls=clip(a);points=[int(s.split()[0],16)for s in ls if '0x268'in s];out[hex(a)]={'instruction_count':len(ls),'array_offset_contexts':[[s for s in ls if at-75<=int(s.split()[0],16)<=at+110]for at in points]}
out['plan_instance_lookup_10af270']=clip(0x10af270)
# Distinguish exact lowercase persistent tokens from uppercase localized UI keys.
terms=[]
for m in re.finditer(rb'[ -~]{5,200}\x00',p.data):
 raw=m.group()[:-1]
 if any(t in raw for t in(b'encircled',b'isolated',b'IsEncircled',b'is_encircled',b'supply_connection')):terms.append({'file_offset':m.start(),'text':raw.decode('ascii')})
out['native_isolation_terms']=terms
(R/'research/t201_hourly_plan_native.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
