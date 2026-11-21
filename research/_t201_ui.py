from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
import re
names=[]
for m in re.finditer(rb'[A-Z][A-Z0-9_]{4,100}\x00',p.data):
 t=m.group()[:-1].decode();a=rv(m.start()) if 'rv'in globals()else None
 if 'SUPPLY'in t and any(k in t for k in('UNIT','ARMY','DIVISION','FULFILL','RATIO','STATUS','SATISF','ISOLAT','OUT_OF','REMAINING','LACK')):names.append({'offset':m.start(),'text':t})
# only deduplicated UI strings; no assertion of what they mean yet
seen=set();out=[]
for x in names:
 if x['text']not in seen and not x['text'].startswith(('NAI','NMILITARY','NMilitary')):out.append(x);seen.add(x['text'])
(R/'research/t201_supply_ui_names.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('SUPPLY_NAMES',json.dumps(out,indent=2))
# Caller argument provenance at exact instruction boundaries
cs.detail=False
ranges=((0xe733ab-0xd0,0xe733ab+10),(0xe7645d-0xd0,0xe7645d+10),(0x1489740,0x1489810))
lines=(R/'research/_t201_clip_e73250.txt').read_text().splitlines();allclips={}
for a,b in ranges:
 source=lines if a<0xe80000 else (R/'research/_t201_clip_1489550.txt').read_text().splitlines();ls=[x for x in source if a<=int(x.split()[0],16)<b];allclips[hex(a)]=ls;print('CALLER_EXCERPT',hex(a),'\n'.join(ls))
(R/'research/t201_argument_provenance.json').write_text(json.dumps(allclips,indent=2),encoding='utf-8')
