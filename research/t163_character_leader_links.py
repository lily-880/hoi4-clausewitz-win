import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls
out={'links':[]}
try:
 rows=json.loads(Path('research/t163_own_character_names.json').read_text(encoding='utf-8'));leaders=json.loads(Path('research/t163_leader_fields.json').read_text(encoding='utf-8'))['leaders'];ls={int(x['ptr'],16):x['name20'] for x in leaders}
 cp=int(rows[0]['ptr'],16);vt=u64(cp);out['character_vtable_rva']=hex(vt-P.base);out['functions']=[hex(x[0]-P.base) for x in struct.iter_unpack('<Q',P.read(vt,0x50))]
 for r in rows:
  p=int(r['ptr'],16);b=P.read(p,0x140)
  for off in range(0,0x140,8):
   val=struct.unpack_from('<Q',b,off)[0]
   if val in ls:out['links'].append({'character':r['name48'],'display_name':r['name28'],'leader':ls[val],'offset':hex(off)})
 out['trait_headers']=[]
 for r in leaders:
  for t in r['traits']:
   tp=int(t['ptr'],16);b=P.read(tp+0x10,32);n,cap=struct.unpack_from('<QQ',b,16);raw=b[:n] if cap<=15 else P.read(struct.unpack_from('<Q',b)[0],n)
   out['trait_headers'].append({'token':t['token'],'name':raw.decode('utf-8'),'offset':'0x10','size':n,'capacity':cap})
 Path('research/t163_character_leader_links.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:P.close()
